import lcd
from system import keys, ui
from system.gfx import CLEAR, LIGHT, MID, INK, small

TITLE = "Patterns"
ICON = "graphic_fill"
CATEGORY = "System"
ORDER = 86

CELL = 18
SWATCH = 16
PREVIEW = 64
COLOURS = (("INK", INK), ("MID", MID), ("LIGHT", LIGHT))
BACKGROUNDS = (("none", None), ("LIGHT", LIGHT), ("MID", MID))


def usage(number, colour_name):
    return "lcd.fill(x, y, w, h, {}, {})".format(colour_name, number)


class Patterns(ui.View):
    def __init__(self):
        super().__init__()
        self.index = 0
        self.colour_index = 0
        self.background_index = 0

    @property
    def colour_name(self):
        return COLOURS[self.colour_index][0]

    @property
    def background_name(self):
        return BACKGROUNDS[self.background_index][0]

    @property
    def columns(self):
        return max(1, (self.w - PREVIEW - 12) // CELL)

    def select(self, index):
        self.index = max(0, min(index, lcd.PATTERNS - 1))
        self.refresh()

    def cycle_colour(self):
        self.colour_index = (self.colour_index + 1) % len(COLOURS)
        self.refresh()

    def cycle_background(self):
        self.background_index = (self.background_index + 1) % len(BACKGROUNDS)
        self.refresh()

    def print_usage(self):
        print(usage(self.index, self.colour_name))

    def key(self, key):
        steps = {keys.LEFT: -1, keys.RIGHT: 1, keys.UP: -self.columns, keys.DOWN: self.columns}
        if key.code in steps:
            self.select(self.index + steps[key.code])
        elif key.code == keys.HOME:
            self.select(0)
        elif key.code == keys.END:
            self.select(lcd.PATTERNS - 1)
        elif key.code == keys.ENTER:
            self.print_usage()
        elif key.char in ("c", "C"):
            self.cycle_colour()
        elif key.char in ("b", "B"):
            self.cycle_background()
        else:
            return False
        return True

    def swatch(self, x, y, size, number):
        background = BACKGROUNDS[self.background_index][1]
        if background is not None:
            self.fill(x, y, size, size, background)
        self.fill(x, y, size, size, COLOURS[self.colour_index][1], number)

    def draw(self):
        columns = self.columns
        rows = (lcd.PATTERNS + columns - 1) // columns
        top = max(0, (self.h - rows * CELL) // 2)
        for number in range(lcd.PATTERNS):
            x = 2 + (number % columns) * CELL
            y = top + (number // columns) * CELL
            self.swatch(x + 1, y + 1, SWATCH, number)
            self.rect(x + 1, y + 1, SWATCH, SWATCH, MID)
            if number == self.index:
                self.rect(x - 1, y - 1, SWATCH + 4, SWATCH + 4, INK)
        preview_x = self.w - PREVIEW - 4
        preview_y = max(0, (self.h - PREVIEW) // 2)
        self.fill(preview_x, preview_y, PREVIEW, PREVIEW, CLEAR)
        self.swatch(preview_x, preview_y, PREVIEW, self.index)
        self.rect(preview_x - 1, preview_y - 1, PREVIEW + 2, PREVIEW + 2, INK)
        label = "pattern {}".format(self.index)
        self.text(label, preview_x + (PREVIEW - small.measure(label)) // 2, preview_y - 11)


def launch():
    view = Patterns()
    return ui.Screen("Patterns", view,
                     status=lambda: "{} on {}".format(view.colour_name, view.background_name),
                     footer=lambda: usage(view.index, view.colour_name),
                     footer_status=lambda: "{}/{}".format(view.index + 1, lcd.PATTERNS),
                     menu=lambda: [("Colour", view.cycle_colour), ("Background", view.cycle_background),
                                   ("Print usage", view.print_usage)])
