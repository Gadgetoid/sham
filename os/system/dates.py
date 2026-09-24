import host
from system.timefmt import DAYS, MONTHS


def to_days(year, month, day):
    year -= month <= 2
    era = year // 400
    year_of_era = year - era * 400
    day_of_year = (153 * (month + (-3 if month > 2 else 9)) + 2) // 5 + day - 1
    day_of_era = year_of_era * 365 + year_of_era // 4 - year_of_era // 100 + day_of_year
    return era * 146097 + day_of_era - 719468


def from_days(days):
    days += 719468
    era = days // 146097
    day_of_era = days - era * 146097
    year_of_era = (day_of_era - day_of_era // 1460 + day_of_era // 36524 - day_of_era // 146096) // 365
    day_of_year = day_of_era - (365 * year_of_era + year_of_era // 4 - year_of_era // 100)
    shifted_month = (5 * day_of_year + 2) // 153
    day = day_of_year - (153 * shifted_month + 2) // 5 + 1
    month = shifted_month + (3 if shifted_month < 10 else -9)
    return year_of_era + era * 400 + (month <= 2), month, day


def weekday(days):
    return (days + 3) % 7


def today():
    t = host.localtime()
    return to_days(t[0], t[1], t[2])


def now_minutes():
    t = host.localtime()
    return t[3] * 60 + t[4]


def iso(days):
    return "{:04d}-{:02d}-{:02d}".format(*from_days(days))


def parse_iso(text):
    try:
        year, month, day = (int(part) for part in text.split("-"))
    except ValueError:
        return None
    days = to_days(year, month, day)
    return days if from_days(days) == (year, month, day) else None


def parse_time(text):
    try:
        hours, minutes = (int(part) for part in text.split(":"))
    except ValueError:
        return None
    if not (0 <= hours < 24 and 0 <= minutes < 60):
        return None
    return hours * 60 + minutes


def format_time(minutes):
    return "{:02d}:{:02d}".format(minutes // 60, minutes % 60)


def short_label(days):
    year, month, day = from_days(days)
    return "{} {}({})".format(MONTHS[month - 1], day, DAYS[weekday(days)])
