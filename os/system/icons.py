import lcd
from system import gfx
from system.gfx import CLEAR, INK
from system.icondata import CATEGORIES

SEARCH_ORDER = ("software",) + tuple(sorted(c for c in CATEGORIES if c != "software"))
FALLBACK = "software:warning_mark_help"


class IconSet:
    def __init__(self, name):
        self.name = name
        self.outline = gfx.load_font("/fonts/icons/{}.ppf".format(name))
        self.fill = gfx.load_font("/fonts/icons/{}_fill.ppf".format(name))
        self.chars = CATEGORIES[name]
        self.width = self.outline.cell_width
        self.height = self.outline.height


_sets = {}


def icon_set(name):
    found = _sets.get(name)
    if found is None:
        found = _sets[name] = IconSet(name)
    return found


def resolve(icon):
    if ":" in icon:
        category, name = icon.split(":", 1)
        if name in CATEGORIES.get(category, ()):
            return icon_set(category), CATEGORIES[category][name]
    else:
        for category in SEARCH_ORDER:
            char = CATEGORIES[category].get(icon)
            if char:
                return icon_set(category), char
    if icon != FALLBACK:
        return resolve(FALLBACK)
    raise ValueError("no icon " + icon)


def names(category=None):
    if category:
        return sorted(CATEGORIES[category])
    return sorted("{}:{}".format(c, n) for c in SEARCH_ORDER for n in CATEGORIES[c])


def draw(icon, x, y, outline=INK, fill=CLEAR, scale=1):
    found, char = resolve(icon)
    if fill is not None:
        lcd.text(found.fill, char, x, y, fill, scale)
    lcd.text(found.outline, char, x, y, outline, scale)


SIZE = icon_set("software").height
