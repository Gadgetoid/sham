import host
from system import dates, keys, prefs, sound, store, timefmt, ui

SNOOZE_MINUTES = 5
RING_MS = 60000

_snoozed = []
_last_minute = None


def clock_alarms():
    return store.load("alarms", [])


def due(day, minute):
    labels = []
    alarms = clock_alarms()
    changed = False
    daily_on = prefs.get("daily_alarm", True)
    for alarm in alarms:
        if daily_on and alarm.get("on") and dates.parse_time(alarm.get("time", "")) == minute:
            labels.append(alarm.get("label") or "Alarm")
            if alarm.get("repeat") == "Once":
                alarm["on"] = False
                changed = True
    if changed:
        store.save("alarms", alarms)
    events = store.load("schedule", []) if prefs.get("schedule_alarm", True) else []
    for event in events:
        if (event.get("alarm") and dates.parse_iso(event.get("date", "")) == day
                and dates.parse_time(event.get("time", "")) == minute):
            labels.append(event.get("title") or "Appointment")
    for snoozed in list(_snoozed):
        if snoozed[:2] == (day, minute):
            labels.append(snoozed[2])
            _snoozed.remove(snoozed)
    return labels


def next_clock_alarm():
    now = dates.now_minutes()
    best = None
    for alarm in clock_alarms():
        minute = dates.parse_time(alarm.get("time", ""))
        if alarm.get("on") and minute is not None:
            wait = (minute - now - 1) % 1440 + 1
            if best is None or wait < best[0]:
                best = (wait, minute)
    return best[1] if best else None


def check():
    global _last_minute
    t = host.localtime()
    minute_key = t[:5]
    if minute_key == _last_minute:
        return
    booting = _last_minute is None
    _last_minute = minute_key
    if booting:
        return
    day = dates.today()
    minute = t[3] * 60 + t[4]
    labels = due(day, minute)
    if labels:
        ui.push(Ringing(labels, day, minute))


class Ringing(ui.Dialog):
    def __init__(self, labels, day, minute):
        super().__init__("ALARM  " + timefmt.clock_label(minute // 60, minute % 60),
                         ui.Message("\n".join(labels), "Enter: stop  S: snooze"))
        self.labels = labels
        self.day = day
        self.minute = minute
        self.started = host.ticks_ms()

    def tick(self, now):
        if now - self.started < RING_MS and not host.beeping():
            for _ in range(4):
                host.beep(2400, 70)
                host.beep(0, 50)
            host.beep(0, 400)

    def snooze(self):
        minute = self.minute + SNOOZE_MINUTES
        day = self.day + minute // 1440
        for label in self.labels:
            _snoozed.append((day, minute % 1440, label))

    def key(self, key):
        if key.code in (keys.ENTER, keys.ESC) or key.char in ("s", "S"):
            if key.char in ("s", "S"):
                self.snooze()
            sound.stop()
            ui.pop()
        return True
