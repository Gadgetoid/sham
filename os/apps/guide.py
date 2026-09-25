from system import ui

TITLE = "Guide"
ICON = "speech_tutorial"
CATEGORY = "System"
ORDER = 90

TEXT = """KEYS
F1 MAIN, F2 Tel, F3 Schedule, F4 Memo, F5 Programs, F6 backlight. Tab is MENU. Esc goes back. Arrows move, Enter picks. Ctrl-C interrupts the running app.

GAMES
Snake: arrows steer, Enter pauses. Mines: arrows move, Enter reveals (or clears around a satisfied number), F flags. Breakout: hold arrows to move, Enter serves and pauses. Blocks: Up or X rotates, Z rotates back, Down soft drops, Space hard drops, C holds, P pauses. Reversi: arrows and Enter, you are black. Codebreaker: 1-6 or arrows set pegs, Enter guesses. Hangman: type letters. Crates: arrows push, U undoes, R restarts, N/P change level. Solitaire: Enter picks up and drops, Up/Down picks how many cards, Space sends a card home.

KEYBOARD
NEW, EDIT and SEARCH run the matching MENU entry. SEARCH in a list finds text. In text, 2nd+X/C/V cut, copy and paste the line, 2nd+F flips case, and SMBL picks a symbol.

WRITING AN APP
Drop a file in /apps. Give it TITLE, ICON and ORDER, and a launch() that returns a ui.Screen. CATEGORY = "Games" files it in a launcher folder. Save it and the device restarts straight back into it.

SCREENS
ui.Screen(title, body, status=, menu=, on_close=) is a header over one body view. status and title can be callables. menu is a list of (label, function) pairs shown on MENU.

BODIES
ui.List(items, label=, detail=, icon=, on_select=, on_change=)
ui.TextView(text)
ui.TextEdit(text, multiline=)
ui.Form([ui.Field(label, value, choices=)], on_submit=)
ui.Grid(items, label=, icon=)
ui.Canvas(paint=, step=) or subclass it.

LAYOUT
ui.Split(first, second, ratio=, vertical=) puts two views side by side or stacked. Arrows cross between panes when the focused pane has nothing to do with them.
ui.Stack(a, b, c) stacks views top to bottom, sized by preferred_height.

DIALOGS
ui.alert(text), ui.confirm(text, on_yes), ui.prompt(title, on_done), ui.choose(title, options, on_pick).

CUSTOM VIEWS
Subclass ui.View. Draw in draw() with self.text, self.fill, self.icon, self.line, self.invert. Coordinates are local and clipped. Return True from key() when you use a key. Call self.refresh() to redraw.

DATA
store.load(name, default) and store.save(name, value) keep JSON in /data.

HELD KEYS
keys.held(keys.LEFT) or keys.held("c") is True while a key is down, for smooth movement in tick().

ICONS
icons.draw("notepad", x, y) or "weather:sun". icons.names("emoji") lists a set. Outline is INK, fill is CLEAR unless you say otherwise.

PROGRAMS
Programs in /data/programs run from the Programs app without a restart. A program runs top to bottom, or defines launch() returning a Screen. ui, gfx, icons, keys, sound, store, dates, lcd and host are ready to use. Errors offer to open the editor at the failing line.

REPL
The REPL shares main.py's globals. Try shell.stack, ui.alert("hi") or lcd.invert(0, 0, 239, 80)."""


def launch():
    view = ui.TextView(TEXT)
    return ui.Screen("Guide", view, status=lambda: "{}/{}".format(view.top + 1, len(view.lines)))
