import math

import lcd
from system import sound
from system.gfx import CLEAR, INK, load_font

WIDTH = 239
HEIGHT = 70
ROW_H = 10

_font = None


def font():
    global _font
    if _font is None:
        _font = load_font("/fonts/sharp.ppf")
    return _font


class Screen:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.changed = False

    def place(self, x, y):
        self.x = x
        self.y = y

    def measure(self, text):
        return lcd.measure(font(), text)

    def inside(self, x, y):
        return 0 <= x < WIDTH and 0 <= y < HEIGHT

    def clear(self):
        lcd.fill(self.x, self.y, WIDTH, HEIGHT, CLEAR)
        self.changed = True

    def char(self, char, x, row):
        width = lcd.measure(font(), char)
        top = self.y + row * ROW_H
        lcd.fill(self.x + x, top, min(width, WIDTH - x), ROW_H, CLEAR)
        lcd.text(font(), char, self.x + x, top, INK)
        self.changed = True

    def clear_row_from(self, x, row):
        lcd.fill(self.x + x, self.y + row * ROW_H, WIDTH - x, ROW_H, CLEAR)
        self.changed = True

    def cursor(self, x, row):
        if x < WIDTH:
            lcd.fill(self.x + x, self.y + row * ROW_H + ROW_H - 2, min(5, WIDTH - x), 1, INK)
            self.changed = True

    def scroll(self):
        rest = lcd.grab(self.x, self.y + ROW_H, WIDTH, HEIGHT - ROW_H)
        lcd.blit(rest, self.x, self.y, WIDTH, HEIGHT - ROW_H)
        lcd.fill(self.x, self.y + HEIGHT - ROW_H, WIDTH, ROW_H, CLEAR)
        self.changed = True

    def point(self, x, y):
        if not self.inside(x, y):
            return 0
        return 1 if lcd.grab(self.x + x, self.y + y, 1, 1)[0] else 0

    def pset(self, x, y, mode="S"):
        if not self.inside(x, y):
            return
        if mode == "X":
            lcd.invert(self.x + x, self.y + y, 1, 1)
        else:
            lcd.pixel(self.x + x, self.y + y, CLEAR if mode == "R" else INK)
        self.changed = True

    def line(self, x0, y0, x1, y1, mode="S", pattern=0xFFFF):
        if pattern == 0xFFFF and mode != "X":
            previous = lcd.clip(self.x, self.y, WIDTH, HEIGHT)
            lcd.line(self.x + x0, self.y + y0, self.x + x1, self.y + y1, CLEAR if mode == "R" else INK)
            lcd.clip(previous)
            self.changed = True
            return
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        error = dx + dy
        bit = 0
        while True:
            if pattern & (0x8000 >> (bit & 15)):
                self.pset(x0, y0, mode)
            bit += 1
            if x0 == x1 and y0 == y1:
                break
            doubled = 2 * error
            if doubled >= dy:
                error += dy
                x0 += sx
            if doubled <= dx:
                error += dx
                y0 += sy

    def box_fill(self, x0, y0, x1, y1, mode="S"):
        left, right = max(0, min(x0, x1)), min(WIDTH - 1, max(x0, x1))
        top, bottom = max(0, min(y0, y1)), min(HEIGHT - 1, max(y0, y1))
        if right < left or bottom < top:
            return
        if mode == "X":
            lcd.invert(self.x + left, self.y + top, right - left + 1, bottom - top + 1)
        else:
            lcd.fill(self.x + left, self.y + top, right - left + 1, bottom - top + 1, CLEAR if mode == "R" else INK)
        self.changed = True

    def circle(self, cx, cy, radius, start=0, end=360, ratio=1):
        steps = max(12, int(abs(radius) * 6))
        span = (end - start) if end > start else end - start + 360
        previous = None
        for i in range(steps + 1):
            angle = math.radians(start + span * i / steps)
            x = int(round(cx + radius * math.cos(angle)))
            y = int(round(cy - radius * ratio * math.sin(angle)))
            if previous and previous != (x, y):
                self.line(previous[0], previous[1], x, y)
            elif previous is None:
                self.pset(x, y)
            previous = (x, y)

    def row(self, x, y, bits):
        for bit in range(8):
            if bits & (0x80 >> bit):
                self.pset(x + bit, y)

    def beep(self, count):
        sound.play(" ".join(["C6:1"] * count), 60)
