import sys

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

AXES = {"FILL": 0, "wght": 500, "opsz": 24, "GRAD": 0}

ICONS = {
    "call": 0xe0b0,
    "keyboard_arrow_down": 0xe313,
    "keyboard_arrow_up": 0xe316,
    "light_mode": 0xe518,
    "apps": 0xe5c3,
    "power_settings_new": 0xe8ac,
    "calendar_month": 0xebcc,
    "sticky_note_2": 0xf1fc,
    "menu": 0xe5d2,
    "close": 0xe5cd,
    "check": 0xe5ca,
}


def main():
    source = sys.argv[1]
    target = sys.argv[2]
    font = instancer.instantiateVariableFont(TTFont(source), AXES)
    options = subset.Options()
    options.layout_features = []
    options.name_IDs = ["*"]
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=ICONS.values())
    subsetter.subset(font)
    font.save(target)
    print("{}: {} icons".format(target, len(ICONS)))


if __name__ == "__main__":
    main()
