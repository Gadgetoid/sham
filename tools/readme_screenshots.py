import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "docs", "screenshots")
BINARY = os.path.join(ROOT, "sham.exe" if os.path.exists(os.path.join(ROOT, "sham.exe")) else "sham")
OS_DIR = os.path.join(ROOT, "os")
SAMPLE_WZD = os.path.join(OS_DIR, "samples", "wzd", "Sierpinski.wzd")

TIMEZONE = "Europe/London"
MOMENT = (2026, 6, 12, 9, 41, 20)
STARTUP_SECONDS = 1.5
LCD_CELL = 3
LCD_COLOURS = 16
DEVICE_WIDTH = 800
DEVICE_COLOURS = 256
KEY_START_FRAME = 60
KEY_INTERVAL = 4
SETTLE_FRAMES = 60

OWNER = {"name": "Ada Lovelace", "number": "01632 960001", "address": "12 St James Square, London"}

PREFS = {
    "sound": False,
    "click": False,
    "home_city": "London",
    "daily_alarm": True,
    "owner": OWNER,
}

ALARMS = [
    {"on": True, "time": "07:00", "repeat": "Daily", "label": "Wake up"},
    {"on": False, "time": "13:30", "repeat": "Once", "label": "Lunch"},
]

SCHEDULE = [
    {"date": "2026-06-12", "time": "10:00", "title": "Stand-up", "alarm": True},
    {"date": "2026-06-12", "time": "12:30", "title": "Lunch with Grace"},
    {"date": "2026-06-12", "time": "16:00", "title": "Engine notes review"},
    {"date": "2026-06-13", "time": "09:30", "title": "Park run"},
    {"date": "2026-06-15", "time": "14:00", "title": "Dentist", "alarm": True},
]

MEMOS = [
    "Shopping\nMilk, eggs, flour\nBatteries (CR2032)\nString for the kite",
    "Ideas\nA pocket loom that punches its own cards.",
    "Books to read\nThe Difference Engine\nCryptonomicon",
]

EXPENSES = [
    {"date": "2026-06-10", "amount": "4.20", "note": "Coffee"},
    {"date": "2026-06-11", "amount": "32.00", "note": "Train"},
]

SILENCE = "host.sound(False); host.key_click(False)"
DUNGEON_TURNS = 200


DUNGEON_WALK = ("exec(" + repr("view = shell.top().body\n"
                              "game = view.game\n"
                              "for turn in range({}):\n"
                              "    distances = game.distances_from(*game.stairs)\n"
                              "    here = distances[game.index(game.player_x, game.player_y)]\n"
                              "    if here <= 3 or game.dead:\n"
                              "        break\n"
                              "    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n"
                              "        if distances[game.index(game.player_x + dx, game.player_y + dy)] < here:\n"
                              "            game.take_turn(dx, dy)\n"
                              "            break\n"
                              "view.after_turn()\n".format(DUNGEON_TURNS)) + "); ")


SNAKE_SETUP = ("exec(" + repr("view = shell.top().body\n"
                              "path = []\n"
                              "for row in range(4):\n"
                              "    columns = range(12, 40) if row % 2 == 0 else range(39, 11, -1)\n"
                              "    for column in columns:\n"
                              "        path.append((column, 6 + row * 3))\n"
                              "    if row < 3:\n"
                              "        edge = 39 if row % 2 == 0 else 12\n"
                              "        path += [(edge, 7 + row * 3), (edge, 8 + row * 3)]\n"
                              "view.body = list(reversed(path[-84:]))\n"
                              "view.direction = (-1, 0) if view.body[0][0] < view.body[1][0] else (1, 0)\n"
                              "view.score = 80\n"
                              "view.food = (20, 20)\n"
                              "view.state = 'playing'\n"
                              "view.interval = 10 ** 9\n") + "); ")

BLOCKS_SETUP = ("exec(" + repr("import random\n"
                               "view = shell.top().body\n"
                               "view.state = 'playing'\n"
                               "rows = len(view.board)\n"
                               "columns = len(view.board[0])\n"
                               "for row in range(rows - 7, rows):\n"
                               "    gap = random.randrange(columns)\n"
                               "    view.board[row] = [0 if column == gap or random.randrange(9) == 0 else 1 for column in range(columns)]\n"
                               "view.score = 1260\n"
                               "view.lines = 14\n") + "); ")


def launch(app, seed=None, extra=""):
    seeding = "import random; random.seed({}); ".format(seed) if seed is not None else ""
    return "{}; {}shell.launch({!r}); {}ui.invalidate()".format(SILENCE, seeding, app, extra)


LCD_SHOTS = [
    {"name": "launcher", "exec": SILENCE + "; ui.invalidate()"},
    {"name": "launcher_unlit", "exec": SILENCE + "; host.backlight(False); ui.invalidate()"},
    {"name": "games", "exec": SILENCE + "; shell.open_folder('Games')"},
    {"name": "options", "exec": launch("options")},
    {"name": "owner", "exec": SILENCE + "; shell.push(__import__('system.shell').shell.OwnerSplash(prefs.get('owner')))"},
    {"name": "tel", "exec": launch("tel")},
    {"name": "schedule", "exec": launch("schedule")},
    {"name": "clock", "exec": launch("clock")},
    {"name": "world", "exec": launch("world")},
    {"name": "memo", "exec": launch("memo"), "keys": "{ENTER}"},
    {"name": "calc", "exec": launch("calc"), "keys": "12.5*8+3{ENTER}"},
    {"name": "guide", "exec": launch("guide"), "keys": "{DOWN}{DOWN}{DOWN}{ENTER}{ENTER}"},
    {"name": "charmap", "exec": launch("charmap")},
    {"name": "patterns", "exec": launch("patterns"), "keys": "{RIGHT}{RIGHT}{RIGHT}{RIGHT}{RIGHT}{RIGHT}{RIGHT}{RIGHT}{RIGHT}{RIGHT}{RIGHT}"},
    {"name": "dungeon", "exec": launch("dungeon", seed=11, extra=DUNGEON_WALK)},
    {"name": "solitaire", "exec": launch("solitaire", seed=3)},
    {"name": "mines", "exec": launch("mines", seed=5), "keys": "{ENTER}"},
    {"name": "blocks", "exec": launch("blocks", seed=2, extra=BLOCKS_SETUP), "keys": "{LEFT}{LEFT}{UP}"},
    {"name": "snake", "exec": launch("snake", seed=4, extra=SNAKE_SETUP)},
    {"name": "sharp_basic", "exec": SILENCE + "; import apps.sharp; apps.sharp.run('/data/wzd/Sierpinski.wzd'); ui.invalidate()",
     "frames": 1500},
]

DEVICE_SHOTS = [
    {"name": "device", "args": ["--layout=3", "--no-compact", "--size=620x620"]},
    {"name": "device_compact", "args": ["--layout=3", "--compact", "--size=620x620"]},
]


def moment_offset():
    target = time.mktime(MOMENT + (0, 0, -1))
    return int(target - time.time() - STARTUP_SECONDS)


def seed_data(data, wzd):
    os.makedirs(os.path.join(data, "wzd"))
    prefs = dict(PREFS, clock_offset=moment_offset())
    stores = {"prefs": prefs, "alarms": ALARMS, "schedule": SCHEDULE, "memo": MEMOS, "expense": EXPENSES}
    for name, value in stores.items():
        with open(os.path.join(data, name + ".json"), "w") as output:
            json.dump(value, output)
    if wzd:
        shutil.copy(wzd, os.path.join(data, "wzd"))


def frames_for(shot):
    count = len(re.findall(r"\{[^}]*\}|.", shot.get("keys", "")))
    return max(shot.get("frames", 0), KEY_START_FRAME + count * KEY_INTERVAL + SETTLE_FRAMES)


def run(arguments, data):
    environment = dict(os.environ, TZ=TIMEZONE)
    result = subprocess.run([BINARY, "--root=" + OS_DIR, "--data=" + data, "--no-watch", "--no-repl", "--response=0"]
                            + arguments, capture_output=True, text=True, env=environment, timeout=120)
    output = result.stdout + result.stderr
    if result.returncode != 0 or "Traceback" in output:
        sys.exit("sham failed for {}\n{}".format(arguments, output))


def quantise(source, target, colours, dither=True):
    subprocess.run(["pngquant", "--force"] + ([] if dither else ["--nofs"]) + [str(colours), "--output", target, source], check=True)


def png_chunk(tag, body):
    return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)


def write_png(path, width, height, rows):
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    raw = b"".join(b"\x00" + row for row in rows)
    with open(path, "wb") as output:
        output.write(b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", header) + png_chunk(b"IDAT", zlib.compress(raw, 9)) + png_chunk(b"IEND", b""))


def unpremultiplied_png(bmp_path, png_path):
    data = open(bmp_path, "rb").read()
    offset = struct.unpack_from("<I", data, 10)[0]
    width, height = struct.unpack_from("<ii", data, 18)
    masks = struct.unpack_from("<IIII", data, 54)
    shifts = [(mask & -mask).bit_length() - 1 for mask in masks]
    top_down = height < 0
    height = abs(height)
    rows = []
    for y in range(height):
        source_row = y if top_down else height - 1 - y
        row = bytearray()
        for pixel in struct.iter_unpack("<I", data[offset + source_row * width * 4:offset + (source_row + 1) * width * 4]):
            red, green, blue, alpha = [(pixel[0] >> shift) & 0xFF for shift in shifts]
            if alpha:
                red, green, blue = [min(255, round(channel * 255 / alpha)) for channel in (red, green, blue)]
            row += bytes((red, green, blue, alpha))
        rows.append(bytes(row))
    write_png(png_path, width, height, rows)


def lcd_shot(shot, work, wzd):
    data = os.path.join(work, shot["name"])
    seed_data(data, wzd)
    bmp = os.path.join(work, shot["name"] + ".bmp")
    arguments = ["--layout=0", "--lcd=" + bmp, "--lcd-cell={}".format(LCD_CELL), "--frames={}".format(frames_for(shot)),
                 "--exec=" + shot["exec"]]
    if shot.get("keys"):
        arguments.append("--keys=" + shot["keys"])
    run(arguments, data)
    png = os.path.join(work, shot["name"] + ".png")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", bmp, png], check=True)
    quantise(png, os.path.join(OUTPUT, shot["name"] + ".png"), LCD_COLOURS, dither=False)


def device_shot(shot, work):
    data = os.path.join(work, shot["name"])
    seed_data(data, None)
    bmp = os.path.join(work, shot["name"] + ".bmp")
    run(["--borderless", "--screenshot=" + bmp, "--frames=150", "--exec=" + SILENCE] + shot["args"], data)
    straight = os.path.join(work, shot["name"] + "_straight.png")
    scaled = os.path.join(work, shot["name"] + "_scaled.png")
    unpremultiplied_png(bmp, straight)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", straight, "-vf", "scale={}:-1:flags=lanczos,format=rgba".format(DEVICE_WIDTH), scaled],
                   check=True)
    quantise(scaled, os.path.join(OUTPUT, shot["name"] + ".png"), DEVICE_COLOURS)


def main():
    parser = argparse.ArgumentParser(description="Render the README screenshots into docs/screenshots.")
    parser.add_argument("names", nargs="*", help="only these shots")
    options = parser.parse_args()
    os.makedirs(OUTPUT, exist_ok=True)
    work = tempfile.mkdtemp()
    try:
        wzd = SAMPLE_WZD
        for shot in LCD_SHOTS:
            if not options.names or shot["name"] in options.names:
                lcd_shot(shot, work, wzd)
                print(shot["name"])
        for shot in DEVICE_SHOTS:
            if not options.names or shot["name"] in options.names:
                device_shot(shot, work)
                print(shot["name"])
    finally:
        shutil.rmtree(work)


if __name__ == "__main__":
    main()
