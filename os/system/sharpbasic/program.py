from system.sharpbasic import tokens as T

KEYWORD = 0
NUMBER = 1
STRING = 2
NAME = 3
SYMBOL = 4
REFERENCE = 5
LABEL = 6
RAW = 7

TWO_CHAR = ("<=", ">=", "<>", "=<", "=>", "><")


class LoadError(Exception):
    pass


def latin(data):
    return "".join(chr(c) for c in data)


def _tag(data, tag):
    start = data.find(b"<" + tag + b">")
    if start < 0:
        return ""
    start += len(tag) + 2
    end = data.find(b"</" + tag + b">", start)
    return latin(data[start:end]).strip() if end > 0 else ""


class Line:
    __slots__ = ("number", "tokens", "labels")

    def __init__(self, number, tokens, labels):
        self.number = number
        self.tokens = tokens
        self.labels = labels


class Program:
    def __init__(self, title, description, lines):
        self.title = title
        self.description = description
        self.lines = lines
        self.by_number = {}
        self.by_label = {}
        self.data = []
        for index, line in enumerate(lines):
            self.by_number[line.number] = index
            for label, position in line.labels:
                self.by_label[label] = (index, position)
            for position, token in enumerate(line.tokens):
                if token[0] == RAW:
                    for item in _split_data(token[1]):
                        self.data.append((index, item))

    def find(self, target):
        if isinstance(target, str):
            return self.by_label.get(target)
        index = self.by_number.get(target)
        return None if index is None else (index, 0)


def load(path):
    with open(path, "rb") as f:
        data = f.read()
    if b"<SHARP WZD DATA>" not in data:
        raise LoadError("not a .wzd file")
    title = _tag(data, b"TITLE")
    description = _tag(data, b"DESCRIPTION")
    start = data.find(b"<BIN>\r\n")
    if start < 0 or not _tag(data, b"DATA").startswith("PFILE:"):
        raise LoadError("not a program")
    body = data[start + 7:]
    listing = body[body[0] + 1:]
    lines, end = parse_lines(listing)
    if len(listing) - end > 2:
        raise LoadError("machine code programs aren't supported")
    return Program(title, description, lines)


def parse_lines(listing):
    lines = []
    i = 0
    while i + 3 <= len(listing):
        number = listing[i] << 8 | listing[i + 1]
        length = listing[i + 2]
        body = listing[i + 3:i + 3 + length]
        if length == 0 or len(body) < length or body[-1] not in (0x0D, 0x0E, 0x0F):
            raise LoadError("damaged line after {}".format(lines[-1].number if lines else 0))
        tokens, labels = lex(body[:-1])
        lines.append(Line(number, tokens, labels))
        i += 3 + length
        if body[-1] == 0x0F:
            return lines, i
        if body[-1] == 0x0E:
            while i < len(listing) and listing[i] == 0xFF:
                i += 1
    raise LoadError("no end of program")


def _is_name_start(c):
    return 65 <= c <= 90 or 97 <= c <= 122


def _is_name_char(c):
    return 65 <= c <= 90 or 97 <= c <= 122 or 48 <= c <= 57


def _split_data(text):
    items = []
    current = ""
    quoted = False
    for char in text:
        if char == '"':
            quoted = not quoted
        elif char == "," and not quoted:
            items.append(current)
            current = ""
            continue
        current += char
    items.append(current)
    return [item.strip() for item in items]


def lex(body):
    out = []
    labels = []
    i = 0
    n = len(body)
    statement_start = True
    while i < n:
        c = body[i]
        if c == 0x20:
            i += 1
            continue
        if c == 0xFE and i + 1 < n:
            code = body[i + 1]
            i += 2
            if code == T.REM:
                break
            if code == T.DATA:
                out.append((RAW, latin(body[i:])))
                break
            out.append((KEYWORD, code))
            statement_start = code in (T.THEN, T.ELSE)
            continue
        if c == 0x1A and i + 2 < n:
            i += 3
            if i < n and body[i] == 0x2A:
                j = i + 1
                while j < n and _is_name_char(body[j]):
                    j += 1
                out.append((REFERENCE, latin(body[i:j])))
            else:
                j = i
                while j < n and 48 <= body[j] <= 57:
                    j += 1
                out.append((REFERENCE, int(latin(body[i:j])) if j > i else 0))
            i = j
            statement_start = False
            continue
        if c == 0x22:
            end = body.find(b'"', i + 1)
            if end < 0:
                end = n
            out.append((STRING, latin(body[i + 1:end])))
            i = end + 1
            statement_start = False
            continue
        if c == 0x27:
            break
        if c == 0x2A and statement_start:
            j = i + 1
            while j < n and _is_name_char(body[j]):
                j += 1
            labels.append(("*" + latin(body[i + 1:j]), len(out)))
            i = j
            continue
        if 48 <= c <= 57 or (c == 0x2E and i + 1 < n and 48 <= body[i + 1] <= 57):
            j = i
            while j < n and (48 <= body[j] <= 57 or body[j] == 0x2E):
                j += 1
            if j < n and body[j] in (0x45, 0x65) and j + 1 < n and (48 <= body[j + 1] <= 57 or body[j + 1] in (0x2B, 0x2D)):
                j += 2
                while j < n and 48 <= body[j] <= 57:
                    j += 1
            out.append((NUMBER, float(latin(body[i:j]))))
            i = j
            statement_start = False
            continue
        if c == 0x26 and i + 1 < n and body[i + 1] in (0x48, 0x68):
            j = i + 2
            while j < n and chr(body[j]) in "0123456789ABCDEFabcdef":
                j += 1
            out.append((NUMBER, float(int(latin(body[i + 2:j]), 16)) if j > i + 2 else 0.0))
            i = j
            statement_start = False
            continue
        if _is_name_start(c):
            j = i + 1
            while j < n and _is_name_char(body[j]):
                j += 1
            if j < n and body[j] == 0x24:
                j += 1
            out.append((NAME, latin(body[i:j]).upper()))
            i = j
            statement_start = False
            continue
        pair = latin(body[i:i + 2])
        if pair in TWO_CHAR:
            out.append((SYMBOL, {"=<": "<=", "=>": ">=", "><": "<>"}.get(pair, pair)))
            i += 2
            statement_start = False
            continue
        symbol = chr(c)
        out.append((SYMBOL, symbol))
        statement_start = symbol == ":"
        i += 1
    return out, labels
