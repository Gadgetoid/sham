MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
DAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")


def date_label(t):
    return "{} {},{}({})".format(MONTHS[t[1] - 1], t[2], t[0], DAYS[t[6]])


def time_label(t):
    hour = t[3] % 12 or 12
    return "{}:{:02d}{}".format(hour, t[4], "AM" if t[3] < 12 else "PM")


def iso_date(t):
    return "{:04d}-{:02d}-{:02d}".format(t[0], t[1], t[2])
