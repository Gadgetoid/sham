import host
import lcd
from system import gfx, icons, keys
from system.gfx import CLEAR, LIGHT, MID, INK, WIDTH, HEIGHT, small, large

HEADER_H = 12
ROW_H = small.height + 2
ICON_ROW_H = icons.SIZE + 1
BLINK_MS = 500

_dirty = True
_shell = None
_clipboard = ""

SYMBOLS = list("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~") + ["£", "€", "¥", "°", "±", "×", "÷", "§", "©", "®", "µ", "¿", "¡"]
MENU_SHORTCUTS = {keys.NEW: ("new",), keys.EDIT: ("edit",), keys.SEARCH: ("search", "find", "go to")}


def invalidate():
    global _dirty
    _dirty = True


def take_dirty():
    global _dirty
    dirty = _dirty
    _dirty = False
    return dirty


def push(screen):
    _shell.push(screen)


def pop():
    _shell.pop()


def home():
    _shell.go_home()


def _call(value):
    return value() if callable(value) else value


class View:
    focusable = True
    preferred_height = None

    def __init__(self):
        self.x = self.y = self.w = self.h = 0
        self.focused = False

    def place(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.layout()

    def layout(self):
        pass

    def focus(self, focused):
        self.focused = focused

    def draw(self):
        pass

    def key(self, key):
        return False

    def tick(self, now):
        pass

    def refresh(self):
        invalidate()

    def render(self):
        previous = lcd.clip(self.x, self.y, self.w, self.h)
        x0 = max(previous[0], self.x)
        y0 = max(previous[1], self.y)
        x1 = min(previous[0] + previous[2], self.x + self.w)
        y1 = min(previous[1] + previous[3], self.y + self.h)
        lcd.clip(x0, y0, max(0, x1 - x0), max(0, y1 - y0))
        try:
            self.draw()
        finally:
            lcd.clip(previous)

    def clear(self, colour=CLEAR):
        lcd.fill(self.x, self.y, self.w, self.h, colour)

    def text(self, text, x, y, colour=INK, type=small):
        return type.draw(text, self.x + x, self.y + y, colour)

    def icon(self, name, x, y, outline=INK, fill=CLEAR):
        icons.draw(name, self.x + x, self.y + y, outline, fill)

    def fill(self, x, y, w, h, colour=INK):
        lcd.fill(self.x + x, self.y + y, w, h, colour)

    def rect(self, x, y, w, h, colour=INK):
        lcd.rect(self.x + x, self.y + y, w, h, colour)

    def pixel(self, x, y, colour=INK):
        lcd.pixel(self.x + x, self.y + y, colour)

    def line(self, x0, y0, x1, y1, colour=INK):
        lcd.line(self.x + x0, self.y + y0, self.x + x1, self.y + y1, colour)

    def invert(self, x, y, w, h):
        lcd.invert(self.x + x, self.y + y, w, h)

    def sprite(self, rows, x, y, colour=INK):
        for dy, row in enumerate(rows):
            for dx, char in enumerate(row):
                if char == "#":
                    self.pixel(x + dx, y + dy, colour)

    def banner(self, *lines, bottom=False):
        width = max(small.measure(line) for line in lines) + 10
        height = len(lines) * small.line_height + 6
        x = (self.w - width) // 2
        y = self.h - height - 10 if bottom else (self.h - height) // 2
        self.fill(x, y, width, height, CLEAR)
        self.rect(x, y, width, height, INK)
        for index, line in enumerate(lines):
            self.text(line, x + (width - small.measure(line)) // 2, y + 3 + index * small.line_height)


class Label(View):
    focusable = False

    def __init__(self, text="", type=small, align="left", colour=INK):
        super().__init__()
        self.value = text
        self.type = type
        self.align = align
        self.colour = colour
        self.preferred_height = type.line_height + 1

    def set_text(self, text):
        self.value = text
        invalidate()

    def draw(self):
        text = self.type.fit(_call(self.value), self.w - 2)
        width = self.type.measure(text)
        x = {"left": 1, "center": (self.w - width) // 2, "right": self.w - width - 1}[self.align]
        self.text(text, x, 1, self.colour, self.type)


class Screen(View):
    modal = False

    def __init__(self, title="", body=None, status=None, menu=None, on_close=None):
        super().__init__()
        self.title = title
        self.body = body
        self.status = status
        self.menu = menu
        self.on_close = on_close
        self.place(0, 0, WIDTH, HEIGHT)

    def layout(self):
        if self.body:
            self.body.place(self.x, self.y + HEADER_H, self.w, self.h - HEADER_H)
            self.body.focus(True)

    def set_body(self, body):
        self.body = body
        self.layout()
        invalidate()

    def draw_header(self):
        status = _call(self.status) or ""
        status_w = small.measure(status)
        small.draw(small.fit(_call(self.title) or "", self.w - status_w - 8), self.x + 2, self.y)
        if status:
            small.draw(status, self.x + self.w - 2 - status_w, self.y)
        lcd.hline(self.x, self.y + HEADER_H - 2, self.w)

    def draw(self):
        self.draw_header()
        if self.body:
            self.body.render()

    def key(self, key):
        if self.body and self.body.key(key):
            return True
        if key.code == keys.MENU and self.menu:
            open_menu(_call(self.menu))
            return True
        if key.code in MENU_SHORTCUTS and self.menu:
            for label, action in _call(self.menu):
                if label.lower().startswith(MENU_SHORTCUTS[key.code]):
                    action()
                    return True
        return False

    def tick(self, now):
        if self.body:
            self.body.tick(now)


class Dialog(Screen):
    modal = True

    def __init__(self, title, body, width=180, height=None, on_close=None):
        View.__init__(self)
        self.title = title
        self.body = body
        self.status = None
        self.menu = None
        self.on_close = on_close
        height = height or HEADER_H + (body.preferred_height or 40) + 4
        height = min(HEIGHT - 4, height)
        self.place((WIDTH - width) // 2, (HEIGHT - height) // 2, width, height)

    def layout(self):
        self.body.place(self.x + 3, self.y + HEADER_H, self.w - 6, self.h - HEADER_H - 2)
        self.body.focus(True)

    def render(self):
        lcd.clip()
        lcd.fill(self.x + 2, self.y + 2, self.w, self.h, MID)
        lcd.fill(self.x, self.y, self.w, self.h, CLEAR)
        lcd.rect(self.x, self.y, self.w, self.h, INK)
        lcd.fill(self.x, self.y, self.w, HEADER_H - 1, INK)
        small.draw(small.fit(_call(self.title), self.w - 6), self.x + 3, self.y + 1, CLEAR)
        self.body.render()

    def key(self, key):
        if self.body.key(key):
            return True
        if key.code == keys.ESC:
            pop()
            return True
        return False


class List(View):
    def __init__(self, items=(), on_select=None, on_change=None, label=str, detail=None,
                 icon=None, numbered=False, empty="Nothing here"):
        super().__init__()
        self.items = list(items)
        self.on_select = on_select
        self.on_change = on_change
        self.label = label
        self.detail = detail
        self.icon_for = icon
        self.numbered = numbered
        self.empty = empty
        self.index = 0
        self.top = 0

    @property
    def row_height(self):
        return ICON_ROW_H if self.icon_for else ROW_H

    @property
    def rows(self):
        return max(1, self.h // self.row_height)

    @property
    def selected(self):
        return self.items[self.index] if self.items else None

    def set_items(self, items):
        self.items = list(items)
        self.select(min(self.index, max(0, len(self.items) - 1)), force=True)

    def select(self, index, force=False):
        index = max(0, min(index, len(self.items) - 1))
        changed = index != self.index
        self.index = index
        if self.index < self.top:
            self.top = self.index
        elif self.index >= self.top + self.rows:
            self.top = self.index - self.rows + 1
        self.top = max(0, min(self.top, len(self.items) - self.rows))
        if (changed or force) and self.on_change:
            self.on_change(self.selected, self.index)
        invalidate()

    def layout(self):
        if self.items:
            self.select(self.index)

    def activate(self):
        if self.on_select and self.items:
            self.on_select(self.selected, self.index)
            return True
        return False

    def jump_to_letter(self, char):
        char = char.lower()
        count = len(self.items)
        for step in range(1, count + 1):
            index = (self.index + step) % count
            if str(self.label(self.items[index]))[:1].lower() == char:
                self.select(index)
                return True
        return False

    def search(self):
        def find(text):
            needle = text.lower()
            count = len(self.items)
            for step in range(count):
                index = (self.index + step) % count
                if needle in str(self.label(self.items[index])).lower():
                    self.select(index)
                    return
            alert("No match for {}".format(text), title="Search")

        prompt("Search", find)

    def key(self, key):
        if key.code == keys.SEARCH and self.items:
            self.search()
            return True
        if key.second and key.code in (keys.UP, keys.DOWN) and self.items:
            self.select(0 if key.code == keys.UP else len(self.items) - 1)
            return True
        if not self.items:
            return False
        code = key.code
        if code == keys.UP:
            self.select(self.index - 1)
        elif code == keys.DOWN:
            self.select(self.index + 1)
        elif code == keys.PGUP:
            self.select(self.index - self.rows)
        elif code == keys.PGDN:
            self.select(self.index + self.rows)
        elif code == keys.HOME:
            self.select(0)
        elif code == keys.END:
            self.select(len(self.items) - 1)
        elif code == keys.ENTER:
            return self.activate()
        elif key.char and key.char.isdigit() and self.numbered:
            number = int(key.char)
            if 1 <= number <= len(self.items):
                self.select(number - 1)
                return self.activate()
            return False
        elif key.char and key.char.isalpha():
            return self.jump_to_letter(key.char)
        else:
            return False
        return True

    def draw(self):
        if not self.items:
            text = small.fit(self.empty, self.w - 4)
            self.text(text, (self.w - small.measure(text)) // 2, (self.h - small.height) // 2, MID)
            return
        row_h = self.row_height
        overflow = len(self.items) > self.rows
        content_w = self.w - (5 if overflow else 0)
        for row in range(self.rows):
            index = self.top + row
            if index >= len(self.items):
                break
            item = self.items[index]
            y = row * row_h
            x = 2
            if self.numbered:
                x += self.text(str(index + 1), x, y + (row_h - small.height) // 2, MID) + 3
            if self.icon_for:
                self.icon(self.icon_for(item), x, y + 1)
                x += icons.SIZE + 3
            right = content_w - 2
            if self.detail:
                detail = str(self.detail(item))
                right -= small.measure(detail)
                self.text(detail, right, y + (row_h - small.height) // 2)
                right -= 4
            label = small.fit(str(self.label(item)), right - x)
            self.text(label, x, y + (row_h - small.height) // 2)
            if index == self.index:
                if self.focused:
                    self.invert(0, y, content_w, row_h)
                else:
                    self.rect(0, y, content_w, row_h, MID)
        gfx.scrollbar(self.x + self.w - 3, self.y, self.h, len(self.items), self.rows, self.top)


class Grid(View):
    def __init__(self, items=(), on_select=None, label=str, icon=None, columns=2):
        super().__init__()
        self.items = list(items)
        self.on_select = on_select
        self.label = label
        self.icon_for = icon
        self.columns = columns
        self.index = 0

    @property
    def rows(self):
        return max(1, self.h // ICON_ROW_H)

    @property
    def per_page(self):
        return self.rows * self.columns

    @property
    def page(self):
        return self.index // self.per_page

    @property
    def pages(self):
        return max(1, (len(self.items) + self.per_page - 1) // self.per_page)

    def page_label(self):
        return "{}/{}".format(self.page + 1, self.pages)

    def select(self, index):
        if self.items:
            self.index = max(0, min(index, len(self.items) - 1))
            invalidate()

    def key(self, key):
        code = key.code
        position = self.index % self.per_page
        if code == keys.LEFT:
            self.select(self.index - self.rows if position >= self.rows else self.index - 1)
        elif code == keys.RIGHT:
            self.select(self.index + self.rows if position + self.rows < self.per_page else self.index + 1)
        elif code == keys.UP:
            self.select(self.index - 1)
        elif code == keys.DOWN:
            self.select(self.index + 1)
        elif code == keys.PGUP:
            self.select(self.index - self.per_page)
        elif code == keys.PGDN:
            self.select(self.index + self.per_page)
        elif code == keys.ENTER and self.items and self.on_select:
            self.on_select(self.items[self.index], self.index)
        elif key.char and key.char.isdigit() and key.char != "0":
            index = self.page * self.per_page + int(key.char) - 1
            if index < len(self.items):
                self.select(index)
                if self.on_select:
                    self.on_select(self.items[index], index)
        else:
            return False
        return True

    def draw(self):
        cell_w = self.w // self.columns
        first = self.page * self.per_page
        for position in range(self.per_page):
            index = first + position
            if index >= len(self.items):
                break
            item = self.items[index]
            x = (position // self.rows) * cell_w + 2
            y = (position % self.rows) * ICON_ROW_H + 1
            self.fill(x, y + 2, 9, small.height + 2, INK)
            number = str(position + 1)
            self.text(number, x + (10 - small.measure(number)) // 2, y + 3, CLEAR)
            if self.icon_for:
                self.icon(self.icon_for(item), x + 12, y)
            label_x = x + 13 + icons.SIZE
            label = small.fit(str(self.label(item)), cell_w - (label_x - x) - 4)
            self.text(label, label_x + 1, y + 3)
            if index == self.index:
                self.invert(label_x - 1, y + 1, cell_w - (label_x - x) - 2, small.height + 4)


class TextView(View):
    def __init__(self, text="", type=small):
        super().__init__()
        self.value = text
        self.type = type
        self.top = 0
        self._lines = None

    def set_text(self, text):
        self.value = text
        self.top = 0
        self._lines = None
        invalidate()

    def layout(self):
        self._lines = None

    @property
    def lines(self):
        if self._lines is None:
            self._lines = gfx.wrap(self.value, self.type, self.w - 6)
        return self._lines

    @property
    def rows(self):
        return max(1, (self.h - 1) // self.type.line_height)

    def scroll(self, top):
        top = max(0, min(top, len(self.lines) - self.rows))
        if top == self.top:
            return False
        self.top = top
        invalidate()
        return True

    def key(self, key):
        code = key.code
        if code == keys.UP:
            return self.scroll(self.top - 1)
        if code == keys.DOWN:
            return self.scroll(self.top + 1)
        if code == keys.PGUP:
            return self.scroll(self.top - self.rows)
        if code == keys.PGDN:
            return self.scroll(self.top + self.rows)
        if code == keys.HOME:
            return self.scroll(0)
        if code == keys.END:
            return self.scroll(len(self.lines))
        return False

    def draw(self):
        line_h = self.type.line_height
        for row, line in enumerate(self.lines[self.top:self.top + self.rows]):
            self.text(line, 1, row * line_h + 1, INK, self.type)
        gfx.scrollbar(self.x + self.w - 3, self.y, self.h, len(self.lines), self.rows, self.top)


class TextEdit(View):
    def __init__(self, text="", on_change=None, on_submit=None, multiline=True, type=small, placeholder="",
                 wrap=True, line_numbers=False, auto_indent=False):
        super().__init__()
        self.value = text
        self.cursor = len(text)
        self.on_change = on_change
        self.on_submit = on_submit
        self.multiline = multiline
        self.type = type
        self.placeholder = placeholder
        self.wrap = wrap and multiline
        self.gutter = small.measure("000") + 4 if line_numbers else 0
        self.auto_indent = auto_indent
        self.top = 0
        self.scroll_x = 0
        self.goal_x = None
        self.blink_on = True
        self.blink_at = 0
        self._spans = None
        self.preferred_height = type.line_height + 2

    def set_text(self, text):
        self.value = text
        self.cursor = len(text)
        self._spans = None
        invalidate()

    def layout(self):
        self._spans = None

    @property
    def spans(self):
        if self._spans is None:
            if self.wrap:
                self._spans = gfx.wrap_spans(self.value, self.type, self.w - 6 - self.gutter)
            elif self.multiline:
                self._spans = []
                start = 0
                for line in self.value.split("\n"):
                    self._spans.append((start, start + len(line)))
                    start += len(line) + 1
            else:
                self._spans = [(0, len(self.value))]
        return self._spans

    @property
    def rows(self):
        return max(1, (self.h - 1) // self.type.line_height)

    def line_of(self, cursor):
        spans = self.spans
        for line in range(len(spans) - 1, -1, -1):
            if spans[line][0] <= cursor:
                return line
        return 0

    def x_of(self, cursor):
        start = self.spans[self.line_of(cursor)][0]
        return self.type.measure(self.value[start:cursor])

    def cursor_at(self, line, x):
        spans = self.spans
        start, end = spans[line]
        soft_wrapped = line + 1 < len(spans) and spans[line + 1][0] == end
        if soft_wrapped:
            end -= 1
        used = 0
        for index in range(start, end):
            width = self.type.char_width(self.value[index])
            if used + width // 2 >= x:
                return index
            used += width
        return end

    def edited(self):
        self._spans = None
        if self.on_change:
            self.on_change(self.value)

    @property
    def line_index(self):
        return self.line_of(self.cursor)

    @property
    def column(self):
        return self.cursor - self.spans[self.line_index][0]

    def go_to_line(self, line):
        line = max(0, min(line, len(self.spans) - 1))
        self.cursor = self.spans[line][0]
        self.top = max(0, line - self.rows // 2)
        self.reveal()
        invalidate()

    def indentation(self):
        start = self.spans[self.line_index][0]
        line = self.value[start:self.cursor]
        indent = len(line) - len(line.lstrip(" "))
        if line.rstrip().endswith(":"):
            indent += 4
        return indent

    def insert(self, text):
        self.value = self.value[:self.cursor] + text + self.value[self.cursor:]
        self.cursor += len(text)
        self.edited()

    def move_line(self, delta):
        line = self.line_of(self.cursor) + delta
        if line < 0 or line >= len(self.spans):
            return False
        if self.goal_x is None:
            self.goal_x = self.x_of(self.cursor)
        self.cursor = self.cursor_at(line, self.goal_x)
        return True

    def key(self, key):
        if key.second and key.code in (keys.UP, keys.DOWN):
            self.cursor = 0 if key.code == keys.UP else len(self.value)
            self.goal_x = None
            self.reveal()
            invalidate()
            return True
        global _clipboard
        if key.code in (keys.CUT, keys.COPY):
            start, end = self.spans[self.line_index]
            _clipboard = self.value[start:end]
            if key.code == keys.CUT:
                cut_end = end + 1 if end < len(self.value) and self.value[end:end + 1] == "\n" else end
                self.value = self.value[:start] + self.value[cut_end:]
                self.cursor = start
                self.edited()
            invalidate()
            return True
        if key.code == keys.PASTE:
            if _clipboard:
                self.insert(_clipboard if self.multiline else _clipboard.replace("\n", " "))
                invalidate()
            return True
        if key.code == keys.CASE:
            if self.cursor > 0:
                char = self.value[self.cursor - 1]
                flipped = char.lower() if char.isupper() else char.upper()
                self.value = self.value[:self.cursor - 1] + flipped + self.value[self.cursor:]
                self.edited()
                invalidate()
            return True
        if key.code == keys.SMBL:
            choose("Symbol", SYMBOLS, lambda symbol, index: (self.insert(symbol), invalidate()))
            return True
        code = key.code
        char = key.char
        keep_goal = False
        if char:
            self.insert(char)
        elif code == keys.BACKSPACE:
            if self.cursor == 0:
                return True
            start = self.spans[self.line_index][0]
            before = self.value[start:self.cursor]
            remove = 1
            if self.auto_indent and before and not before.strip(" "):
                remove = (len(before) - 1) % 4 + 1
            self.value = self.value[:self.cursor - remove] + self.value[self.cursor:]
            self.cursor -= remove
            self.edited()
        elif code == keys.DELETE:
            self.value = self.value[:self.cursor] + self.value[self.cursor + 1:]
            self.edited()
        elif code == keys.LEFT:
            if self.cursor == 0:
                return False
            self.cursor -= 1
        elif code == keys.RIGHT:
            if self.cursor >= len(self.value):
                return False
            self.cursor += 1
        elif code == keys.UP or code == keys.DOWN:
            if not self.move_line(-1 if code == keys.UP else 1):
                return False
            keep_goal = True
        elif code == keys.HOME:
            self.cursor = self.spans[self.line_of(self.cursor)][0]
        elif code == keys.END:
            line = self.line_of(self.cursor)
            self.cursor = self.cursor_at(line, 10000)
        elif code == keys.ENTER:
            if self.multiline:
                self.insert("\n" + " " * (self.indentation() if self.auto_indent else 0))
            elif self.on_submit:
                self.on_submit(self.value)
            else:
                return False
        else:
            return False
        if not keep_goal:
            self.goal_x = None
        self.blink_on = True
        self.blink_at = host.ticks_ms()
        self.reveal()
        invalidate()
        return True

    def reveal(self):
        line = self.line_of(self.cursor)
        if line < self.top:
            self.top = line
        elif line >= self.top + self.rows:
            self.top = line - self.rows + 1
        if not self.wrap:
            x = self.x_of(self.cursor)
            visible = self.w - 6 - self.gutter
            if x - self.scroll_x > visible:
                self.scroll_x = x - visible + visible // 3
            elif x < self.scroll_x:
                self.scroll_x = max(0, x - visible // 3)

    def tick(self, now):
        if self.focused and now - self.blink_at >= BLINK_MS:
            self.blink_at = now
            self.blink_on = not self.blink_on
            invalidate()

    def draw(self):
        line_h = self.type.line_height
        offset = 1 + self.gutter - self.scroll_x
        if not self.value and self.placeholder:
            self.text(self.placeholder, offset + 1, 1, MID, self.type)
        spans = self.spans
        for row in range(self.rows):
            line = self.top + row
            if line >= len(spans):
                break
            start, end = spans[line]
            self.text(self.value[start:end], offset, row * line_h + 1, INK, self.type)
        if self.focused and self.blink_on:
            row = self.line_of(self.cursor) - self.top
            if 0 <= row < self.rows:
                self.fill(offset + self.x_of(self.cursor), row * line_h, 1, line_h, INK)
        if self.gutter:
            self.fill(0, 0, self.gutter, self.h, CLEAR)
            self.fill(self.gutter - 2, 0, 1, self.h, LIGHT)
            for row in range(self.rows):
                line = self.top + row
                if line >= len(spans):
                    break
                number = str(line + 1)
                self.text(number, self.gutter - 4 - small.measure(number), row * line_h + 1, MID)
        if self.multiline:
            gfx.scrollbar(self.x + self.w - 3, self.y, self.h, len(spans), self.rows, self.top)


class Split(View):
    def __init__(self, first, second, ratio=0.4, vertical=False, size=None):
        super().__init__()
        self.panes = [first, second]
        self.ratio = ratio
        self.vertical = vertical
        self.size = size
        self.active = 0 if first.focusable else 1

    def layout(self):
        first, second = self.panes
        if self.vertical:
            size = self.size or first.preferred_height or int(self.h * self.ratio)
            first.place(self.x, self.y, self.w, size)
            second.place(self.x, self.y + size + 2, self.w, self.h - size - 2)
        else:
            size = self.size or int(self.w * self.ratio)
            first.place(self.x, self.y, size, self.h)
            second.place(self.x + size + 3, self.y, self.w - size - 3, self.h)
        self.focus(self.focused)

    def focus(self, focused):
        self.focused = focused
        for index, pane in enumerate(self.panes):
            pane.focus(focused and index == self.active)

    def switch(self, index):
        if self.panes[index].focusable and index != self.active:
            self.active = index
            self.focus(self.focused)
            invalidate()
            return True
        return False

    def key(self, key):
        if self.panes[self.active].key(key):
            return True
        back, forward = (keys.UP, keys.DOWN) if self.vertical else (keys.LEFT, keys.RIGHT)
        if key.code == forward:
            return self.switch(1)
        if key.code == back:
            return self.switch(0)
        return False

    def tick(self, now):
        for pane in self.panes:
            pane.tick(now)

    def draw(self):
        first, second = self.panes
        first.render()
        second.render()
        if self.vertical:
            lcd.hline(self.x, second.y - 2, self.w, MID)
        else:
            lcd.vline(second.x - 2, self.y, self.h, MID)


class Stack(View):
    def __init__(self, *children):
        super().__init__()
        self.children = list(children)
        self.active = next((i for i, c in enumerate(children) if c.focusable), 0)

    def layout(self):
        fixed = sum(c.preferred_height for c in self.children if c.preferred_height)
        flexible = [c for c in self.children if not c.preferred_height]
        share = (self.h - fixed) // len(flexible) if flexible else 0
        y = self.y
        for child in self.children:
            height = child.preferred_height or share
            child.place(self.x, y, self.w, height)
            y += height
        self.focus(self.focused)

    def focus(self, focused):
        self.focused = focused
        for index, child in enumerate(self.children):
            child.focus(focused and index == self.active)

    def key(self, key):
        if self.children[self.active].key(key):
            return True
        step = {keys.UP: -1, keys.DOWN: 1}.get(key.code)
        if step is None:
            return False
        index = self.active + step
        while 0 <= index < len(self.children):
            if self.children[index].focusable:
                self.active = index
                self.focus(self.focused)
                invalidate()
                return True
            index += step
        return False

    def tick(self, now):
        for child in self.children:
            child.tick(now)

    def draw(self):
        for child in self.children:
            child.render()


class Field:
    def __init__(self, label, value="", choices=None, numeric=False, name=None, on_change=None, picker=None):
        self.label = label
        self.name = name or label.lower().replace(" ", "_")
        self.choices = choices
        self.numeric = numeric
        self.on_change = on_change
        self.picker = picker
        self.value = str(value) if value is not None else ""
        if choices and self.value not in choices:
            self.value = choices[0]
        self.cursor = len(self.value)

    def cycle(self, step):
        index = (self.choices.index(self.value) + step) % len(self.choices)
        self.set(self.choices[index])

    def set(self, value, cursor=None):
        self.value = value
        self.cursor = len(value) if cursor is None else max(0, min(cursor, len(value)))
        if self.on_change:
            self.on_change(value)


class Form(View):
    def __init__(self, fields, on_submit=None):
        super().__init__()
        self.fields = list(fields)
        self.on_submit = on_submit
        self.index = 0
        self.top = 0
        self.blink_on = True
        self.blink_at = 0
        self.label_w = max(small.measure(f.label) for f in self.fields) + 6
        self.preferred_height = len(self.fields) * ROW_H

    @property
    def rows(self):
        return max(1, self.h // ROW_H)

    @property
    def field(self):
        return self.fields[self.index]

    def values(self):
        return {f.name: f.value for f in self.fields}

    def move(self, index):
        if not 0 <= index < len(self.fields):
            return False
        self.index = index
        if self.index < self.top:
            self.top = self.index
        elif self.index >= self.top + self.rows:
            self.top = self.index - self.rows + 1
        invalidate()
        return True

    def key(self, key):
        field = self.field
        code = key.code
        char = key.char
        if key.second and code in (keys.UP, keys.DOWN):
            return self.move(0 if code == keys.UP else len(self.fields) - 1)
        if code == keys.UP:
            return self.move(self.index - 1)
        if code == keys.DOWN:
            return self.move(self.index + 1)
        if code == keys.ENTER:
            if self.index < len(self.fields) - 1:
                return self.move(self.index + 1)
            if self.on_submit:
                self.on_submit(self.values())
                return True
            return False
        if field.choices:
            if code in (keys.LEFT, keys.RIGHT) or char == " ":
                field.cycle(-1 if code == keys.LEFT else 1)
            elif char:
                for choice in field.choices:
                    if choice[:1].lower() == char.lower():
                        field.set(choice)
                        break
            else:
                return False
        elif not self.edit_text(field, key):
            return False
        self.blink_on = True
        self.blink_at = host.ticks_ms()
        invalidate()
        return True

    def edit_text(self, field, key):
        global _clipboard
        code, char = key.code, key.char
        if code == keys.PICK and field.picker:
            field.picker(field)
            return True
        value, cursor = field.value, min(field.cursor, len(field.value))
        if char:
            if field.numeric and char not in "0123456789.-":
                return True
            field.set(value[:cursor] + char + value[cursor:], cursor + 1)
        elif code == keys.BACKSPACE:
            if cursor:
                field.set(value[:cursor - 1] + value[cursor:], cursor - 1)
        elif code == keys.DELETE:
            field.set(value[:cursor] + value[cursor + 1:], cursor)
        elif code == keys.LEFT:
            field.cursor = max(0, cursor - 1)
        elif code == keys.RIGHT:
            field.cursor = min(len(value), cursor + 1)
        elif code == keys.HOME:
            field.cursor = 0
        elif code == keys.END:
            field.cursor = len(value)
        elif code in (keys.CUT, keys.COPY):
            _clipboard = value
            if code == keys.CUT:
                field.set("", 0)
        elif code == keys.PASTE:
            field.set(value[:cursor] + _clipboard.replace("\n", " ") + value[cursor:], cursor + len(_clipboard))
        elif code == keys.CASE:
            if cursor:
                letter = value[cursor - 1]
                letter = letter.lower() if letter.isupper() else letter.upper()
                field.set(value[:cursor - 1] + letter + value[cursor:], cursor)
        elif code == keys.SMBL:
            def insert(symbol, index):
                current = min(field.cursor, len(field.value))
                field.set(field.value[:current] + symbol + field.value[current:], current + 1)
                invalidate()
            choose("Symbol", SYMBOLS, insert)
        else:
            return False
        return True

    def tick(self, now):
        if self.focused and not self.field.choices and now - self.blink_at >= BLINK_MS:
            self.blink_at = now
            self.blink_on = not self.blink_on
            invalidate()

    def draw(self):
        value_w = self.w - self.label_w - 4
        for row in range(self.rows):
            index = self.top + row
            if index >= len(self.fields):
                break
            field = self.fields[index]
            y = row * ROW_H
            selected = index == self.index and self.focused
            self.text(field.label, 2, y + 1, INK if selected else MID)
            value = field.value
            if field.choices and selected:
                value = "< {} >".format(value)
            if not field.choices and selected:
                cursor = min(field.cursor, len(value))
                start = 0
                while start < cursor and small.measure(value[start:cursor]) > value_w - 6:
                    start += 1
                shown = value[start:]
                while shown and small.measure(shown) > value_w - 4:
                    shown = shown[:-1]
                self.text(shown, self.label_w + 1, y + 1)
                if self.blink_on:
                    caret = self.label_w + 1 + small.measure(value[start:cursor])
                    self.fill(caret, y, 1, ROW_H - 1, INK)
            else:
                self.text(small.fit(value, value_w - 2), self.label_w + 1, y + 1)
            if selected:
                self.invert(self.label_w - 1, y, value_w + 2, ROW_H - 1)
            else:
                lcd.hline(self.x + self.label_w - 1, self.y + y + ROW_H - 2, value_w + 2, LIGHT)
        gfx.scrollbar(self.x + self.w - 3, self.y, self.h, len(self.fields), self.rows, self.top)


class Canvas(View):
    retain = False

    def __init__(self, paint=None, step=None, key=None, retain=None):
        super().__init__()
        self._paint = paint
        self._step = step
        self._key = key
        if retain is not None:
            self.retain = retain
        self._snapshot = None
        self._painted = False

    def paint(self):
        if self._paint:
            self._paint(self)

    def step(self, now):
        if self._step:
            self._step(self, now)

    def key(self, key):
        return bool(self._key and self._key(self, key))

    def restart(self):
        self._snapshot = None
        self._painted = False
        invalidate()

    def draw(self):
        if self.retain and self._snapshot:
            lcd.blit(self._snapshot, self.x, self.y, self.w, self.h)
        else:
            self.clear()
            self.paint()
            self._painted = True

    def tick(self, now):
        if not self._painted:
            return
        previous = lcd.clip(self.x, self.y, self.w, self.h)
        try:
            self.step(now)
        finally:
            lcd.clip(previous)
        if self.retain:
            self._snapshot = lcd.grab(self.x, self.y, self.w, self.h)


class Message(View):
    def __init__(self, text, hint=None):
        super().__init__()
        self.lines = gfx.wrap(text, small, 168)
        self.hint = hint
        self.preferred_height = (len(self.lines) + (1 if hint else 0)) * small.line_height + 4

    def draw(self):
        for row, line in enumerate(self.lines):
            self.text(line, 1, row * small.line_height + 2)
        if self.hint:
            self.text(self.hint, 1, len(self.lines) * small.line_height + 2, MID)


class _Alert(Dialog):
    def __init__(self, text, title, on_close):
        super().__init__(title, Message(text, "Enter: OK"), on_close=on_close)

    def key(self, key):
        if key.code in (keys.ENTER, keys.ESC):
            pop()
        return True


class _Confirm(Dialog):
    def __init__(self, text, title, on_yes):
        super().__init__(title, Message(text, "Enter: yes  Esc: no"))
        self.on_yes = on_yes

    def key(self, key):
        if key.code == keys.ENTER or key.char in ("y", "Y"):
            pop()
            self.on_yes()
        elif key.code == keys.ESC or key.char in ("n", "N"):
            pop()
        return True


class _Prompt(Dialog):
    def __init__(self, title, text, on_done):
        self.editor = TextEdit(text, multiline=False, on_submit=self.submit)
        super().__init__(title, self.editor)
        self.on_done = on_done

    def submit(self, value):
        pop()
        self.on_done(value)


class _Choose(Dialog):
    def __init__(self, title, options, on_pick, label):
        self.listing = List(options, on_select=self.pick, label=label)
        self.listing.preferred_height = min(len(options), 4) * ROW_H + 1
        super().__init__(title, self.listing, width=140)
        self.on_pick = on_pick

    def pick(self, option, index):
        pop()
        self.on_pick(option, index)


def alert(text, title="Note", on_close=None):
    push(_Alert(text, title, on_close))


def confirm(text, on_yes, title="Confirm"):
    push(_Confirm(text, title, on_yes))


def prompt(title, on_done, text=""):
    push(_Prompt(title, text, on_done))


def choose(title, options, on_pick, label=str):
    push(_Choose(title, options, on_pick, label))


def open_menu(entries):
    choose("Menu", entries, lambda entry, index: entry[1](), label=lambda entry: entry[0])


class CalendarPopup(Screen):
    modal = True
    POPUP_W = 118

    def __init__(self, day, on_pick):
        View.__init__(self)
        from system import dates
        self.dates = dates
        self.day = day
        self.on_pick = on_pick
        self.title = ""
        self.body = None
        self.status = None
        self.menu = None
        self.on_close = None
        self.place(WIDTH - self.POPUP_W, 0, self.POPUP_W, HEIGHT)

    def layout(self):
        pass

    def shift_month(self, step):
        year, month, day = self.dates.from_days(self.day)
        month += step
        year += (month - 1) // 12
        month = (month - 1) % 12 + 1
        while day > 28 and self.dates.parse_iso("{:04d}-{:02d}-{:02d}".format(year, month, day)) is None:
            day -= 1
        self.day = self.dates.to_days(year, month, day)
        invalidate()

    def key(self, key):
        code = key.code
        if code in (keys.UP, keys.DOWN) and key.lid or code in (keys.PGUP, keys.PGDN):
            self.shift_month(-1 if code in (keys.UP, keys.PGUP) else 1)
            return True
        steps = {keys.LEFT: -1, keys.RIGHT: 1, keys.UP: -7, keys.DOWN: 7}
        if code in steps:
            self.day += steps[code]
            invalidate()
        elif key.char in ("t", "T"):
            self.day = self.dates.today()
            invalidate()
        elif code in (keys.ENTER, keys.PICK):
            pop()
            self.on_pick(self.day)
        elif code == keys.ESC:
            pop()
        return True

    def render(self):
        from system import timefmt
        lcd.clip()
        x0, w = self.x, self.w
        lcd.fill(x0, 0, w, HEIGHT, CLEAR)
        lcd.rect(x0, 0, w, HEIGHT, INK)
        lcd.rect(x0 + 1, 0, w - 2, HEIGHT, INK)
        year, month, _ = self.dates.from_days(self.day)
        start = self.dates.to_days(year, month, 1)
        next_start = self.dates.to_days(year + (month == 12), month % 12 + 1, 1)
        length = next_start - start
        first = timefmt.week_start()
        offset = (self.dates.weekday(start) - first) % 7
        heading = "{}  {}".format(timefmt.MONTHS[month - 1], year)
        small.draw(heading, x0 + (w - small.measure(heading)) // 2, 1)
        cell_w = (w - 4) // 7
        left = x0 + 2 + (w - 4 - cell_w * 7) // 2
        names = "MTWTFSS"
        for column in range(7):
            name = names[(first + column) % 7]
            small.draw(name, left + column * cell_w + (cell_w - small.measure(name)) // 2, 11)
        lcd.hline(x0 + 2, 21, w - 4, INK)
        weeks = (offset + length + 6) // 7
        row_h = max(9, (HEIGHT - 24) // max(5, weeks))
        today = self.dates.today()
        for index in range(length):
            slot = offset + index
            cx = left + (slot % 7) * cell_w
            cy = 23 + (slot // 7) * row_h
            label = str(index + 1)
            small.draw(label, cx + cell_w - 1 - small.measure(label), cy)
            day = start + index
            if day == today:
                lcd.hline(cx + 1, cy + small.height + 1, cell_w - 1, MID)
            if day == self.day:
                lcd.invert(cx, cy - 1, cell_w, small.height + 2)


def pick_date(day, on_pick, title="Date"):
    push(CalendarPopup(day, on_pick))


def date_picker(parse, format):
    def open_picker(field):
        from system import dates
        day = parse(field.value)
        pick_date(day if day is not None else dates.today(), lambda chosen: field.set(format(chosen)))
    return open_picker
