import math
import os
import random

import host
from system.sharpbasic import tokens as T
from system.sharpbasic.program import KEYWORD, NUMBER, STRING, NAME, SYMBOL, REFERENCE, RAW

ROWS = 7
ROW_H = 10
WIDTH = 239
HEIGHT = 70
MAX_FILES = 4

MESSAGES = {
    10: "Syntax error", 20: "Overflow", 21: "Division by Zero", 22: "Illegal function call",
    30: "Duplicate Definition", 31: "Array specified without DIM", 32: "Subscript out of range",
    40: "Illegal line number", 50: "GOSUB or FOR nesting exceeded", 51: "RETURN without GOSUB",
    52: "NEXT without FOR", 53: "Out of data", 61: "String too long", 70: "RESUME without error",
    81: "USING format error", 82: "I/O error", 83: "Too many files open", 85: "File not open",
    86: "File already open", 87: "Input past end", 90: "Type mismatch", 94: "File not found",
    95: "Bad file name", 99: "Machine code isn't supported",
}


class BasicError(Exception):
    def __init__(self, code):
        super().__init__(MESSAGES.get(code, "Error {}".format(code)))
        self.code = code


class Suspend(Exception):
    pass


class Finished(Exception):
    pass


def format_number(value):
    if value == 0:
        return "0."
    if value != value or abs(value) >= 1e100:
        raise BasicError(20)
    sign = "-" if value < 0 else ""
    digits = "{:.9e}".format(abs(value))
    mantissa, _, power = digits.partition("e")
    exponent = int(power)
    mantissa = mantissa.replace(".", "").rstrip("0") or "0"
    if 0 <= exponent < 10 and len(mantissa) <= 10:
        whole = (mantissa + "0" * exponent)[:exponent + 1]
        fraction = mantissa[exponent + 1:]
        return sign + whole + "." + fraction
    if -10 < exponent < 0 and len(mantissa) - exponent <= 10:
        return sign + "0." + "0" * (-exponent - 1) + mantissa
    body = mantissa[0] + "." + mantissa[1:]
    return "{}{}E{}{:02d}".format(sign, body, "-" if exponent < 0 else " ", abs(exponent))


def string_of(value):
    text = format_number(value)
    return text[:-1] if text.endswith(".") else text


def format_using(value, pattern):
    if isinstance(value, str):
        width = pattern.count("&")
        return (value + " " * width)[:width] if width else value
    if "#" not in pattern:
        return format_number(value)
    point = pattern.find(".")
    decimals = len(pattern) - point - 1 if point >= 0 else 0
    width = len(pattern)
    text = ("{:." + str(decimals) + "f}").format(value)
    if point >= 0 and decimals == 0:
        text += "."
    if len(text) > width:
        return "%" + text
    return " " * (width - len(text)) + text


class File:
    def __init__(self, path, mode):
        self.path = path
        self.mode = mode
        if mode == "input":
            with open(path) as f:
                self.values = self.split(f.read())
            self.position = 0
        else:
            self.handle = open(path, "a" if mode == "append" else "w")

    @staticmethod
    def split(text):
        values = []
        for line in text.replace("\r", "").split("\n"):
            if line == "":
                continue
            current = ""
            quoted = False
            for char in line:
                if char == '"':
                    quoted = not quoted
                elif char == "," and not quoted:
                    values.append(current)
                    current = ""
                    continue
                current += char
            values.append(current)
        return values

    def close(self):
        if self.mode != "input":
            self.handle.close()


class Interpreter:
    def __init__(self, program, screen, files_dir):
        self.program = program
        self.screen = screen
        self.files_dir = files_dir
        self.keys = []
        self.reset()

    def reset(self):
        self.numbers = {}
        self.strings = {}
        self.arrays = {}
        self.gosubs = []
        self.fors = []
        self.data_index = 0
        self.files = {}
        self.line = 0
        self.position = 0
        self.statement = (0, 0)
        self.angle = math.pi / 180
        self.using = None
        self.print_pause = None
        self.wake_at = 0
        self.waiting_key = False
        self.input = None
        self.input_groups = []
        self.error_target = None
        self.error_code = 0
        self.error_line = 0
        self.error_resume = None
        self.finished = False
        self.message = None
        self.cursor_x = 0
        self.cursor_y = 0
        self.graphic_x = 0
        self.graphic_y = 0

    def push_key(self, code):
        if self.waiting_key == "pause":
            self.waiting_key = False
            return
        if len(self.keys) < 16:
            self.keys.append(code)
        if self.waiting_key == "inkey":
            self.waiting_key = False

    @property
    def tokens(self):
        return self.program.lines[self.line].tokens

    def peek(self, offset=0):
        tokens = self.tokens
        index = self.position + offset
        return tokens[index] if index < len(tokens) else None

    def take(self):
        token = self.peek()
        if token is None:
            raise BasicError(10)
        self.position += 1
        return token

    def at_symbol(self, symbol):
        token = self.peek()
        return token is not None and token[0] == SYMBOL and token[1] == symbol

    def at_keyword(self, code):
        token = self.peek()
        return token is not None and token[0] == KEYWORD and token[1] == code

    def accept(self, symbol):
        if self.at_symbol(symbol):
            self.position += 1
            return True
        return False

    def accept_keyword(self, code):
        if self.at_keyword(code):
            self.position += 1
            return True
        return False

    def expect(self, symbol):
        if not self.accept(symbol):
            raise BasicError(10)

    def at_end(self):
        token = self.peek()
        return token is None or (token[0] == SYMBOL and token[1] == ":") or (token[0] == KEYWORD and token[1] in (T.ELSE, T.THEN))

    def run(self, now, budget_ms=12):
        if self.finished:
            return
        if self.input is not None or self.waiting_key:
            return
        if now < self.wake_at:
            return
        deadline = now + budget_ms
        steps = 0
        while not self.finished and self.input is None and not self.waiting_key and self.wake_at <= now:
            self.statement = (self.line, self.position)
            try:
                self.step()
            except Suspend:
                self.line, self.position = self.statement
                return
            except Finished:
                self.finish()
                return
            except BasicError as error:
                self.fail(error)
            except ZeroDivisionError:
                self.fail(BasicError(21))
            except OverflowError:
                self.fail(BasicError(20))
            except (ValueError, IndexError):
                self.fail(BasicError(22))
            except OSError:
                self.fail(BasicError(82))
            steps += 1
            if steps % 16 == 0 and host.ticks_ms() >= deadline:
                return

    def finish(self):
        for file in self.files.values():
            file.close()
        self.files = {}
        self.finished = True

    def fail(self, error):
        line = self.program.lines[self.statement[0]].number
        if self.error_target is not None and self.error_resume is None:
            self.error_code = error.code
            self.error_line = line
            self.error_resume = self.statement
            self.jump(self.error_target)
            return
        self.message = "{} in {}".format(error, line)
        self.finish()

    def jump(self, target):
        found = self.program.find(target)
        if found is None:
            raise BasicError(40)
        self.line, self.position = found

    def next_line(self):
        self.line += 1
        self.position = 0
        if self.line >= len(self.program.lines):
            raise Finished()

    def step(self):
        while True:
            token = self.peek()
            if token is None:
                self.next_line()
                continue
            if (token[0] == SYMBOL and token[1] == ":") or (token[0] == KEYWORD and token[1] == T.THEN):
                self.position += 1
                continue
            if token[0] == KEYWORD and token[1] == T.ELSE:
                self.next_line()
                continue
            break
        self.statement = (self.line, self.position)
        kind, value = self.take()
        if kind == NAME:
            self.position -= 1
            self.assign()
        elif kind == KEYWORD:
            handler = STATEMENTS.get(value)
            if handler is None:
                raise BasicError(10)
            try:
                handler(self)
            except Continue:
                return
        elif kind == RAW:
            pass
        else:
            raise BasicError(10)
        if not self.at_end():
            raise BasicError(10)

    def reference(self):
        kind, value = self.take()
        if kind == REFERENCE:
            return value
        if kind == NUMBER:
            return int(value)
        raise BasicError(10)

    def variable(self):
        kind, name = self.take()
        if kind != NAME:
            raise BasicError(10)
        if self.at_symbol("("):
            self.position += 1
            indices = [self.integer()]
            while self.accept(","):
                indices.append(self.integer())
            self.expect(")")
            return name, indices
        return name, None

    def store(self, target, value):
        name, indices = target
        is_string = name.endswith("$")
        if is_string != isinstance(value, str):
            raise BasicError(90)
        if indices is None:
            (self.strings if is_string else self.numbers)[name] = value
            return
        array = self.array(name)
        array[1][self.offset(array, indices)] = value

    def fetch(self, target):
        name, indices = target
        if indices is None:
            if name.endswith("$"):
                return self.strings.get(name, "")
            return self.numbers.get(name, 0.0)
        array = self.array(name)
        return array[1][self.offset(array, indices)]

    def array(self, name):
        array = self.arrays.get(name)
        if array is None:
            raise BasicError(31)
        return array

    def offset(self, array, indices):
        dims = array[0]
        if len(indices) != len(dims):
            raise BasicError(32)
        offset = 0
        for index, size in zip(indices, dims):
            if index < 0 or index > size:
                raise BasicError(32)
            offset = offset * (size + 1) + index
        return offset

    def assign(self):
        while True:
            target = self.variable()
            self.expect("=")
            self.store(target, self.expression())
            if not self.accept(","):
                return

    def integer(self):
        value = self.expression()
        if isinstance(value, str):
            raise BasicError(90)
        return int(value)

    def number(self):
        value = self.expression()
        if isinstance(value, str):
            raise BasicError(90)
        return value

    def text_value(self):
        value = self.expression()
        if not isinstance(value, str):
            raise BasicError(90)
        return value

    def expression(self):
        left = self.conjunction()
        while True:
            if self.accept_keyword(T.OR):
                left = float(int(self.as_number(left)) | int(self.as_number(self.conjunction())))
            elif self.accept_keyword(T.XOR):
                left = float(int(self.as_number(left)) ^ int(self.as_number(self.conjunction())))
            else:
                return left

    def conjunction(self):
        left = self.negation()
        while self.accept_keyword(T.AND):
            left = float(int(self.as_number(left)) & int(self.as_number(self.negation())))
        return left

    def negation(self):
        if self.accept_keyword(T.NOT):
            return float(~int(self.as_number(self.negation())))
        return self.comparison()

    def comparison(self):
        left = self.sum()
        token = self.peek()
        if token is not None and token[0] == SYMBOL and token[1] in ("=", "<", ">", "<=", ">=", "<>"):
            self.position += 1
            right = self.sum()
            if isinstance(left, str) != isinstance(right, str):
                raise BasicError(90)
            op = token[1]
            result = (left == right if op == "=" else left < right if op == "<" else left > right if op == ">" else
                      left <= right if op == "<=" else left >= right if op == ">=" else left != right)
            return -1.0 if result else 0.0
        return left

    def sum(self):
        left = self.product()
        while True:
            if self.accept("+"):
                right = self.product()
                if isinstance(left, str) != isinstance(right, str):
                    raise BasicError(90)
                left = left + right
                if isinstance(left, str) and len(left) > 255:
                    raise BasicError(61)
            elif self.accept("-"):
                left = self.as_number(left) - self.as_number(self.product())
            else:
                return left

    def product(self):
        left = self.unary()
        while True:
            if self.accept("*"):
                left = self.as_number(left) * self.as_number(self.unary())
            elif self.accept("/"):
                right = self.as_number(self.unary())
                if right == 0:
                    raise BasicError(21)
                left = self.as_number(left) / right
            else:
                return left

    def unary(self):
        if self.accept("-"):
            return -self.as_number(self.unary())
        if self.accept("+"):
            return self.as_number(self.unary())
        return self.power()

    def power(self):
        left = self.primary()
        while self.accept("^"):
            right = self.as_number(self.unary())
            left = math.pow(self.as_number(left), right)
        return left

    def as_number(self, value):
        if isinstance(value, str):
            raise BasicError(90)
        return value

    def primary(self):
        kind, value = self.take()
        if kind == NUMBER:
            return value
        if kind == STRING:
            return value
        if kind == NAME:
            self.position -= 1
            return self.fetch(self.variable())
        if kind == SYMBOL and value == "(":
            result = self.expression()
            self.expect(")")
            return result
        if kind == KEYWORD:
            return self.function(value)
        raise BasicError(10)

    def argument(self):
        if self.accept("("):
            value = self.expression()
            self.expect(")")
            return value
        return self.power()

    def arguments(self, count):
        parens = self.accept("(")
        values = [self.expression()]
        while len(values) < count and self.accept(","):
            values.append(self.expression())
        if parens:
            self.expect(")")
        return values

    def function(self, code):
        if code in T.NO_ARGUMENT:
            return self.constant(code)
        if code == 0xE9:
            return self.inkey()
        if code in T.PAREN_ARGUMENTS:
            return self.multi(code, self.arguments(3))
        if code in T.ONE_ARGUMENT:
            return self.single(code, self.argument())
        raise BasicError(10)

    def constant(self, code):
        if code == 0xAE:
            return math.pi
        if code == 0xF7:
            return float(self.error_code)
        if code == 0xF8:
            return float(self.error_line)
        now = host.localtime()
        if code == 0xF3:
            return "{:04d}{:02d}{:02d}".format(now[0], now[1], now[2])
        return "{:02d}:{:02d}".format(now[3], now[4])

    def inkey(self):
        wait = False
        if self.accept("("):
            wait = self.expression() != 0
            self.expect(")")
        if self.keys:
            return chr(self.keys.pop(0))
        if wait:
            self.waiting_key = "inkey"
            raise Suspend()
        return ""

    def single(self, code, value):
        if code in (0xD0, 0xD1, 0xD2, 0xD3):
            if not isinstance(value, str):
                raise BasicError(90)
            if code == 0xD0:
                return float(ord(value[0])) if value else 0.0
            if code == 0xD1:
                return self.parse_value(value)
            if code == 0xD2:
                return float(len(value))
            return float(self.screen.measure(value))
        value = self.as_number(value)
        a = self.angle
        if code == 0xF0:
            return chr(int(value) & 0xFF)
        if code == 0xF1:
            return string_of(value)
        if code == 0xF2:
            return "{:X}".format(int(value))
        if code == 0x98:
            return float(math.floor(value))
        if code == 0x99:
            return abs(value)
        if code == 0x9A:
            return float((value > 0) - (value < 0))
        if code == 0xA0:
            if value > 1:
                return float(random.randint(1, int(value)))
            return random.random() * value if value > 0 else random.random()
        if code == 0x94:
            if value < 0:
                raise BasicError(22)
            return math.sqrt(value)
        if code == 0x95:
            return math.sin(value * a)
        if code == 0x96:
            return math.cos(value * a)
        if code == 0x97:
            return math.tan(value * a)
        if code == 0x9D:
            return math.asin(value) / a
        if code == 0x9E:
            return math.acos(value) / a
        if code == 0x9F:
            return math.atan(value) / a
        if code == 0x91:
            if value <= 0:
                raise BasicError(22)
            return math.log(value)
        if code == 0x92:
            if value <= 0:
                raise BasicError(22)
            return math.log(value) / math.log(10)
        if code == 0x93:
            return math.exp(value)
        if code == 0x86:
            return math.pow(10, value)
        if code == 0x87:
            if value == 0:
                raise BasicError(21)
            return 1 / value
        if code == 0x88:
            return value * value
        if code == 0xBF:
            return value * value * value
        if code == 0x89:
            return math.copysign(math.pow(abs(value), 1 / 3), value)
        if code == 0x8A:
            return (math.exp(value) - math.exp(-value)) / 2
        if code == 0x8B:
            return (math.exp(value) + math.exp(-value)) / 2
        if code == 0x8C:
            return math.tanh(value) if hasattr(math, "tanh") else (math.exp(2 * value) - 1) / (math.exp(2 * value) + 1)
        if code == 0x8D:
            return math.log(value + math.sqrt(value * value + 1))
        if code == 0x8E:
            return math.log(value + math.sqrt(value * value - 1))
        if code == 0x8F:
            return 0.5 * math.log((1 + value) / (1 - value))
        if code == 0x90:
            if value < 0 or value != int(value) or value > 69:
                raise BasicError(22)
            result = 1.0
            for i in range(2, int(value) + 1):
                result *= i
            return result
        if code == 0x9B:
            sign = -1 if value < 0 else 1
            value = abs(value)
            degrees = int(value)
            minutes = int(round((value - degrees) * 100, 6))
            seconds = ((value - degrees) * 100 - minutes) * 100
            return sign * (degrees + minutes / 60 + seconds / 3600)
        if code == 0x9C:
            sign = -1 if value < 0 else 1
            value = abs(value)
            degrees = int(value)
            minutes = int((value - degrees) * 60)
            seconds = ((value - degrees) * 60 - minutes) * 60
            return sign * (degrees + minutes / 100 + seconds / 10000)
        if code == 0x80:
            return value
        if code in (0xB0, 0xB2):
            file = self.files.get(int(value))
            if file is None:
                raise BasicError(85)
            if code == 0xB0:
                return -1.0 if file.mode != "input" or file.position >= len(file.values) else 0.0
            return float(len(file.values)) if file.mode == "input" else 0.0
        raise BasicError(10)

    def multi(self, code, values):
        if code in (0xEA, 0xEB, 0xEC):
            text = values[0]
            if not isinstance(text, str):
                raise BasicError(90)
            if code == 0xEB:
                return text[:max(0, int(values[1]))]
            if code == 0xEC:
                count = max(0, int(values[1]))
                return text[len(text) - count:] if count else ""
            start = max(1, int(values[1])) - 1
            if len(values) > 2:
                return text[start:start + max(0, int(values[2]))]
            return text[start:]
        values = [self.as_number(v) for v in values]
        if code == 0xAD:
            return float(self.screen.point(int(values[0]), int(values[1])))
        if code == 0xA4:
            return 0.0
        if code == 0x81:
            return values[0] * math.cos(values[1] * self.angle)
        if code == 0x82:
            return math.sqrt(values[0] * values[0] + values[1] * values[1])
        if code in (0xB6, 0xB7):
            n, r = int(values[0]), int(values[1])
            if r < 0 or n < r:
                raise BasicError(22)
            result = 1.0
            for i in range(n - r + 1, n + 1):
                result *= i
            if code == 0xB6:
                for i in range(2, r + 1):
                    result /= i
            return float(round(result))
        raise BasicError(10)

    def parse_value(self, text):
        text = text.strip()
        if text[:2].upper() == "&H":
            try:
                return float(int(text[2:], 16))
            except ValueError:
                return 0.0
        end = 0
        while end < len(text) and (text[end].isdigit() or text[end] in "+-.eE"):
            end += 1
        while end:
            try:
                return float(text[:end])
            except ValueError:
                end -= 1
        return 0.0

    def print_value(self, value):
        if self.using is not None:
            return format_using(value, self.using)
        return value if isinstance(value, str) else format_number(value)

    def pause_after_print(self):
        if not self.print_pause:
            return
        if self.print_pause == "key":
            self.waiting_key = "pause"
            self.keys.clear()
            return
        self.wake_at = host.ticks_ms() + int(self.print_pause * 100)

    def write(self, text):
        screen = self.screen
        for char in text:
            if char == "\r":
                continue
            if self.cursor_y >= ROWS:
                screen.scroll()
                self.cursor_y = ROWS - 1
            width = screen.measure(char)
            if self.cursor_x + width > WIDTH:
                self.newline()
            screen.char(char, self.cursor_x, self.cursor_y)
            self.cursor_x += width

    def newline(self):
        self.cursor_x = 0
        if self.cursor_y >= ROWS:
            self.screen.scroll()
        else:
            self.cursor_y += 1

    def file_number(self):
        self.expect("#")
        return self.integer()

    def open_file(self, number):
        file = self.files.get(number)
        if file is None:
            raise BasicError(85)
        return file

    def path_for(self, name):
        if name[:2].upper() != "E:":
            raise BasicError(82)
        base = name[2:]
        if not base or len(base) > 8 or any(c in base for c in "/\\:*?"):
            raise BasicError(95)
        return self.files_dir + "/" + base

    def begin_input(self, prompt, targets):
        self.write("?" if prompt is None else prompt)
        self.input = {"targets": targets, "text": "", "x": self.cursor_x, "y": self.cursor_y}
        self.show_input()

    def feed_input(self, code):
        state = self.input
        if code in (10, 13):
            self.input = None
            self.newline()
            try:
                self.finish_input(state)
            except BasicError as error:
                self.fail(error)
                return
            if self.input_groups:
                self.begin_input(*self.input_groups.pop(0))
            return
        if code == 12:
            if state["text"]:
                state["text"] = state["text"][:-1]
        elif code == 27:
            state["text"] = ""
        elif 32 <= code < 256:
            state["text"] += chr(code)
        self.show_input()

    def show_input(self):
        state = self.input
        self.screen.clear_row_from(state["x"], state["y"])
        x = state["x"]
        for char in state["text"]:
            self.screen.char(char, x, state["y"])
            x += self.screen.measure(char)
        self.screen.cursor(x, state["y"])
        self.cursor_x = x

    def finish_input(self, state):
        values = File.split(state["text"]) if len(state["targets"]) > 1 else [state["text"]]
        for index, target in enumerate(state["targets"]):
            text = values[index].strip() if index < len(values) else ""
            if target[0].endswith("$"):
                self.store(target, text)
            else:
                self.store(target, self.parse_value(text))


def statement_print(interp):
    if interp.at_symbol("#"):
        file = interp.open_file(interp.file_number())
        interp.accept(",")
        parts = []
        while not interp.at_end():
            if interp.accept(";") or interp.accept(","):
                continue
            value = interp.expression()
            parts.append('"{}"'.format(value) if isinstance(value, str) and "," in value else
                         value if isinstance(value, str) else string_of(value))
        if file.mode == "input":
            raise BasicError(82)
        file.handle.write(",".join(parts) + "\r\n")
        return
    newline = True
    while not interp.at_end():
        if interp.accept_keyword(T.USING):
            interp.using = interp.text_value() if interp.peek() and interp.peek()[0] == STRING else None
            interp.accept(";")
            continue
        if interp.accept(";") or interp.accept(","):
            newline = False
            continue
        interp.write(interp.print_value(interp.expression()))
        newline = True
    if newline:
        interp.newline()
    interp.pause_after_print()


def statement_locate(interp):
    if not interp.at_symbol(","):
        interp.cursor_x = max(0, min(WIDTH - 1, interp.integer()))
    if interp.accept(","):
        interp.cursor_y = max(0, min(ROWS - 1, interp.integer()))


def statement_cls(interp):
    interp.screen.clear()
    interp.cursor_x = interp.cursor_y = 0


def statement_if(interp):
    condition = interp.expression()
    truth = condition != "" if isinstance(condition, str) else condition != 0
    if truth:
        if interp.accept_keyword(T.THEN) or interp.at_keyword(T.GOTO):
            token = interp.peek()
            if token is not None and token[0] in (REFERENCE, NUMBER):
                interp.jump(interp.reference())
                raise_continue()
            if interp.accept_keyword(T.GOTO):
                interp.jump(interp.reference())
                raise_continue()
        raise_continue()
    tokens = interp.tokens
    for index in range(interp.position, len(tokens)):
        if tokens[index][0] == KEYWORD and tokens[index][1] == T.ELSE:
            interp.position = index + 1
            token = interp.peek()
            if token is not None and token[0] in (REFERENCE, NUMBER):
                interp.jump(interp.reference())
            raise_continue()
    interp.next_line()
    raise_continue()


class Continue(Exception):
    pass


def raise_continue():
    raise Continue()


def statement_goto(interp):
    interp.jump(interp.reference())
    raise_continue()


def statement_gosub(interp):
    target = interp.reference()
    if len(interp.gosubs) > 64:
        raise BasicError(50)
    interp.gosubs.append((interp.line, interp.position))
    interp.jump(target)
    raise_continue()


def statement_return(interp):
    if not interp.gosubs:
        raise BasicError(51)
    interp.line, interp.position = interp.gosubs.pop()


def statement_for(interp):
    target = interp.variable()
    if target[1] is not None or target[0].endswith("$"):
        raise BasicError(10)
    interp.expect("=")
    start = interp.number()
    if not interp.accept_keyword(T.TO):
        raise BasicError(10)
    end = interp.number()
    step = interp.number() if interp.accept_keyword(T.STEP) else 1.0
    interp.store(target, start)
    interp.fors = [frame for frame in interp.fors if frame[0] != target[0]]
    if len(interp.fors) > 32:
        raise BasicError(50)
    interp.fors.append((target[0], end, step, interp.line, interp.position))


def statement_next(interp):
    name = None
    if not interp.at_end():
        name = interp.variable()[0]
    while interp.fors:
        frame = interp.fors[-1]
        if name is None or frame[0] == name:
            break
        interp.fors.pop()
    if not interp.fors:
        raise BasicError(52)
    var, end, step, line, position = interp.fors[-1]
    value = interp.numbers.get(var, 0.0) + step
    interp.numbers[var] = value
    if (step >= 0 and value <= end) or (step < 0 and value >= end):
        interp.line, interp.position = line, position
        raise_continue()
    interp.fors.pop()


def statement_on(interp):
    if interp.accept_keyword(T.ERROR):
        if not interp.accept_keyword(T.GOTO):
            raise BasicError(10)
        target = interp.reference()
        interp.error_target = None if target == 0 else target
        return
    index = interp.integer()
    is_gosub = interp.accept_keyword(T.GOSUB)
    if not is_gosub and not interp.accept_keyword(T.GOTO):
        raise BasicError(10)
    targets = [interp.reference()]
    while interp.accept(","):
        targets.append(interp.reference())
    if 1 <= index <= len(targets):
        if is_gosub:
            interp.gosubs.append((interp.line, len(interp.tokens)))
        interp.jump(targets[index - 1])
        raise_continue()


def statement_resume(interp):
    if interp.error_resume is None:
        raise BasicError(70)
    line, position = interp.error_resume
    interp.error_resume = None
    if interp.at_end():
        interp.line, interp.position = line, position
        raise_continue()
    if interp.accept_keyword(T.NEXT):
        interp.line, interp.position = line, position
        skip_statement(interp)
        raise_continue()
    target = interp.reference()
    if target == 0:
        interp.line, interp.position = line, position
    else:
        interp.jump(target)
    raise_continue()


def skip_statement(interp):
    tokens = interp.tokens
    depth = 0
    index = interp.position
    while index < len(tokens):
        kind, value = tokens[index]
        if kind == SYMBOL and value == "(":
            depth += 1
        elif kind == SYMBOL and value == ")":
            depth -= 1
        elif kind == SYMBOL and value == ":" and depth <= 0:
            break
        index += 1
    interp.position = index


def statement_end(interp):
    raise Finished()


def statement_input(interp):
    if interp.at_symbol("#"):
        file = interp.open_file(interp.file_number())
        interp.accept(",")
        while True:
            target = interp.variable()
            if file.mode != "input" or file.position >= len(file.values):
                raise BasicError(87)
            text = file.values[file.position]
            file.position += 1
            if target[0].endswith("$"):
                interp.store(target, text[1:-1] if text[:1] == '"' and text[-1:] == '"' else text)
            else:
                interp.store(target, interp.parse_value(text))
            if not interp.accept(","):
                return
    groups = []
    while True:
        prompt = None
        token = interp.peek()
        if token is not None and token[0] == STRING:
            prompt = token[1]
            interp.position += 1
            if not (interp.accept(";") or interp.accept(",")):
                raise BasicError(10)
        targets = [interp.variable()]
        while interp.at_symbol(",") and interp.peek(1) is not None and interp.peek(1)[0] == NAME:
            interp.position += 1
            targets.append(interp.variable())
        groups.append((prompt, targets))
        if not interp.accept(","):
            break
    interp.input_groups = groups[1:]
    interp.begin_input(*groups[0])


def statement_wait(interp):
    interp.print_pause = "key" if interp.at_end() else max(0, interp.number())


def statement_beep(interp):
    count = interp.integer() if not interp.at_end() else 1
    if interp.accept(","):
        interp.number()
        if interp.accept(","):
            interp.number()
    interp.screen.beep(max(1, min(count, 20)))


def statement_dim(interp):
    while True:
        kind, name = interp.take()
        if kind != NAME:
            raise BasicError(10)
        interp.expect("(")
        dims = [interp.integer()]
        while interp.accept(","):
            dims.append(interp.integer())
        interp.expect(")")
        if interp.accept("*"):
            interp.integer()
        if name in interp.arrays:
            raise BasicError(30)
        size = 1
        for d in dims:
            if d < 0:
                raise BasicError(32)
            size *= d + 1
        interp.arrays[name] = (dims, [""] * size if name.endswith("$") else [0.0] * size)
        if not interp.accept(","):
            return


def statement_erase(interp):
    while True:
        kind, name = interp.take()
        if kind != NAME:
            raise BasicError(10)
        interp.arrays.pop(name, None)
        if not interp.accept(","):
            return


def statement_clear(interp):
    interp.numbers.clear()
    interp.strings.clear()
    interp.arrays.clear()


def statement_read(interp):
    while True:
        target = interp.variable()
        if interp.data_index >= len(interp.program.data):
            raise BasicError(53)
        text = interp.program.data[interp.data_index][1]
        interp.data_index += 1
        if target[0].endswith("$"):
            interp.store(target, text[1:-1] if text[:1] == '"' and text[-1:] == '"' else text)
        else:
            interp.store(target, interp.parse_value(text))
        if not interp.accept(","):
            return


def statement_restore(interp):
    if interp.at_end():
        interp.data_index = 0
        return
    target = interp.program.find(interp.reference())
    if target is None:
        raise BasicError(40)
    interp.data_index = next((i for i, (line, _) in enumerate(interp.program.data) if line >= target[0]), len(interp.program.data))


def statement_let(interp):
    interp.assign()


def statement_randomize(interp):
    random.seed(host.ticks_ms())


def statement_angle(mode):
    def handler(interp):
        interp.angle = mode
    return handler


def statement_using(interp):
    token = interp.peek()
    interp.using = interp.text_value() if token is not None and token[0] in (STRING, NAME) else None


def point_argument(interp):
    interp.expect("(")
    x = interp.integer()
    interp.expect(",")
    y = interp.integer()
    interp.expect(")")
    return x, y


def graphics_mode(interp, default):
    token = interp.peek()
    if token is not None and token[0] == NAME and token[1] in ("S", "R", "X"):
        interp.position += 1
        return token[1]
    return default


def statement_pset(interp, default="S"):
    x, y = point_argument(interp)
    mode = default
    if interp.accept(","):
        mode = graphics_mode(interp, default)
    interp.screen.pset(x, y, mode)
    interp.graphic_x, interp.graphic_y = x, y


def statement_preset(interp):
    statement_pset(interp, "R")


def statement_line(interp):
    if interp.at_symbol("("):
        x0, y0 = point_argument(interp)
    else:
        x0, y0 = interp.graphic_x, interp.graphic_y
    interp.expect("-")
    x1, y1 = point_argument(interp)
    mode = "S"
    box = None
    pattern = 0xFFFF
    while interp.accept(","):
        token = interp.peek()
        if token is None or interp.at_end():
            break
        if token[0] == NAME and token[1] in ("S", "R", "X"):
            mode = token[1]
            interp.position += 1
        elif token[0] == NAME and token[1] in ("B", "BF"):
            box = token[1]
            interp.position += 1
        elif token[0] == SYMBOL and token[1] == ",":
            continue
        else:
            pattern = interp.integer() & 0xFFFF
    screen = interp.screen
    if box == "BF":
        screen.box_fill(x0, y0, x1, y1, mode)
    elif box == "B":
        screen.line(x0, y0, x1, y0, mode, pattern)
        screen.line(x1, y0, x1, y1, mode, pattern)
        screen.line(x1, y1, x0, y1, mode, pattern)
        screen.line(x0, y1, x0, y0, mode, pattern)
    else:
        screen.line(x0, y0, x1, y1, mode, pattern)
    interp.graphic_x, interp.graphic_y = x1, y1


def statement_circle(interp):
    x, y = point_argument(interp)
    interp.expect(",")
    radius = interp.number()
    extras = []
    while interp.accept(","):
        extras.append(None if interp.at_symbol(",") or interp.at_end() else interp.number())
    start = extras[0] if len(extras) > 0 and extras[0] is not None else 0
    end = extras[1] if len(extras) > 1 and extras[1] is not None else 360
    ratio = extras[2] if len(extras) > 2 and extras[2] is not None else 1
    interp.screen.circle(x, y, radius, start, end, ratio)


def statement_gcursor(interp):
    interp.graphic_x, interp.graphic_y = point_argument(interp)


def statement_gprint(interp):
    while not interp.at_end():
        if interp.accept(";") or interp.accept(","):
            continue
        value = interp.expression()
        if isinstance(value, str):
            rows = [int(value[i:i + 2], 16) for i in range(0, len(value) - 1, 2)]
        else:
            rows = [int(value) & 0xFF]
        for row in rows:
            interp.screen.row(interp.graphic_x, interp.graphic_y, row)
            interp.graphic_y += 1


def statement_open(interp):
    name = interp.text_value()
    mode = "input"
    if interp.accept_keyword(T.FOR):
        if interp.accept_keyword(T.OUTPUT):
            mode = "output"
        elif interp.accept_keyword(T.FILE_INPUT) or interp.accept_keyword(T.INPUT):
            mode = "input"
        else:
            token = interp.take()
            if token[0] == NAME and token[1] == "APPEND":
                mode = "append"
            else:
                raise BasicError(10)
    if not interp.accept_keyword(T.AS):
        raise BasicError(10)
    number = interp.file_number()
    if number in interp.files:
        raise BasicError(86)
    if len(interp.files) >= MAX_FILES:
        raise BasicError(83)
    path = interp.path_for(name)
    if mode == "input":
        try:
            os.stat(path)
        except OSError:
            raise BasicError(94)
    interp.files[number] = File(path, mode)


def statement_close(interp):
    numbers = []
    while not interp.at_end():
        if interp.accept(","):
            continue
        numbers.append(interp.file_number())
    for number in numbers or list(interp.files):
        file = interp.files.pop(number, None)
        if file:
            file.close()


def statement_kill(interp):
    path = interp.path_for(interp.text_value())
    try:
        os.remove(path)
    except OSError:
        raise BasicError(94)


def statement_call(interp):
    raise BasicError(99)


STATEMENTS = {
    T.PRINT: statement_print, T.LOCATE: statement_locate, T.CLS: statement_cls, T.IF: statement_if,
    T.GOTO: statement_goto, T.GOSUB: statement_gosub, T.RETURN: statement_return, T.FOR: statement_for,
    T.NEXT: statement_next, T.ON: statement_on, T.RESUME: statement_resume, T.END: statement_end,
    T.STOP: statement_end, T.INPUT: statement_input, T.WAIT: statement_wait, T.BEEP: statement_beep,
    T.DIM: statement_dim, T.ERASE: statement_erase, T.CLEAR: statement_clear, T.READ: statement_read,
    T.RESTORE: statement_restore, T.LET: statement_let, T.RANDOMIZE: statement_randomize,
    T.DEGREE: statement_angle(math.pi / 180), T.RADIAN: statement_angle(1.0), T.GRAD: statement_angle(math.pi / 200),
    T.USING: statement_using, T.PSET: statement_pset, T.PRESET: statement_preset, T.LINE: statement_line,
    T.CIRCLE: statement_circle, T.GCURSOR: statement_gcursor, T.GPRINT: statement_gprint, T.OPEN: statement_open,
    T.CLOSE: statement_close, T.KILL: statement_kill, T.CALL: statement_call,
}
