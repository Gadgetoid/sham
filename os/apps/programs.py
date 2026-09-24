import os
import sys

import host
import lcd
from system import dates, gfx, icons, keys, sound, store, ui

TITLE = "Programs"
ICON = "terminal"
ORDER = 65

FOLDER = "/data/programs"

TEMPLATE = """def launch():
    return ui.Screen("{title}", ui.TextView("Hello from {title}!"))
"""

EXAMPLES = {
    "hello.py": """ui.alert("Hello from a program. Find me in Programs and press MENU to edit.", title="Hello")
""",
    "tune.py": """sound.play("E5 D#5 E5 D#5 E5 B4 D5 C5 A4:3")
ui.alert("Fur Elise, on a piezo.", title="Tune")
""",
    "bounce.py": """class Bounce(ui.View):
    def __init__(self):
        super().__init__()
        self.x, self.y = 20, 10
        self.dx, self.dy = 1, 1

    def tick(self, now):
        self.x += self.dx
        self.y += self.dy
        if self.x <= 0 or self.x >= self.w - 16:
            self.dx = -self.dx
            sound.beep(1800, 8)
        if self.y <= 0 or self.y >= self.h - 16:
            self.dy = -self.dy
            sound.beep(1200, 8)
        self.refresh()

    def draw(self):
        self.icon("emoji:face_happy", self.x, self.y)


def launch():
    return ui.Screen("Bounce", Bounce(), status="Esc: stop")
""",
}


def path(name):
    return FOLDER + "/" + name


def read(name):
    with open(path(name)) as f:
        return f.read()


def write(name, text):
    with open(path(name), "w") as f:
        f.write(text)


def ensure_folder():
    try:
        os.stat(FOLDER)
    except OSError:
        os.mkdir(FOLDER)
        for name, source in EXAMPLES.items():
            write(name, source)


def programs():
    return sorted(name for name in os.listdir(FOLDER) if name.endswith(".py"))


def safe_name(title):
    name = "".join(c for c in title.lower().replace(" ", "_") if c.isalpha() or c.isdigit() or c == "_")
    return (name or "program") + ".py"


def describe(error, filename):
    host.capture_start()
    try:
        sys.print_exception(error)
    finally:
        text = host.capture_stop()
    print(text, end="")
    line = None
    for row in text.split("\n"):
        if filename in row and "line " in row:
            number = row.split("line ")[1].split(",")[0]
            if number.isdigit():
                line = int(number)
    return line, text.strip().split("\n")[-1]


def run(name, edit):
    filename = path(name)
    try:
        code = compile(read(name), filename, "exec")
        scope = {"__name__": "__program__", "host": host, "lcd": lcd, "ui": ui, "gfx": gfx,
                 "icons": icons, "keys": keys, "sound": sound, "store": store, "dates": dates}
        exec(code, scope)
        if callable(scope.get("launch")):
            ui.push(scope["launch"]())
    except Exception as error:
        line, message = describe(error, filename)
        if line:
            ui.confirm("{}\nEdit line {}?".format(message, line), lambda: edit(name, line), title=name)
        else:
            ui.alert(message, title=name)


def editor_screen(name, edit, on_close):
    editor = ui.TextEdit(read(name), wrap=False, line_numbers=True, auto_indent=True)
    saved = [editor.value]

    def save():
        write(name, editor.value)
        saved[0] = editor.value
        ui.invalidate()

    def close():
        if editor.value != saved[0]:
            save()
        on_close()

    def run_now():
        save()
        run(name, edit)

    def go_to():
        ui.prompt("Go to line", lambda value: editor.go_to_line(int(value) - 1) if value.isdigit() else None)

    def status():
        return "{}L{} C{}".format("* " if editor.value != saved[0] else "", editor.line_index + 1, editor.column + 1)

    screen = ui.Screen(name, editor, status=status, on_close=close,
                       menu=[("Save", save), ("Run", run_now), ("Go to line", go_to)])
    return screen, editor


def launch():
    ensure_folder()
    listing = ui.List(programs(), label=lambda name: name[:-3], icon=lambda name: "text",
                      empty="No programs. MENU: new")

    def refresh():
        listing.set_items(programs())

    def edit(name=None, line=None):
        name = name or listing.selected
        if not name:
            return
        screen, editor = editor_screen(name, edit, refresh)
        ui.push(screen)
        if line:
            editor.go_to_line(line - 1)

    def create(title):
        name = safe_name(title)
        if name in programs():
            ui.alert("{} already exists.".format(name), title="New program")
            return
        write(name, TEMPLATE.format(title=title or name[:-3]))
        refresh()
        listing.select(programs().index(name))
        edit(name)

    def delete():
        name = listing.selected
        if name:
            ui.confirm("Delete {}?".format(name), lambda: (os.remove(path(name)), refresh()))

    listing.on_select = lambda name, index: run(name, edit)
    return ui.Screen("Programs", listing, status="Enter: run  MENU: edit",
                     menu=lambda: [("Run", lambda: listing.selected and run(listing.selected, edit)),
                                   ("Edit", edit), ("New program", lambda: ui.prompt("New program", create)),
                                   ("Delete", delete)])
