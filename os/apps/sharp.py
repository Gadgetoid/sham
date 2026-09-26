import os

from system import keys, ui
from system.gfx import MID
from system.sharpbasic import program, screen
from system.sharpbasic.interpreter import Interpreter

TITLE = "Sharp BASIC"
ICON = "save_disk"
ORDER = 66

FOLDER = "/data/wzd"
FILES = "/data/sharp"

KEY_CODES = {
    keys.LEFT: 15, keys.RIGHT: 14, keys.ENTER: 10, keys.ESC: 27, keys.BACKSPACE: 12, keys.DELETE: 12,
    keys.MENU: 9, keys.NEW: 30,
}


def ensure(folder):
    try:
        os.stat(folder)
    except OSError:
        os.mkdir(folder)


def sharp_code(key):
    code = key.code
    if code == keys.UP:
        return 6 if key.lid else 4
    if code == keys.DOWN:
        return 7 if key.lid else 5
    if code in KEY_CODES:
        return KEY_CODES[code]
    char = key.char
    if char and len(char) == 1 and ord(char) < 256:
        return ord(char.swapcase()) if char.isalpha() else ord(char)
    return None


class BasicView(ui.Canvas):
    retain = True

    def __init__(self, loaded, on_finish):
        super().__init__()
        self.screen = screen.Screen()
        self.interpreter = Interpreter(loaded, self.screen, FILES)
        self.on_finish = on_finish
        self.done = False
        self.pending = []

    def layout(self):
        self.screen.place(self.x + (self.w - screen.WIDTH) // 2, self.y + (self.h - screen.HEIGHT) // 2)

    def paint(self):
        self.clear()
        left = (self.w - screen.WIDTH) // 2
        top = (self.h - screen.HEIGHT) // 2
        self.rect(left - 2, top - 2, screen.WIDTH + 4, screen.HEIGHT + 4, MID)
        self.screen.clear()

    def step(self, now):
        interpreter = self.interpreter
        while self.pending and interpreter.input is not None:
            interpreter.feed_input(self.pending.pop(0))
        interpreter.run(now)
        if self.screen.changed:
            self.screen.changed = False
            self.refresh()
        if interpreter.finished and not self.done:
            self.done = True
            self.on_finish(interpreter.message)

    def key(self, key):
        code = sharp_code(key)
        if code is None:
            return False
        if self.interpreter.input is not None:
            self.pending.append(code)
        else:
            self.interpreter.push_key(code)
        return True


def run(path):
    try:
        loaded = program.load(path)
    except (program.LoadError, OSError) as error:
        ui.alert("{}: {}".format(path.split("/")[-1], error), title="Sharp BASIC")
        return
    ensure(FILES)

    def finished(message):
        ui.pop()
        if message:
            ui.alert(message, title=loaded.title or "Sharp BASIC")

    ui.push(ui.Screen(loaded.title or "Sharp BASIC", BasicView(loaded, finished)))


def programs():
    ensure(FOLDER)
    return sorted(name for name in os.listdir(FOLDER) if name.lower().endswith(".wzd"))


def launch():
    listing = ui.List(programs(), label=lambda name: name[:-4], icon=lambda name: "save_disk",
                      empty="No .wzd files. Install > Install .wzd")
    listing.on_select = lambda name, index: run(FOLDER + "/" + name)
    return ui.Screen("Sharp BASIC", listing, status="Enter: run")
