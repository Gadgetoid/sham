import math

import host
import lcd
from system import dates, keys, prefs, sound, ui, worldtime
from system.gfx import CLEAR, LIGHT, MID, INK, small, large
from system import timefmt
from system.timefmt import DAYS

TITLE = "World"
ICON = "software:planet_2"
ORDER = 25

TWILIGHT = -0.105

DAY_LEVELS = (CLEAR, LIGHT, LIGHT, MID)
NIGHT_LEVELS = (LIGHT, MID, MID, INK)


def load_map():
    with open("/assets/worldmap.bin", "rb") as f:
        data = f.read()
    return data[0], data[1], data[2] - 128.0, data[3] - 128.0, data[4:]


class World(ui.View):
    def __init__(self):
        super().__init__()
        self.map_w, self.map_h, self.lat_top, self.lat_bottom, self.coverage = load_map()
        names = [city[0] for city in worldtime.CITIES]
        self.home = names.index(prefs.get("home_city", "London")) if prefs.get("home_city", "London") in names else names.index("London")
        self.index = self.home
        self.shaded = None
        self.shaded_minute = None
        self.blink = True
        self.blink_at = 0

    @property
    def city(self):
        return worldtime.CITIES[self.index]

    def to_map(self, lat, lon):
        x = int((lon + 180.0) / 360.0 * self.map_w)
        y = int((self.lat_top - lat) / (self.lat_top - self.lat_bottom) * self.map_h)
        return x, y

    def shade(self, utc):
        declination, sun_lon = worldtime.subsolar(utc)
        sin_d = math.sin(math.radians(declination))
        cos_d = math.cos(math.radians(declination))
        cos_lon = [math.cos(math.radians(-180.0 + (x + 0.5) * 360.0 / self.map_w - sun_lon)) for x in range(self.map_w)]
        span = self.lat_top - self.lat_bottom
        pixels = bytearray(self.map_w * self.map_h)
        coverage = self.coverage
        for y in range(self.map_h):
            lat = math.radians(self.lat_top - (y + 0.5) * span / self.map_h)
            sin_part = math.sin(lat) * sin_d
            cos_part = math.cos(lat) * cos_d
            row = y * self.map_w
            for x in range(self.map_w):
                altitude = sin_part + cos_part * cos_lon[x]
                land = coverage[row + x]
                if altitude > 0:
                    level = DAY_LEVELS[land]
                elif altitude > TWILIGHT and (x + y) % 2:
                    level = DAY_LEVELS[land]
                else:
                    level = NIGHT_LEVELS[land]
                pixels[row + x] = level
        self.shaded = pixels

    def tick(self, now):
        minute = host.epoch() // 60
        if minute != self.shaded_minute:
            self.shaded_minute = minute
            self.shade(host.epoch())
            self.refresh()
        if now - self.blink_at >= 500:
            self.blink_at = now
            self.blink = not self.blink
            self.refresh()

    def select(self, index):
        self.index = index % len(worldtime.CITIES)
        self.blink = True
        self.refresh()

    def set_home(self):
        self.home = self.index
        prefs.set("home_city", self.city[0])
        sound.beep(1500, 30)
        self.refresh()

    def key(self, key):
        code = key.code
        char = key.char
        if code in (keys.RIGHT, keys.DOWN):
            self.select(self.index + 1)
        elif code in (keys.LEFT, keys.UP):
            self.select(self.index - 1)
        elif code == keys.ENTER:
            ui.confirm("Make {} home?".format(self.city[0]), self.set_home)
        elif char and char.isalpha():
            for step in range(1, len(worldtime.CITIES) + 1):
                candidate = (self.index + step) % len(worldtime.CITIES)
                if worldtime.CITIES[candidate][0][0].lower() == char.lower():
                    self.select(candidate)
                    break
        else:
            return False
        return True

    def draw(self):
        if self.shaded is None:
            self.shade(host.epoch())
        top = (self.h - self.map_h) // 2
        lcd.blit(self.shaded, self.x, self.y + top, self.map_w, self.map_h)
        for index, city in enumerate(worldtime.CITIES):
            x, y = self.to_map(city[1], city[2])
            if 0 <= y < self.map_h:
                under = self.shaded[y * self.map_w + x]
                colour = CLEAR if under >= MID else INK
                if index == self.home:
                    self.rect(x - 1, top + y - 1, 3, 3, colour)
                else:
                    self.pixel(x, top + y, colour)
        x, y = self.to_map(self.city[1], self.city[2])
        if self.blink:
            self.invert(x - 4, top + y, 3, 1)
            self.invert(x + 2, top + y, 3, 1)
            self.invert(x, top + y - 4, 1, 3)
            self.invert(x, top + y + 2, 1, 3)

        utc = host.epoch()
        panel = self.map_w + 4
        panel_w = self.w - panel
        self.fill(panel - 2, 0, 1, self.h, MID)
        spacing = self.h // 9
        name = small.fit(self.city[0], panel_w - 2)
        self.text(name, panel, spacing - small.height)
        days, hour, minute = worldtime.local(self.city, utc)
        clock = timefmt.clock_label(hour, minute, suffix=False)
        self.text(clock, panel + (panel_w - large.measure(clock)) // 2, spacing * 2, INK, large)
        date = "{} {}  {}".format(DAYS[dates.weekday(days)], dates.from_days(days)[2], timefmt.meridiem(hour))
        self.text(date, panel, spacing * 2 + large.height + spacing // 2 + 2, MID)
        offset = worldtime.city_offset(self.city, utc)
        home_offset = worldtime.city_offset(worldtime.CITIES[self.home], utc)
        if self.index == self.home:
            relative = "Home"
        else:
            relative = worldtime.format_offset(offset - home_offset) + "h"
        dst = " DST" if worldtime.dst_active(self.city[4], self.city[3], utc) else ""
        self.text(small.fit(relative + dst, panel_w - 2), panel, spacing * 6)
        self.text("UTC" + worldtime.format_offset(offset), panel, spacing * 7 + 2, MID)
        coordinates = "{:.0f}{} {:.0f}{}".format(abs(self.city[1]), "N" if self.city[1] >= 0 else "S",
                                                  abs(self.city[2]), "E" if self.city[2] >= 0 else "W")
        self.text(small.fit(coordinates, panel_w - 2), panel, spacing * 8 + 2, MID)


def launch():
    view = World()
    return ui.Screen("World", view, status=lambda: "UTC " + timefmt.clock_label(host.epoch() % 86400 // 3600,
                                                                               host.epoch() % 3600 // 60),
                     menu=[("Set as home", view.set_home)])
