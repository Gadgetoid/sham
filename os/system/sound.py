import host
from system import prefs

NOTE_OFFSETS = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}

DTMF_ROWS = (697, 770, 852, 941)
DTMF_COLUMNS = (1209, 1336, 1477, 1633)
DTMF_KEYS = ("123A", "456B", "789C", "*0#D")


def enabled():
    return prefs.get("sound", True)


def frequency(note):
    name = note[0].upper()
    if name == "R":
        return 0
    semitone = NOTE_OFFSETS[name]
    rest = note[1:]
    if rest.startswith("#"):
        semitone += 1
        rest = rest[1:]
    elif rest.startswith("b"):
        semitone -= 1
        rest = rest[1:]
    octave = int(rest) if rest else 4
    return 440 * 2 ** ((semitone + (octave - 4) * 12) / 12)


def tone(hz, ms, second_hz=0):
    if enabled():
        host.beep(hz, ms, second_hz)


def beep(hz=2000, ms=80):
    tone(hz, ms)


def click():
    if prefs.get("click", False):
        tone(3200, 3)


def play(tune, beat_ms=120):
    for token in tune.split():
        note, _, beats = token.partition(":")
        tone(frequency(note), int(float(beats or 1) * beat_ms))
        tone(0, 12)


def alarm():
    for _ in range(4):
        tone(2400, 70)
        tone(0, 50)
    tone(0, 400)


def dtmf(digits, ms=90, gap_ms=60):
    for digit in digits.upper():
        for row, keys in enumerate(DTMF_KEYS):
            column = keys.find(digit)
            if column >= 0:
                tone(DTMF_ROWS[row], ms, DTMF_COLUMNS[column])
                tone(0, gap_ms)


def busy():
    return host.beeping()


def stop():
    host.beep_stop()
