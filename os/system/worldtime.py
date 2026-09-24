import math

from system import dates

CITIES = sorted([
    ("Honolulu", 21.3, -157.9, -10, None),
    ("Anchorage", 61.2, -149.9, -9, "US"),
    ("Los Angeles", 34.1, -118.2, -8, "US"),
    ("Denver", 39.7, -105.0, -7, "US"),
    ("Mexico City", 19.4, -99.1, -6, None),
    ("Chicago", 41.9, -87.6, -6, "US"),
    ("New York", 40.7, -74.0, -5, "US"),
    ("Sao Paulo", -23.6, -46.6, -3, None),
    ("Buenos Aires", -34.6, -58.4, -3, None),
    ("Reykjavik", 64.1, -21.9, 0, None),
    ("London", 51.5, -0.1, 0, "EU"),
    ("Paris", 48.9, 2.4, 1, "EU"),
    ("Berlin", 52.5, 13.4, 1, "EU"),
    ("Athens", 38.0, 23.7, 2, "EU"),
    ("Johannesburg", -26.2, 28.0, 2, None),
    ("Moscow", 55.8, 37.6, 3, None),
    ("Nairobi", -1.3, 36.8, 3, None),
    ("Dubai", 25.2, 55.3, 4, None),
    ("Delhi", 28.6, 77.2, 5.5, None),
    ("Bangkok", 13.8, 100.5, 7, None),
    ("Singapore", 1.4, 103.8, 8, None),
    ("Beijing", 39.9, 116.4, 8, None),
    ("Tokyo", 35.7, 139.7, 9, None),
    ("Sydney", -33.9, 151.2, 10, "AU"),
    ("Auckland", -36.8, 174.8, 12, "NZ"),
], key=lambda city: city[2])


def sunday(year, month, n):
    if n > 0:
        first = dates.to_days(year, month, 1)
        return first + (6 - dates.weekday(first)) % 7 + (n - 1) * 7
    last = (dates.to_days(year, month + 1, 1) if month < 12 else dates.to_days(year + 1, 1, 1)) - 1
    return last - (dates.weekday(last) + 1) % 7


def at(day, local_hour, offset_hours):
    return int(day * 86400 + (local_hour - offset_hours) * 3600)


def dst_active(rule, offset, utc):
    year = dates.from_days(utc // 86400)[0]
    if rule == "EU":
        return at(sunday(year, 3, -1), 1, 0) <= utc < at(sunday(year, 10, -1), 1, 0)
    if rule == "US":
        return at(sunday(year, 3, 2), 2, offset) <= utc < at(sunday(year, 11, 1), 2, offset + 1)
    if rule == "AU":
        return utc < at(sunday(year, 4, 1), 3, offset + 1) or utc >= at(sunday(year, 10, 1), 2, offset)
    if rule == "NZ":
        return utc < at(sunday(year, 4, 1), 3, offset + 1) or utc >= at(sunday(year, 9, -1), 2, offset)
    return False


def city_offset(city, utc):
    name, lat, lon, offset, rule = city
    return offset + (1 if dst_active(rule, offset, utc) else 0)


def local(city, utc):
    shifted = utc + int(city_offset(city, utc) * 3600)
    days = shifted // 86400
    seconds = shifted % 86400
    return days, seconds // 3600, (seconds // 60) % 60


def subsolar(utc):
    days = utc // 86400
    year = dates.from_days(days)[0]
    day_of_year = days - dates.to_days(year, 1, 1)
    declination = -23.44 * math.cos(2 * math.pi / 365 * (day_of_year + 10))
    b = 2 * math.pi * (day_of_year - 81) / 364
    equation_minutes = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)
    hours = (utc % 86400) / 3600
    longitude = (12 - hours - equation_minutes / 60) * 15
    longitude = (longitude + 180) % 360 - 180
    return declination, longitude


def format_offset(hours):
    sign = "+" if hours >= 0 else "-"
    hours = abs(hours)
    whole = int(hours)
    minutes = int(round((hours - whole) * 60))
    return "{}{}{}".format(sign, whole, ":{:02d}".format(minutes) if minutes else "")
