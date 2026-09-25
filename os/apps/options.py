import gc
import os
import sys

import host
from system import dates, keys, prefs, sound, store, timefmt, ui, worldtime
from system.gfx import CLEAR, LIGHT, MID, INK, small

TITLE = "Options"
ICON = "options_wrench"
CATEGORY = "System"
ORDER = 80

ON_OFF = ["On", "Off"]


def on_off(value):
    return "On" if value else "Off"


def local_day(text):
    date = timefmt.parse_numeric_date(text)
    return dates.parse_iso("{:04d}-{:02d}-{:02d}".format(*date)) if date else None


def local_label(day):
    return timefmt.numeric_date(*dates.from_days(day))


def clock_screen():
    t = host.localtime()
    cities = [city[0] for city in worldtime.CITIES]
    fields = [
        ui.Field("City", prefs.get("home_city", "London"), choices=cities),
        ui.Field("Time system", "24" if timefmt.use_24h() else "12", choices=["12", "24"],
                 on_change=lambda value: prefs.set("time_24h", value == "24")),
        ui.Field("Local date", timefmt.numeric_date(t[0], t[1], t[2]), picker=ui.date_picker(local_day, local_label)),
        ui.Field("Local time", timefmt.clock_label(t[3], t[4])),
    ]

    def done(values):
        date = timefmt.parse_numeric_date(values["local_date"])
        clock = timefmt.parse_clock(values["local_time"])
        day = dates.parse_iso("{:04d}-{:02d}-{:02d}".format(*date)) if date else None
        if day is None:
            ui.alert("Invalid year, month or day settings!", title="Clock")
            return
        if clock is None:
            ui.alert("Invalid time settings!", title="Clock")
            return
        wanted = day * 86400 + clock[0] * 3600 + clock[1] * 60
        for _ in range(2):
            now = host.localtime()
            current = dates.to_days(now[0], now[1], now[2]) * 86400 + now[3] * 3600 + now[4] * 60
            host.clock_offset(host.clock_offset() + wanted - current)
        prefs.set("clock_offset", host.clock_offset())
        prefs.set("home_city", values["city"])
        ui.pop()

    def use_mac_clock():
        host.clock_offset(0)
        prefs.set("clock_offset", 0)
        ui.pop()

    def status():
        city = [c for c in worldtime.CITIES if c[0] == fields[0].value][0]
        return "DST" if worldtime.dst_active(city[4], city[3], host.epoch()) else ""

    return ui.Screen("ADJUST TIME/DATE", ui.Form(fields, on_submit=done), status=status,
                     menu=[("Use Mac clock", use_mac_clock)])


def formats_screen():
    return ui.Screen("FORMATS", ui.Form([
        ui.Field("Date format", timefmt.date_format(), choices=list(timefmt.DATE_FORMATS),
                 on_change=lambda value: prefs.set("date_format", value)),
        ui.Field("Weekly format", prefs.get("week_start", "SUNDAY"), choices=["SUNDAY", "MONDAY"],
                 on_change=lambda value: prefs.set("week_start", value)),
        ui.Field("Time system", "24" if timefmt.use_24h() else "12", choices=["12", "24"],
                 on_change=lambda value: prefs.set("time_24h", value == "24")),
    ]))


def sound_screen():
    def toggle(setting):
        def apply(value):
            setting(value == "On")
            sound.beep()
        return apply

    def pref_toggle(name):
        return lambda value: prefs.set(name, value == "On")

    return ui.Screen("SOUND", ui.Form([
        ui.Field("Sound", on_off(host.sound()), choices=ON_OFF, on_change=toggle(host.sound)),
        ui.Field("Key sound", on_off(host.key_click()), choices=ON_OFF, on_change=toggle(host.key_click)),
        ui.Field("Schedule alarm", on_off(prefs.get("schedule_alarm", True)), choices=ON_OFF,
                 on_change=pref_toggle("schedule_alarm")),
        ui.Field("Daily alarm", on_off(prefs.get("daily_alarm", True)), choices=ON_OFF,
                 on_change=pref_toggle("daily_alarm")),
    ]), menu=[("Alarm tone test", sound.alarm)])


class Contrast(ui.View):
    def key(self, key):
        step = {keys.UP: 1, keys.RIGHT: 1, keys.DOWN: -1, keys.LEFT: -1}.get(key.code)
        if step is None:
            if key.code == keys.ENTER:
                ui.pop()
                return True
            return False
        host.contrast(host.contrast() + step)
        prefs.set("contrast", host.contrast())
        self.refresh()
        return True

    def draw(self):
        level = host.contrast()
        left = 40
        cell = (self.w - 2 * left) // 11
        self.text("LIGHT", 2, 10, MID)
        self.text("DARK", self.w - small.measure("DARK") - 2, 10, MID)
        for index in range(11):
            x = left + index * cell
            height = 4 + index
            self.fill(x, 20 - height, cell - 2, height, INK if index <= level else LIGHT)
        self.rect(left + level * cell - 2, 3, cell + 2, 20, INK)
        self.text("Press [UP] for darker, [DOWN] for lighter.", 2, 32)
        self.text("Press [ENTER] to continue.", 2 + (self.w - small.measure("Press [ENTER] to continue.")) // 2 - 2, 46, MID)


def contrast_screen():
    return ui.Screen("CONTRAST", Contrast(), status=lambda: str(host.contrast()))


def startup_screen():
    return ui.Screen("START UP", ui.Form([
        ui.Field("Owner info", "SHOW" if prefs.get("startup_owner", False) else "HIDE", choices=["SHOW", "HIDE"],
                 on_change=lambda value: prefs.set("startup_owner", value == "SHOW")),
    ]))


def owner_screen():
    owner = prefs.get("owner", {})
    fields = [ui.Field("Name", owner.get("name", "")), ui.Field("Number", owner.get("number", "")),
              ui.Field("Address", owner.get("address", ""))]

    def save():
        prefs.set("owner", {field.name: field.value for field in fields})

    def done(values):
        save()
        ui.pop()

    return ui.Screen("OWNER INFORMATION", ui.Form(fields, on_submit=done), on_close=save)


def key_assignment_screen():
    from system import shell
    apps = shell.discover()
    names = [app.name for app in apps]
    titles = {app.name: app.title for app in apps}
    assigned = prefs.get("hotkeys", {})
    fields = []
    for label, code, default in shell.HOTKEY_BUTTONS:
        current = assigned.get(label, default)
        fields.append(ui.Field("{} key".format(label), titles.get(current, current),
                               choices=[titles[name] for name in names], name=label))

    def save():
        by_title = {title: name for name, title in titles.items()}
        prefs.set("hotkeys", {field.name: by_title[field.value] for field in fields})

    return ui.Screen("KEY ASSIGNMENT", ui.Form(fields), on_close=save, status="F2-F5")


def data_usage():
    total = 0
    files = 0
    folders = ["/data"]
    while folders:
        folder = folders.pop()
        for name in os.listdir(folder):
            path = folder + "/" + name
            stat = os.stat(path)
            if stat[0] & 0x4000:
                folders.append(path)
            else:
                total += stat[6]
                files += 1
    return files, total


def memory_screen():
    gc.collect()
    files, total = data_usage()
    text = "Data: {} files, {} bytes\nHeap free {} KB, used {} KB\nMicroPython {} on {}".format(
        files, total, gc.mem_free() // 1024, gc.mem_alloc() // 1024,
        ".".join(str(part) for part in sys.implementation.version[:3]), sys.platform)

    def format_databank():
        def wipe():
            folders = ["/data"]
            doomed = []
            while folders:
                folder = folders.pop()
                for name in os.listdir(folder):
                    path = folder + "/" + name
                    if os.stat(path)[0] & 0x4000:
                        folders.append(path)
                        doomed.append(path)
                    elif path != "/data/prefs.json":
                        os.remove(path)
            for folder in reversed(doomed):
                os.rmdir(folder)
            host.resume(None)
            host.reload()

        ui.confirm("Do you really want to initialize the organizer's memory (this will delete all data)?", wipe,
                   title="MEMORY")

    return ui.Screen("MEMORY", ui.TextView(text), menu=[("Format databank...", format_databank)])


PAGES = (
    ("Clock", "clock_1", clock_screen),
    ("Formats", "text", formats_screen),
    ("Sound", "options_audio", sound_screen),
    ("Contrast", "monitor_contrast", contrast_screen),
    ("Start-up Display", "window_select_1", startup_screen),
    ("Owner Info.", "sign_property", owner_screen),
    ("Key Assignment", "hardware_key_input", key_assignment_screen),
    ("Memory", "storage_1", memory_screen),
)


def launch():
    listing = ui.List(PAGES, label=lambda page: page[0], icon=lambda page: page[1],
                      on_select=lambda page, index: ui.push(page[2]()))
    return ui.Screen("OPTIONS", listing)
