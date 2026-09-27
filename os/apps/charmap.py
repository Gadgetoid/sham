import lcd
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
PATTERNS = "patterns"
PATTERN_SWATCH = 16
HUGE = gfx.Type(gfx.sins, 4)


def font_codepoints(path):
    with open(path, "rb") as f:
        data = f.read()
    count = int.from_bytes(data[6:10], "big")
    return [int.from_bytes(data[46 + i * 6:50 + i * 6], "big") for i in range(count)]


def set_title(name):
    if name == SINS:
        return "Sins font"
    if name == PATTERNS:
        return "Patterns"
    return icons.icon_set(name).outline.name or name


def set_entries(name):
    if name == SINS:
        return [(chr(cp), "U+{:04X} {}".format(cp, chr(cp))) for cp in font_codepoints("/fonts/sins.ppf") if cp > 32]
    if name == PATTERNS:
        return [(number, "pattern {}".format(number)) for number in range(lcd.PATTERNS)]
    return sorted(((char, label) for label, char in CATEGORIES[name].items()), key=lambda entry: entry[0])


def usage(set_name, entry):
    if set_name == SINS:
        return "gfx.small.draw({!r}, x, y)".format(entry[0])
    if set_name == PATTERNS:
        return "lcd.fill(x, y, w, h, INK, {})".format(entry[0])
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
        if self.set_name == PATTERNS:
            self.fill(2, 2, 48, 48, INK, char)
            self.rect(2, 2, 48, 48, INK)
            self.text("lcd.fill(x, y, w, h,", 56, 4)
            self.text("  INK, {})".format(char), 56, 14)
            self.text("Usage printed", 56, 30, MID)
            self.text("to the REPL", 56, 40, MID)
            return
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
        self.sets = list(icons.SEARCH_ORDER) + [SINS, PATTERNS]
        self.set_index = 0
        self.load()

    @property
    def set_name(self):
        return self.sets[self.set_index]

    def load(self):
        self.entries = set_entries(self.set_name)
        self.cell = GLYPH_CELL if self.set_name == SINS else ICON_CELL
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

    def choose_set(self):
        ui.choose("Sets", list(range(len(self.sets))), lambda value, index: self.switch(index),
                  label=lambda index: "{}  {}".format(set_title(self.sets[index]), self.set_size(index)))

    def set_size(self, index):
        name = self.sets[index]
        if name == SINS:
            return len(font_codepoints("/fonts/sins.ppf"))
        if name == PATTERNS:
            return lcd.PATTERNS
        return len(CATEGORIES[name])

    def search(self):
        def find(text):
            needle = text.strip().lower().replace(" ", "_")
            if not needle:
                return
            order = [(self.set_index + step) % len(self.sets) for step in range(len(self.sets) + 1)]
            for pass_index, set_index in enumerate(order):
                name = self.sets[set_index]
                entries = set_entries(name)
                start = self.index + 1 if pass_index == 0 else 0
                if pass_index == len(order) - 1:
                    entries, start = entries[:self.index + 1], 0
                for position in range(start, len(entries)):
                    char, label = entries[position]
                    if needle in label.lower() or (name == SINS and text.strip() == char):
                        if set_index != self.set_index:
                            self.switch(set_index)
                        self.select(position)
                        return
            ui.alert("No icon matching {}".format(text), title="Search")

        ui.prompt("Search icons", find)

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
        elif code == keys.SEARCH:
            self.search()
        elif code in (keys.SMBL, keys.PICK):
            self.choose_set()
        elif char and char.isalpha() and self.set_name not in (SINS, PATTERNS):
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
            elif self.set_name == PATTERNS:
                self.fill(x + 1, y + 1, PATTERN_SWATCH, PATTERN_SWATCH, INK, char)
                self.rect(x + 1, y + 1, PATTERN_SWATCH, PATTERN_SWATCH, MID)
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
                     menu=lambda: [("Search", view.search), ("Choose set", view.choose_set), ("Preview", view.preview)])
