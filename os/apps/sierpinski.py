import random

from system import keys, ui
from system.gfx import INK

TITLE = "Sierpinski"
ICON = "planet_1"
ORDER = 60

POINTS_PER_FRAME = 120
POINT_LIMIT = 30000


class Sierpinski(ui.Canvas):
    retain = True

    def paint(self):
        self.corners = ((self.w // 2, 0), (0, self.h - 1), (self.w - 1, self.h - 1))
        self.px = random.randrange(self.w)
        self.py = random.randrange(self.h)
        self.count = 0

    def step(self, now):
        if self.count >= POINT_LIMIT:
            return
        for _ in range(POINTS_PER_FRAME):
            corner = self.corners[random.randrange(3)]
            self.px = (self.px + corner[0]) // 2
            self.py = (self.py + corner[1]) // 2
            self.pixel(self.px, self.py, INK)
        self.count += POINTS_PER_FRAME

    def key(self, key):
        if key.code == keys.ENTER:
            self.restart()
            return True
        return False


def launch():
    return ui.Screen("Sierpinski", Sierpinski(), status="Enter: again")
