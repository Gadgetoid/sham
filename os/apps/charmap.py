from system import gfx, icons, keys, ui
from system.gfx import CLEAR, LIGHT, MID, INK, small
from system.icondata import CATEGORIES

TITLE = "Char Map"
ICON = "software:hardware_keyboard_text_input"
CATEGORY = "System"
ORDER = 85

ICON_CELL = 18
GLYPH_CELL = 12
INFO_H = 11
SINS = "sins"
HUGE = gfx.Type(gfx.sins, 4)


def font_codepoints(path):
    with open(path, "rb") as f:
        data = f.read()
    count = int.from_bytes(data[6:10], "big")
    return [int.from_bytes(data[46 + i * 6:50 + i * 6], "big") for i in range(count)]


def set_title(name):
    if name == SINS:
        return "Sins font"
    return icons.icon_set(name).outline.name or name


def usage(set_name, entry):
    if set_name == SINS:
        return "gfx.small.draw({!r}, x, y)".format(entry[0])
    return 'icons.draw("{}:{}", x, y)'.format(set_name, entry[1])


class Enlarged(ui.View):
    focusable = False
    preferred_height = 52

    def __init__(self, set_name, entry):
        super().__init__()
        self.set_name = set_name
        self.entry = entry

    def draw(self):
        char, label = self.entry
        if self.set_name == SINS:
            self.text(char, 4 + (48 - HUGE.measure(char)) // 2, 6, INK, HUGE)
        else:
            icons.draw("{}:{}".format(self.set_name, label), self.x + 2, self.y + 2, scale=3)
        text_x = 56
        self.text(small.fit(label, self.w - text_x - 2), text_x, 4)
        if self.set_name != SINS:
            self.text("U+{:04X}".format(ord(char)), text_x, 16, MID)
        self.text("Usage printed", text_x, 30, MID)
        self.text("to the REPL", text_x, 40, MID)


class CharMap(ui.View):
    def __init__(self):
        super().__init__()
        self.sets = list(icons.SEARCH_ORDER) + [SINS]
        self.set_index = 0
        self.load()

    @property
    def set_name(self):
        return self.sets[self.set_index]

    def load(self):
        if self.set_name == SINS:
            self.entries = [(chr(cp), "U+{:04X} {}".format(cp, chr(cp))) for cp in font_codepoints("/fonts/sins.ppf") if cp > 32]
            self.cell = GLYPH_CELL
        else:
            self.entries = sorted(((char, name) for name, char in CATEGORIES[self.set_name].items()),
                                  key=lambda entry: entry[0])
            self.cell = ICON_CELL
        self.index = 0
        self.top = 0
        self.refresh()

    def switch(self, index):
        self.set_index = index % len(self.sets)
        self.load()

    @property
    def columns(self):
        return max(1, (self.w - 2) // self.cell)

    @property
    def rows(self):
        return max(1, (self.h - INFO_H) // self.cell)

    def select(self, index):
        self.index = max(0, min(index, len(self.entries) - 1))
        row = self.index // self.columns
        if row < self.top:
            self.top = row
        elif row >= self.top + self.rows:
            self.top = row - self.rows + 1
        self.refresh()

    def preview(self):
        entry = self.entries[self.index]
        print(usage(self.set_name, entry))
        ui.push(ui.Dialog(set_title(self.set_name), Enlarged(self.set_name, entry), width=200))

    def key(self, key):
        code = key.code
        char = key.char
        steps = {keys.LEFT: -1, keys.RIGHT: 1, keys.UP: -self.columns, keys.DOWN: self.columns,
                 keys.PGUP: -self.columns * self.rows, keys.PGDN: self.columns * self.rows}
        if code in steps:
            self.select(self.index + steps[code])
        elif code == keys.HOME:
            self.select(0)
        elif code == keys.END:
            self.select(len(self.entries) - 1)
        elif char in ("[", ","):
            self.switch(self.set_index - 1)
        elif char in ("]", "."):
            self.switch(self.set_index + 1)
        elif code == keys.ENTER:
            self.preview()
        elif char and char.isalpha() and self.set_name != SINS:
            for step in range(1, len(self.entries) + 1):
                candidate = (self.index + step) % len(self.entries)
                if self.entries[candidate][1][:1] == char.lower():
                    self.select(candidate)
                    break
        else:
            return False
        return True

    def draw(self):
        cell = self.cell
        left = (self.w - self.columns * cell) // 2
        first = self.top * self.columns
        for position in range(self.columns * self.rows):
            index = first + position
            if index >= len(self.entries):
                break
            char, label = self.entries[index]
            x = left + (position % self.columns) * cell
            y = (position // self.columns) * cell
            if self.set_name == SINS:
                self.text(char, x + (cell - small.measure(char)) // 2, y + 2)
            else:
                icons.draw("{}:{}".format(self.set_name, label), self.x + x + 1, self.y + y + 1)
            if index == self.index:
                self.invert(x, y, cell, cell)
        total_rows = (len(self.entries) + self.columns - 1) // self.columns
        gfx.scrollbar(self.x + self.w - 3, self.y, self.rows * cell, total_rows, self.rows, self.top)
        info_y = self.h - INFO_H + 1
        self.fill(0, info_y - 2, self.w, 1, LIGHT)
        char, label = self.entries[self.index]
        position = "{}/{}".format(self.index + 1, len(self.entries))
        self.text(position, self.w - small.measure(position) - 2, info_y, MID)
        self.text(small.fit(label, self.w - small.measure(position) - 10), 2, info_y)


def launch():
    view = CharMap()
    return ui.Screen("Char Map", view,
                     status=lambda: "{}  {}/{}".format(set_title(view.set_name), view.set_index + 1, len(view.sets)),
                     menu=lambda: [("Choose set", lambda: ui.choose("Sets", list(range(len(view.sets))),
                                                                   lambda value, index: view.switch(index),
                                                                   label=lambda index: set_title(view.sets[index]))),
                                   ("Preview", view.preview)])
