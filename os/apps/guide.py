from system import keys, ui

TITLE = "Guide"
ICON = "speech_tutorial"
CATEGORY = "System"
ORDER = 90

GUIDE = (
    ("Using Pocket", "hardware_keyboard_text_input", (
        ("Keys", """F1 MAIN, F2 Tel, F3 Schedule, F4 Memo, F5 Programs, F6 backlight.
Tab is MENU. Esc goes back. Arrows move, Enter picks.
Ctrl-C interrupts the running app.
MAIN always returns to the first page of the menu."""),
        ("Keyboard", """NEW, EDIT and SEARCH run the matching MENU entry.
SEARCH in a list finds text.
In text: 2nd+X, C and V cut, copy and paste. 2nd+F flips case. SMBL picks a symbol.
2nd and Shift latch for one keypress. 2nd then Shift toggles CAPS."""),
        ("Char Map", """SEARCH finds an icon by name across every set. Search again for the next match.
SMBL picks a set. [ and ] step through sets.
Enter previews an icon and prints the code to use it."""),
    )),
    ("Games", "controller:gamepad", (
        ("Snake", "Arrows steer. Enter pauses."),
        ("Mines", "Arrows move. Enter reveals, or clears around a satisfied number. F flags."),
        ("Breakout", "Hold arrows to move. Enter serves and pauses."),
        ("Blocks", "Up or X rotates, Z rotates back. Down soft drops, Space hard drops. C holds, P pauses."),
        ("Reversi", "Arrows and Enter. You are black."),
        ("Codebreaker", "1-6 or arrows set pegs. Enter guesses."),
        ("Hangman", "Type letters."),
        ("Crates", "Arrows push. U undoes, R restarts, N and P change level."),
        ("Solitaire", "Enter picks up and drops. Up and Down pick how many cards. Space sends a card home."),
    )),
    ("Writing programs", "terminal", (
        ("Programs", """Programs live in /data/programs and run from the Programs app without a restart.
A program runs top to bottom, or defines launch() returning a Screen.
ui, gfx, icons, keys, sound, store, dates, lcd and host are ready to use.
Importing them (from system import ui, sound) also works and keeps editors happy.
Errors offer to open the editor at the failing line."""),
        ("Apps", """Drop a file in /apps. Give it TITLE, ICON and ORDER, and a launch() that returns a ui.Screen.
CATEGORY = "Games" files it in a launcher folder.
Saving it restarts the device straight back into it."""),
        ("Custom views", """Subclass ui.View.
Draw in draw() with self.text, self.fill, self.icon, self.line and self.invert.
Coordinates are local and clipped to the view.
Animate in tick(self, now) and call self.refresh() to redraw.
Don't reuse the view's own names for your data: x, y, w, h, focused, or methods like draw, key and tick. Prefix them, e.g. ball_x."""),
        ("Input", """Add key(self, key) to a view. Return True if you used the key, False to pass it on.
key.code is the key: keys.UP, DOWN, LEFT, RIGHT, ENTER, ESC, BACKSPACE, NEW, SEARCH.
key.char is the typed character, or None.
Example:
  if key.char == "d": ...
  elif key.code == keys.LEFT: ...
For smooth movement, check keys.held(keys.LEFT) in tick()."""),
        ("Switching views", """ui.push(screen) shows a new screen on top. Esc or ui.pop() returns.
screen.set_body(view) swaps the content of a screen in place.
Keep a reference to the screen if a view needs to swap itself out."""),
    )),
    ("SDK reference", "window_button", (
        ("Screens", """ui.Screen(title, body, status=, menu=, on_close=) is a header over one body view.
status and title can be callables.
menu is a list of (label, function) pairs shown on MENU."""),
        ("Bodies", """ui.List(items, label=, detail=, icon=, on_select=, on_change=)
ui.TextView(text)
ui.TextEdit(text, multiline=)
ui.Form([ui.Field(label, value, choices=)], on_submit=)
ui.Grid(items, label=, icon=)
ui.Canvas(paint=, step=), or subclass it."""),
        ("Layout", """ui.Split(first, second, ratio=, vertical=) puts two views side by side or stacked.
Arrows cross between panes when the focused pane doesn't use them.
ui.Stack(a, b, c) stacks views top to bottom, sized by preferred_height."""),
        ("Dialogs", """ui.alert(text)
ui.confirm(text, on_yes)
ui.prompt(title, on_done)
ui.choose(title, options, on_pick)"""),
        ("Data", """store.load(name, default) and store.save(name, value) keep JSON in /data.
prefs.get(name, default) and prefs.set(name, value) keep settings."""),
        ("Icons", """icons.draw("notepad", x, y) or "weather:sun".
icons.names("emoji") lists a set.
Outline is INK and fill is CLEAR unless you say otherwise.
Char Map browses every icon."""),
        ("Sound", """sound.beep(hz, ms), sound.tone(hz, ms)
sound.play("C5 E5 G5:2") plays notes, :2 doubles a note's length.
sound.dtmf("555") dials tones."""),
        ("REPL", """The REPL shares main.py's globals.
Try shell.stack, ui.alert("hi") or lcd.invert(0, 0, 239, 80)."""),
    )),
)


def topic_screen(category, title, text, line=0):
    view = ui.TextView(text)
    screen = ui.Screen(title, view, status=lambda: "{}/{}".format(view.top + 1, len(view.lines)))
    if line:
        view.scroll(line)
    return screen


def matches(text):
    needle = text.lower()
    found = []
    for category, icon, topics in GUIDE:
        for title, body in topics:
            if needle in title.lower():
                found.append((category, title, body, 0))
                continue
            for number, line in enumerate(body.split("\n")):
                if needle in line.lower():
                    found.append((category, title, body, number))
                    break
    return found


def search():
    def find(text):
        if not text.strip():
            return
        found = matches(text.strip())
        if not found:
            ui.alert("Nothing mentions {}".format(text), title="Search")
            return
        results = ui.List(found, label=lambda hit: hit[1], detail=lambda hit: hit[0],
                          on_select=lambda hit, index: ui.push(topic_screen(hit[0], hit[1], hit[2], hit[3])))
        ui.push(ui.Screen("Search: {}".format(text), results, status="{} found".format(len(found))))

    ui.prompt("Search the guide", find)


class GuideList(ui.List):
    def key(self, key):
        if key.code == keys.SEARCH:
            search()
            return True
        return super().key(key)


def category_screen(category, topics):
    listing = GuideList(topics, label=lambda topic: topic[0],
                        on_select=lambda topic, index: ui.push(topic_screen(category, topic[0], topic[1])))
    return ui.Screen(category, listing, status="SEARCH: find", menu=[("Search", search)])


def launch():
    listing = GuideList(GUIDE, label=lambda entry: entry[0], icon=lambda entry: entry[1],
                        detail=lambda entry: str(len(entry[2])),
                        on_select=lambda entry, index: ui.push(category_screen(entry[0], entry[2])))
    return ui.Screen("Guide", listing, status="SEARCH: find", menu=[("Search", search)])
