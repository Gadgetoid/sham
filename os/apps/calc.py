from system import keys, ui
from system.gfx import MID, INK, small, large

TITLE = "Calc"
ICON = "calculator"
ORDER = 50

ALLOWED = "0123456789.+-*/()% "


def format_number(value):
    if isinstance(value, float):
        if value == int(value) and abs(value) < 1e15:
            return str(int(value))
        return "{:.10g}".format(value)
    return str(value)


class Calculator(ui.View):
    def __init__(self):
        super().__init__()
        self.expression = ""
        self.result = "0"
        self.memory = None

    def evaluate(self):
        if not self.expression:
            return
        try:
            self.result = format_number(eval(self.expression, {}, {}))
            self.memory = self.expression
            self.expression = self.result
        except ZeroDivisionError:
            self.result = "Divide by zero"
        except Exception:
            self.result = "Error"

    def key(self, key):
        char = key.char
        if char and char in "xX":
            char = "*"
        if char and char in ALLOWED:
            self.expression += char
        elif char == "=" or key.code == keys.ENTER:
            self.evaluate()
        elif key.code == keys.BACKSPACE:
            self.expression = self.expression[:-1]
        elif key.code == keys.ESC and (self.expression or self.result != "0"):
            self.expression = ""
            self.result = "0"
            self.memory = None
        else:
            return False
        self.refresh()
        return True

    def draw(self):
        if self.memory:
            text = small.fit(self.memory + " =", self.w - 8)
            self.text(text, self.w - 4 - small.measure(text), 3, MID)
        shown = self.expression or "0"
        while large.measure(shown) > self.w - 8 and len(shown) > 1:
            shown = shown[1:]
        self.text(shown, self.w - 4 - large.measure(shown), 17, INK, large)
        if self.result != self.expression:
            text = "= " + self.result
            self.text(text, self.w - 4 - small.measure(text), 42)
        self.text("Enter: =   Esc: clear", 3, 56, MID)


def launch():
    return ui.Screen("Calc", Calculator())
