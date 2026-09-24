import os
import sys

import host
import lcd
from system import alarms, keys, sound, timefmt, ui

HOTKEYS = {
    keys.TEL: "tel",
    keys.CLOCK: "clock",
    keys.MEMO: "memo",
    keys.PROGRAMS: "guide",
}

FOLDER_ICONS = {
    "Games": "controller:gamepad",
    "System": "options_mechanics",
}


class App:
    def __init__(self, name, module):
        self.name = name
        self.module = module
        self.title = getattr(module, "TITLE", None) or name[:1].upper() + name[1:]
        self.icon = getattr(module, "ICON", "window_button")
        self.order = getattr(module, "ORDER", 100)
        self.category = getattr(module, "CATEGORY", None)


class Folder:
    def __init__(self, title):
        self.title = title
        self.icon = FOLDER_ICONS.get(title, "file_explorer")
        self.apps = []

    @property
    def order(self):
        return min(app.order for app in self.apps)


def discover():
    apps = []
    for filename in sorted(os.listdir("/apps")):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue
        name = filename[:-3]
        try:
            __import__("apps." + name)
            apps.append(App(name, sys.modules["apps." + name]))
        except Exception as error:
            print("apps/{}: failed to import".format(filename))
            sys.print_exception(error)
    apps.sort(key=lambda app: (app.order, app.title))
    return apps


def group(apps):
    entries = []
    folders = {}
    for app in apps:
        if not app.category:
            entries.append(app)
            continue
        if app.category not in folders:
            folders[app.category] = Folder(app.category)
            entries.append(folders[app.category])
        folders[app.category].apps.append(app)
    entries.sort(key=lambda entry: (entry.order, entry.title))
    return entries, folders


class Shell:
    def __init__(self):
        ui._shell = self
        self.apps = discover()
        self.entries, self.folders = group(self.apps)
        self.stack = []
        self.current = None
        self.minute = None
        self.grid = self.make_grid(self.entries)
        self.launcher = ui.Screen(lambda: timefmt.date_label(host.localtime()), self.grid,
                                  status=lambda: "{}  {}".format(timefmt.time_label(host.localtime()),
                                                                 self.grid.page_label()))

    def make_grid(self, entries):
        return ui.Grid(entries, on_select=lambda entry, index: self.open(entry),
                       label=lambda entry: entry.title, icon=lambda entry: entry.icon)

    def open(self, entry):
        if isinstance(entry, Folder):
            self.open_folder(entry.title)
        else:
            self.launch(entry.name)

    def folder_screen(self, folder, selected=None):
        grid = self.make_grid(folder.apps)
        if selected in folder.apps:
            grid.select(folder.apps.index(selected))
        return ui.Screen(folder.title, grid, status=grid.page_label)

    def open_folder(self, title):
        folder = self.folders.get(title)
        if not folder:
            return
        self.close_all()
        self.current = None
        self.stack = [self.folder_screen(folder)]
        self.grid.select(self.entries.index(folder))
        host.resume("folder:" + title)
        ui.invalidate()

    def find(self, name):
        for app in self.apps:
            if app.name == name:
                return app
        return None

    def launch(self, name):
        if name.startswith("folder:"):
            self.open_folder(name[7:])
            return
        app = self.find(name)
        if not app:
            return
        self.close_all()
        try:
            screen = app.module.launch()
        except Exception as error:
            self.crash(error, app.title)
            return
        self.current = app
        folder = self.folders.get(app.category)
        self.stack = [self.folder_screen(folder, app), screen] if folder else [screen]
        self.grid.select(self.entries.index(folder or app))
        host.resume(name)
        ui.invalidate()

    def push(self, screen):
        self.stack.append(screen)
        ui.invalidate()

    def pop(self):
        if not self.stack:
            return
        screen = self.stack.pop()
        ui.invalidate()
        if screen.on_close:
            screen.on_close()
        if not self.stack:
            self.go_home()
        elif self.current and self.current.category and len(self.stack) == 1:
            self.current = None
            host.resume("folder:" + self.stack[0].title)

    def close_all(self):
        while self.stack:
            screen = self.stack.pop()
            if screen.on_close:
                screen.on_close()

    def go_home(self):
        self.close_all()
        self.current = None
        host.resume(None)
        ui.invalidate()

    def top(self):
        return self.stack[-1] if self.stack else self.launcher

    def handle(self, key):
        code = key.code
        sound.click()
        if code == keys.MAIN:
            self.go_home()
        elif code in HOTKEYS:
            self.launch(HOTKEYS[code])
        elif code == keys.LIGHT:
            host.backlight(not host.backlight())
        elif not self.top().key(key) and code == keys.ESC and self.stack:
            self.pop()

    def layers(self):
        layers = []
        for screen in reversed(self.stack):
            layers.append(screen)
            if not screen.modal:
                return reversed(layers)
        layers.append(self.launcher)
        return reversed(layers)

    def draw(self):
        lcd.clip()
        lcd.clear()
        for screen in self.layers():
            try:
                screen.render()
            except Exception as error:
                if screen is self.top():
                    raise
                sys.print_exception(error)

    def crash(self, error, where):
        sys.print_exception(error)
        self.stack = []
        self.current = None
        host.resume(None)
        ui.alert("{}: {}".format(type(error).__name__, error), title="{} stopped".format(where))

    def run(self):
        resume = host.resume()
        if resume:
            self.launch(resume)
        while True:
            try:
                for key in keys.poll():
                    self.handle(key)
                alarms.check()
                self.top().tick(host.ticks_ms())
                minute = host.localtime()[4]
                if minute != self.minute:
                    self.minute = minute
                    ui.invalidate()
                if ui.take_dirty():
                    self.draw()
                host.present()
            except KeyboardInterrupt:
                print("KeyboardInterrupt")
                self.go_home()
            except Exception as error:
                self.crash(error, self.current.title if self.current else "System")
