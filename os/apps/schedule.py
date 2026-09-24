from system import dates, keys, store, ui
from system.gfx import CLEAR, MID, INK, small

TITLE = "Schedule"
ICON = "calendar_2"
ORDER = 15

STRIP_H = 12
DAY_NAMES = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")


def sort_key(event):
    return (event["date"], event.get("time") or "")


class Week(ui.View):
    focusable = False
    preferred_height = STRIP_H

    def __init__(self, agenda):
        super().__init__()
        self.agenda = agenda

    def draw(self):
        selected = self.agenda.day
        start = selected - dates.weekday(selected)
        today = dates.today()
        busy = self.agenda.busy_days()
        cell_w = self.w // 7
        for index in range(7):
            day = start + index
            x = index * cell_w
            label = "{} {}".format(DAY_NAMES[index], dates.from_days(day)[2])
            self.text(label, x + (cell_w - small.measure(label)) // 2, 1, INK if index < 5 else MID)
            if day in busy:
                self.fill(x + cell_w // 2 - 1, STRIP_H - 2, 2, 1, INK)
            if day == today:
                self.fill(x + 3, STRIP_H - 1, cell_w - 6, 1, MID)
            if day == selected:
                self.invert(x + 1, 0, cell_w - 2, STRIP_H - 2)
        self.fill(0, STRIP_H - 1, self.w, 1, CLEAR)


class Agenda(ui.Stack):
    def __init__(self):
        self.events = store.load("schedule", [])
        self.day = dates.today()
        self.listing = ui.List([], on_select=lambda event, index: self.edit(event),
                               label=self.label, detail=lambda e: "alarm" if e.get("alarm") else "",
                               empty="Nothing on. MENU: new")
        super().__init__(Week(self), self.listing)
        self.show()

    def label(self, event):
        return "{}  {}".format(event.get("time") or "--:--", event["title"])

    def busy_days(self):
        return {dates.parse_iso(event["date"]) for event in self.events}

    def show(self):
        today = dates.iso(self.day)
        self.listing.set_items([event for event in self.events if event["date"] == today])
        ui.invalidate()

    def go(self, day):
        self.day = day
        self.listing.index = 0
        self.show()

    def save(self):
        self.events.sort(key=sort_key)
        store.save("schedule", self.events)
        self.show()

    def key(self, key):
        code = key.code
        if code == keys.LEFT:
            self.go(self.day - 1)
        elif code == keys.RIGHT:
            self.go(self.day + 1)
        elif code == keys.PGUP:
            self.go(self.day - 7)
        elif code == keys.PGDN:
            self.go(self.day + 7)
        elif key.char in ("t", "T"):
            self.go(dates.today())
        else:
            return self.listing.key(key)
        return True

    def edit(self, event=None):
        current = event or {"date": dates.iso(self.day), "time": "", "title": "", "alarm": False}

        def done(values):
            day = dates.parse_iso(values["date"])
            minute = dates.parse_time(values["time"]) if values["time"] else None
            if day is None or (values["time"] and minute is None):
                ui.alert("Date is YYYY-MM-DD, time is HH:MM or blank.", title="Check that")
                return
            if not values["title"]:
                ui.alert("Give it a title.", title="Check that")
                return
            ui.pop()
            record = event if event is not None else {}
            record.update(date=dates.iso(day), time=dates.format_time(minute) if minute is not None else "",
                          title=values["title"], alarm=values["alarm"] == "On" and minute is not None)
            if event is None:
                self.events.append(record)
            self.day = day
            self.save()
            if record in self.listing.items:
                self.listing.select(self.listing.items.index(record))

        form = ui.Form([
            ui.Field("Date", current["date"]),
            ui.Field("Time", current.get("time", "")),
            ui.Field("Title", current.get("title", "")),
            ui.Field("Alarm", "On" if current.get("alarm") else "Off", choices=["Off", "On"]),
        ], on_submit=done)
        ui.push(ui.Screen("Appointment", form, status="Enter: next"))

    def delete(self):
        event = self.listing.selected
        if event:
            ui.confirm("Delete {}?".format(event["title"]), lambda: (self.events.remove(event), self.save()))


def launch():
    agenda = Agenda()
    return ui.Screen("Schedule", agenda, status=lambda: dates.short_label(agenda.day),
                     menu=[("New appointment", agenda.edit), ("Edit", lambda: agenda.edit(agenda.listing.selected)),
                           ("Delete", agenda.delete), ("Today", lambda: agenda.go(dates.today()))])
