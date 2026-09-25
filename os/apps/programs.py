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
        self.ball_x, self.ball_y = 20, 10
        self.dx, self.dy = 1, 1

    def tick(self, now):
        self.ball_x += self.dx
        self.ball_y += self.dy
        if self.ball_x <= 0 or self.ball_x >= self.w - 15:
            self.dx = -self.dx
            sound.beep(1800, 8)
        if self.ball_y <= 0 or self.ball_y >= self.h - 16:
            self.dy = -self.dy
            sound.beep(1200, 8)
        self.refresh()

    def draw(self):
        self.icon("emoji:face_happy", self.ball_x, self.ball_y)


def launch():
    return ui.Screen("Bounce", Bounce(), status="Esc: stop")
""",
    "piano.py": """LOWER = "zsxdcvgbhnjm"
UPPER = "q2w3er5t6y7u"
WHITE = (0, 2, 4, 5, 7, 9, 11)
BLACK = {1: 0, 3: 1, 6: 3, 8: 4, 10: 5}
NOTE_MS = 280
GLOW_MS = 220


class Piano(ui.View):
    def __init__(self):
        super().__init__()
        self.octave = 4
        self.lit = {}

    def note_for(self, char):
        if char in LOWER:
            return LOWER.index(char)
        if char in UPPER:
            return 12 + UPPER.index(char)
        return None

    def play(self, note):
        hz = 440 * 2 ** ((note - 9) / 12 + self.octave - 4)
        sound.stop()
        sound.tone(hz, NOTE_MS)
        self.lit[note] = host.ticks_ms()
        self.refresh()

    def key(self, key):
        char = key.char.lower() if key.char else None
        note = self.note_for(char) if char else None
        if note is not None:
            self.play(note)
        elif key.code == keys.UP:
            self.octave = min(6, self.octave + 1)
        elif key.code == keys.DOWN:
            self.octave = max(2, self.octave - 1)
        elif key.code == keys.ENTER:
            sound.play("C5 E5 G5 C6:2 G5 C6:3", 110)
        else:
            return False
        self.refresh()
        return True

    def tick(self, now):
        faded = [note for note, at in self.lit.items() if now - at > GLOW_MS]
        for note in faded:
            del self.lit[note]
        if faded:
            self.refresh()

    def draw(self):
        white_w = 16
        left = (self.w - white_w * 14) // 2
        top = 12
        height = self.h - top - 2
        for octave in range(2):
            for index, semitone in enumerate(WHITE):
                note = octave * 12 + semitone
                x = left + (octave * 7 + index) * white_w
                if note in self.lit:
                    self.fill(x, top, white_w - 1, height, gfx.MID)
                self.rect(x, top, white_w, height)
                label = (LOWER if octave == 0 else UPPER)[semitone].upper()
                self.text(label, x + (white_w - gfx.small.measure(label)) // 2, top + height - 12,
                          gfx.CLEAR if note in self.lit else gfx.MID)
            for semitone, after in BLACK.items():
                note = octave * 12 + semitone
                x = left + (octave * 7 + after + 1) * white_w - 5
                self.fill(x, top, 10, height * 3 // 5, gfx.LIGHT if note in self.lit else gfx.INK)
        self.text("C{}  Up/Down: octave  Enter: tune".format(self.octave), 2, 0, gfx.MID)


def launch():
    return ui.Screen("Piano", Piano(), status="Type to play")
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
    seeded = store.load("programs_seeded", [])
    existing = os.listdir(FOLDER)
    for name, source in EXAMPLES.items():
        if name not in seeded:
            if name not in existing:
                write(name, source)
            seeded.append(name)
    store.save("programs_seeded", seeded)


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
