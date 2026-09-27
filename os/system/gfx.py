import lcd

WIDTH = lcd.WIDTH
HEIGHT = lcd.HEIGHT

CLEAR = 0
LIGHT = 1
MID = 2
INK = 3


def load_font(path):
    with open(path, "rb") as f:
        return lcd.Font(f.read())


class Type:
    def __init__(self, font, scale=1, leading=1):
        self.font = font
        self.scale = scale
        self.top = font.ink_top * scale
        self.height = (font.ink_bottom - font.ink_top + 1) * scale
        self.line_height = self.height + leading * scale
        self._widths = {}

    def measure(self, text):
        return lcd.measure(self.font, text, self.scale)

    def char_width(self, char):
        width = self._widths.get(char)
        if width is None:
            width = lcd.measure(self.font, char, self.scale)
            self._widths[char] = width
        return width

    def draw(self, text, x, y, colour=INK):
        return lcd.text(self.font, text, x, y - self.top, colour, self.scale)

    def fit(self, text, width, ellipsis="..."):
        if self.measure(text) <= width:
            return text
        budget = width - self.measure(ellipsis)
        used = 0
        for index, char in enumerate(text):
            used += self.char_width(char)
            if used > budget:
                return text[:index] + ellipsis
        return text


sins = load_font("/fonts/sins.ppf")

small = Type(sins)
large = Type(sins, 2)
huge = Type(sins, 4)


def wrap_spans(text, type, width):
    spans = []
    start = 0
    length = len(text)
    while True:
        newline = text.find("\n", start)
        paragraph_end = length if newline < 0 else newline
        line_start = start
        while True:
            used = 0
            index = line_start
            last_space = -1
            while index < paragraph_end:
                used += type.char_width(text[index])
                if used > width:
                    break
                if text[index] == " ":
                    last_space = index + 1
                index += 1
            if index >= paragraph_end:
                spans.append((line_start, paragraph_end))
                break
            if last_space > line_start:
                split = last_space
            else:
                split = max(index, line_start + 1)
            spans.append((line_start, split))
            line_start = split
        if newline < 0:
            return spans
        start = newline + 1


def wrap(text, type, width):
    return [text[a:b] for a, b in wrap_spans(text, type, width)]


def scrollbar(x, y, h, total, visible, offset):
    if total <= visible or h < 4:
        return
    for dot in range(y, y + h, 2):
        lcd.pixel(x + 1, dot, MID)
    thumb = max(3, h * visible // total)
    top = y + (h - thumb) * offset // max(1, total - visible)
    lcd.fill(x, top, 3, thumb, INK)
