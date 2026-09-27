import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "os"))

from system.sharpbasic.tokens import NAMES

KEYWORDS = {}
for code, name in sorted(NAMES.items()):
    KEYWORDS.setdefault(name, code)
BY_LENGTH = sorted(KEYWORDS, key=len, reverse=True)
JUMPS = ("GOTO", "GOSUB", "THEN", "ELSE", "RESTORE", "RESUME")


def encode_line(text):
    out = bytearray()
    i = 0
    after_jump = False
    while i < len(text):
        char = text[i]
        if char == '"':
            end = text.find('"', i + 1)
            end = len(text) if end < 0 else end + 1
            out += text[i:end].encode("latin-1")
            i = end
            after_jump = False
            continue
        if after_jump and char.isdigit():
            j = i
            while j < len(text) and text[j].isdigit():
                j += 1
            out += b"\x1a\x00\x00" + text[i:j].encode("latin-1")
            i = j
            after_jump = False
            continue
        upper = text[i:].upper()
        keyword = next((name for name in BY_LENGTH if upper.startswith(name)
                        and not (i > 0 and text[i - 1].isalnum())), None)
        if keyword:
            out += bytes((0xFE, KEYWORDS[keyword]))
            i += len(keyword)
            if keyword in ("REM", "DATA"):
                out += text[i:].encode("latin-1")
                break
            after_jump = keyword in JUMPS
            continue
        if char != " ":
            after_jump = False
        out += char.encode("latin-1")
        i += 1
    return bytes(out)


def encode(source):
    lines = []
    for raw in source.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        match = re.match(r"(\d+)\s*(.*)", raw)
        if not match:
            raise SystemExit("line without a number: " + raw)
        lines.append((int(match.group(1)), encode_line(match.group(2))))
    listing = bytearray()
    for index, (number, body) in enumerate(lines):
        terminator = 0x0F if index == len(lines) - 1 else 0x0D
        body = body + bytes((terminator,))
        listing += bytes((number >> 8, number & 0xFF, len(body))) + body
    return bytes(listing)


def main():
    source_path, output_path, title = sys.argv[1], sys.argv[2], sys.argv[3]
    description = sys.argv[4] if len(sys.argv) > 4 else ""
    listing = encode(open(source_path, encoding="latin-1").read())
    name = os.path.splitext(os.path.basename(output_path))[0].upper()[:8]
    header = ("<SHARP WZD DATA>\r\n<DATA TYPE>\r\nBASIC\r\n</DATA TYPE>\r\n<TITLE>\r\n{}\r\n</TITLE>\r\n"
              "<CATEGORY>\r\nPROGRAM\r\n</CATEGORY>\r\n<DESCRIPTION>\r\n{}\r\n</DESCRIPTION>\r\n"
              "<CONTENT>\r\nBIN_PROG_1\r\n</CONTENT>\r\n<DATA>\r\nPFILE:{}.BAS\r\n</DATA>\r\n<BIN>\r\n").format(
        title, description, name)
    with open(output_path, "wb") as output:
        output.write(header.encode("latin-1") + b"\x00" + listing)
    print("{}: {} bytes of BASIC".format(output_path, len(listing)))


if __name__ == "__main__":
    main()
