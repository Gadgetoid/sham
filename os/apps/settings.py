import gc
import sys

import host
from system import ui

TITLE = "Settings"
ICON = "options_wrench"
CATEGORY = "System"
ORDER = 80


def info():
    gc.collect()
    return "MicroPython {}\nHeap free {} KB, used {} KB\nPlatform: {}".format(
        ".".join(str(part) for part in sys.implementation.version[:3]),
        gc.mem_free() // 1024, gc.mem_alloc() // 1024, sys.platform)


def launch():
    backlight = ui.Field("Backlight", "On" if host.backlight() else "Off", choices=["On", "Off"],
                         on_change=lambda value: host.backlight(value == "On"))
    form = ui.Form([backlight])
    details = ui.TextView(info())
    return ui.Screen("Settings", ui.Split(form, details, vertical=True))
