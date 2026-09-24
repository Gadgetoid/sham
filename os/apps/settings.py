import gc
import sys

import host
from system import prefs, sound, ui

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
    def toggle(name):
        def apply(value):
            prefs.set(name, value == "On")
            sound.beep()
        return apply

    sound_field = ui.Field("Sound", "On" if prefs.get("sound", True) else "Off", choices=["On", "Off"],
                           on_change=toggle("sound"))
    click_field = ui.Field("Key click", "On" if prefs.get("click", False) else "Off", choices=["On", "Off"],
                           on_change=toggle("click"))
    form = ui.Form([backlight, sound_field, click_field])
    details = ui.TextView(info())
    return ui.Screen("Settings", ui.Split(form, details, vertical=True))
