import host

BACKSPACE = host.KEY_BACKSPACE
TAB = host.KEY_TAB
ENTER = host.KEY_ENTER
ESC = host.KEY_ESC
DELETE = host.KEY_DELETE
UP = host.KEY_UP
DOWN = host.KEY_DOWN
LEFT = host.KEY_LEFT
RIGHT = host.KEY_RIGHT
HOME = host.KEY_HOME
END = host.KEY_END
PGUP = host.KEY_PGUP
PGDN = host.KEY_PGDN


def F(number):
    return host.KEY_F1 + number - 1


MENU = TAB
MAIN = F(1)
TEL = F(2)
CAL = F(3)
MEMO = F(4)
PROGRAMS = F(5)
LIGHT = F(6)

SPECIAL_FIRST = UP
SPECIAL_LAST = F(16)

SHIFT = host.MOD_SHIFT
CTRL = host.MOD_CTRL
ALT = host.MOD_ALT


class Key:
    __slots__ = ("code", "mods")

    def __init__(self, code, mods=0):
        self.code = code
        self.mods = mods

    @property
    def char(self):
        if self.mods & CTRL:
            return None
        printable_ascii = 32 <= self.code < 127
        printable_unicode = self.code >= 160 and not SPECIAL_FIRST <= self.code <= SPECIAL_LAST
        return chr(self.code) if printable_ascii or printable_unicode else None

    @property
    def shift(self):
        return bool(self.mods & SHIFT)

    @property
    def ctrl(self):
        return bool(self.mods & CTRL)

    def __eq__(self, other):
        if isinstance(other, Key):
            return self.code == other.code and self.mods == other.mods
        return self.code == other

    def __repr__(self):
        return "Key({}, {})".format(self.code, self.mods)


def poll():
    while True:
        event = host.key()
        if event is None:
            return
        yield Key(event[0], event[1])


def held(code):
    if isinstance(code, str):
        code = ord(code.lower())
    return host.held(code)
