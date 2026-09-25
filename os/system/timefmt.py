from system import prefs

MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
DAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
DATE_FORMATS = ("M/D/Y", "D.M.Y")


def use_24h():
    return prefs.get("time_24h", False)


def date_format():
    return prefs.get("date_format", "M/D/Y")


def week_start():
    return 0 if prefs.get("week_start", "SUNDAY") == "MONDAY" else 6


def clock_label(hour, minute, suffix=True):
    if use_24h():
        return "{}:{:02d}".format(hour, minute)
    label = "{}:{:02d}".format(hour % 12 or 12, minute)
    return label + ("AM" if hour < 12 else "PM") if suffix else label


def meridiem(hour):
    return "" if use_24h() else ("AM" if hour < 12 else "PM")


def date_label(t):
    if date_format() == "D.M.Y":
        return "{} {} {}({})".format(t[2], MONTHS[t[1] - 1], t[0], DAYS[t[6]])
    return "{} {},{}({})".format(MONTHS[t[1] - 1], t[2], t[0], DAYS[t[6]])


def time_label(t):
    return clock_label(t[3], t[4])


def numeric_date(year, month, day):
    if date_format() == "D.M.Y":
        return "{:02d}.{:02d}.{:04d}".format(day, month, year)
    return "{:02d}/{:02d}/{:04d}".format(month, day, year)


def parse_numeric_date(text):
    separator = "." if date_format() == "D.M.Y" else "/"
    parts = text.strip().split(separator)
    if len(parts) != 3 or not all(part.strip().isdigit() for part in parts):
        return None
    first, second, year = (int(part) for part in parts)
    day, month = (first, second) if separator == "." else (second, first)
    return year, month, day


def parse_clock(text):
    text = text.strip().upper().replace(" ", "")
    suffix = None
    if text.endswith("AM") or text.endswith("PM"):
        suffix = text[-2:]
        text = text[:-2]
    parts = text.split(":")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        return None
    hour, minute = int(parts[0]), int(parts[1])
    if suffix:
        if not 1 <= hour <= 12:
            return None
        hour = hour % 12 + (12 if suffix == "PM" else 0)
    if not (0 <= hour < 24 and 0 <= minute < 60):
        return None
    return hour, minute


def iso_date(t):
    return "{:04d}-{:02d}-{:02d}".format(t[0], t[1], t[2])
