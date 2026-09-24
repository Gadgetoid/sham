import host
from system import alarms, dates, store, timefmt, ui
from system.gfx import LIGHT, MID, INK, small, large

TITLE = "Clock"
ICON = "clock_1"
ORDER = 20

REPEATS = ["Daily", "Once"]


class Clock(ui.View):
    def __init__(self):
        super().__init__()
        self.second = None

    def tick(self, now):
        second = host.localtime()[5]
        if second != self.second:
            self.second = second
            self.refresh()

    def draw(self):
        t = host.localtime()
        hour = t[3] % 12 or 12
        digits = "{}:{:02d}:{:02d}".format(hour, t[4], t[5])
        suffix = "AM" if t[3] < 12 else "PM"
        width = large.measure(digits) + 4 + small.measure(suffix)
        x = (self.w - width) // 2
        x += self.text(digits, x, 5, INK, large) + 4
        self.text(suffix, x, 5 + large.height - small.height)
        date = timefmt.date_label(t)
        self.text(date, (self.w - small.measure(date)) // 2, 29, MID)
        upcoming = alarms.next_clock_alarm()
        if upcoming is not None:
            label = "Alarm " + dates.format_time(upcoming)
            label_w = small.measure(label) + 19
            left = (self.w - label_w) // 2
            self.icon("clock_up", left, 39)
            self.text(label, left + 19, 43)
        bar_w = self.w - 40
        self.fill(20, 62, bar_w, 3, LIGHT)
        self.fill(20, 62, bar_w * t[5] // 59, 3, INK)


def alarm_screen():
    entries = store.load("alarms", [])
    listing = ui.List(entries,
                      label=lambda a: "{}  {}".format(a["time"], a.get("label") or "Alarm"),
                      detail=lambda a: a.get("repeat", "Daily"),
                      icon=lambda a: "checkbox_done_todo" if a.get("on") else "checkbox_empty_todo",
                      empty="No alarms. MENU: new alarm")

    def save():
        entries.sort(key=lambda a: a["time"])
        store.save("alarms", entries)
        listing.set_items(entries)

    def toggle(alarm, index):
        alarm["on"] = not alarm.get("on")
        save()

    def edit(alarm=None):
        def done(values):
            minute = dates.parse_time(values["time"])
            if minute is None:
                ui.alert("Use HH:MM, like 07:30.", title="Time?")
                return
            ui.pop()
            record = alarm if alarm is not None else {}
            record.update(time=dates.format_time(minute), label=values["label"], repeat=values["repeat"], on=True)
            if alarm is None:
                entries.append(record)
            save()
            listing.select(entries.index(record))

        current = alarm or {}
        form = ui.Form([
            ui.Field("Time", current.get("time", "07:00")),
            ui.Field("Label", current.get("label", "")),
            ui.Field("Repeat", current.get("repeat", "Daily"), choices=REPEATS),
        ], on_submit=done)
        ui.push(ui.Screen("Alarm", form, status="Enter: next"))

    def delete():
        if entries:
            ui.confirm("Delete this alarm?", lambda: (entries.pop(listing.index), save()))

    listing.on_select = toggle
    return ui.Screen("Alarms", listing, status="Enter: on/off",
                     menu=lambda: [("New alarm", edit), ("Edit", lambda: edit(listing.selected)), ("Delete", delete)])


def launch():
    return ui.Screen("Clock", Clock(), status="MENU: alarms",
                     menu=[("Alarms", lambda: ui.push(alarm_screen()))])
