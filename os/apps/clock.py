import host
from system import timefmt, ui
from system.gfx import LIGHT, MID, INK, small, large

TITLE = "Clock"
ICON = "clock_1"
ORDER = 20


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
        x += self.text(digits, x, 8, INK, large) + 4
        self.text(suffix, x, 8 + large.height - small.height)
        date = timefmt.date_label(t)
        self.text(date, (self.w - small.measure(date)) // 2, 36, MID)
        bar_w = self.w - 40
        self.fill(20, 54, bar_w, 5, LIGHT)
        self.fill(20, 54, bar_w * t[5] // 59, 5, INK)


def launch():
    return ui.Screen("Clock", Clock())
