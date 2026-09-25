# Pocket

A fantasy pocket computer in the spirit of the Sharp Wizard and Psion organisers. MicroPython's embed port drives a simulated 239x80 2-bit LCD with an EL backlight. The OS and its apps are plain Python in `os/`, reloaded on save.

## Build

macOS, SDL3 and the two submodules.

```
git submodule update --init
brew install sdl3

make embed     # once, and after any mpconfigport.h change
make
make run
make check     # syntax, View shadowing, icons, Crates solvability, launch every app
```

## Run

```
./pocket                      # boots os/main.py, data in ./data
./pocket --root=DIR --data=DIR
./pocket --keys="{CLICK}{F2}{DOWN}" --screenshot=shot.bmp --frames=120
./pocket --exec="ui.alert('hi')"
./pocket --no-repl --fps=10 --response=2 --menu=dead-columns
```

Key scripts send special keys as real SDL events. `{+LEFT}`/`{-LEFT}` hold and release, `{CLICK}` clicks the device, `{CLICK:0.1,0.2}` clicks at a fraction of the window, `{WAIT}` skips a step.

Saving anything under the root restarts the VM and drops you back into the last app.

## Keys

| Key | Device |
|-----|--------|
| F1 | MAIN |
| F2 / F3 / F4 / F5 | Tel / Schedule / Memo / Programs |
| F6 | Backlight |
| Tab | MENU |
| Esc | Back |
| Ctrl-C | Interrupt the running app, or cancel the REPL line |
| Cmd-R | Reload (Run menu) |
| Cmd-J | Show or hide the REPL (Run menu) |
| Cmd-L | Focus the REPL, Esc to return to the device |
| Cmd-B | Backlight (System menu) |
| Cmd-D | Dead LCD columns, re-rolled each time (System menu) |

The bezel carries clickable ZQ-770 keys: MAIN/TEL/CAL/MEMO/My Programs and the backlight on the left, MENU, POWER, up/down and ESC/ENTER on the right. System > Show Keys (Cmd-K) hides them.

The System menu also has Frame Rate (unlimited, or 60 down to 10 fps for the device while the window stays smooth) and Response Time (LCD ghosting, instant to very slow). `--fps=N` and `--response=N` set them at launch.

## Layout

| Path | What |
|------|------|
| `src/` | Host: SDL3 window, ImGui REPL, LCD compositor, fiber runtime, `host` and `lcd` modules |
| `os/main.py` | Boots the shell; its globals are the REPL's |
| `os/system/ui.py` | The app SDK: Screen, List, Grid, TextView, TextEdit, Form, Split, Stack, Canvas, dialogs |
| `os/system/` | Shell, fonts, icons, keys, JSON store |
| `os/apps/` | One file per app |

The Guide app on the device documents the SDK.

## Credits

- Icons: [nikoichu's 1-bit Pixel Icons](https://nikoichu.itch.io/pixel-icons), packed by [iconfont-ppf](https://github.com/Gadgetoid/iconfont-ppf), subject to that pack's licence.
- Sins 7 pixel font from Badgeware.
- World map rasterised by `make worldmap` from Badgeware's `world.geo.json`.
- Key icons: [Material Symbols](https://fonts.google.com/icons) (Apache-2.0, see `licences/`), subset into `assets/MaterialSymbolsKeys.ttf`.
- [Dear ImGui](https://github.com/ocornut/imgui) (MIT), [minicoro](https://github.com/edubart/minicoro) (public domain or MIT-0), [dmon](https://github.com/septag/dmon) (BSD-2-Clause).
