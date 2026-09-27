import random

import lcd
from system import keys, sound, store, ui
from system.gfx import CLEAR, LIGHT, MID, INK, small, large

TITLE = "Dungeon"
ICON = "map_markers:stairs_down"
CATEGORY = "Games"
ORDER = 79

TILE = 8
MAP_W = 60
MAP_H = 30
PACK_SIZE = 10
SIGHT = 5
CAVE_SIGHT = 4
LOG_LENGTH = 40
REGEN_TURNS = 7
AUTOSAVE_TURNS = 25
SAVE_NAME = "dungeon"

ROCK = 0
WALL = 1
FLOOR = 2
CORRIDOR = 3
DOOR = 4
STAIRS = 5
CAVE_FLOOR = 6
CAVE_WALL = 7

PASSABLE = (FLOOR, CORRIDOR, DOOR, STAIRS, CAVE_FLOOR)
SIGHT_BLOCKERS = (ROCK, WALL, CAVE_WALL)

TILE_LOOKS = {
    WALL: ((11, INK), (11, MID)),
    FLOOR: ((2, MID), (1, LIGHT)),
    CORRIDOR: ((4, MID), (4, LIGHT)),
    CAVE_WALL: ((8, INK), (8, MID)),
    CAVE_FLOOR: ((6, MID), (1, LIGHT)),
}

STEPS = ((0, -1), (0, 1), (-1, 0), (1, 0))
MOVES = {keys.UP: (0, -1), keys.DOWN: (0, 1), keys.LEFT: (-1, 0), keys.RIGHT: (1, 0)}
LETTER_MOVES = {
    "k": (0, -1), "j": (0, 1), "h": (-1, 0), "l": (1, 0),
    "8": (0, -1), "2": (0, 1), "4": (-1, 0), "6": (1, 0),
}


def make_sprite(rows, ink, shade):
    pixels = bytearray(TILE * TILE)
    for row_index, row in enumerate(rows):
        for column_index, char in enumerate(row):
            if char == "#":
                pixels[row_index * TILE + column_index] = ink
            elif char == "+":
                pixels[row_index * TILE + column_index] = shade
    return bytes(pixels)


class Sprite:
    def __init__(self, rows):
        self.lit = make_sprite(rows, INK, MID)
        self.dim = make_sprite(rows, MID, LIGHT)


PLAYER_SPRITE = Sprite((
    "...##...",
    "..####.#",
    "...##.#.",
    ".######.",
    "#.####..",
    "..####..",
    "..#..#..",
    ".##..##.",
))
RAT_SPRITE = Sprite((
    "........",
    "........",
    ".....##.",
    "...####.",
    ".###.###",
    "#######.",
    "#.#..#..",
    "........",
))
BAT_SPRITE = Sprite((
    "........",
    "#..##..#",
    "##.##.##",
    "########",
    "#.#..#.#",
    "...##...",
    "........",
    "........",
))
GOBLIN_SPRITE = Sprite((
    "#.####.#",
    ".#.##.#.",
    "..####..",
    "...##...",
    ".######.",
    "#.####.#",
    "..#..#..",
    ".##..##.",
))
SLIME_SPRITE = Sprite((
    "........",
    "........",
    "...##...",
    "..####..",
    ".#.##.#.",
    ".######.",
    "########",
    "........",
))
ARCHER_SPRITE = Sprite((
    "..###.#.",
    "..#.#..#",
    "..###..#",
    "...#...#",
    ".#####.#",
    "...#..#.",
    "..#.#...",
    ".#...#..",
))
GHOST_SPRITE = Sprite((
    "..####..",
    ".######.",
    ".#.##.#.",
    ".######.",
    ".######.",
    ".######.",
    ".######.",
    ".#.##.#.",
))
TROLL_SPRITE = Sprite((
    ".######.",
    "##.##.##",
    "########",
    ".#....#.",
    "########",
    "########",
    ".##..##.",
    "###..###",
))
GOLD_SPRITE = Sprite((
    "........",
    "........",
    "..####..",
    ".#++++#.",
    ".######.",
    "#.####.#",
    "#++++++#",
    ".######.",
))
POTION_SPRITE = Sprite((
    "...##...",
    "..####..",
    "...##...",
    "..#..#..",
    ".#....#.",
    ".######.",
    ".######.",
    "..####..",
))
SCROLL_SPRITE = Sprite((
    "........",
    ".#####..",
    "#.....#.",
    ".#.##.#.",
    ".#....#.",
    ".#.##.#.",
    ".#....#.",
    "..#####.",
))
WEAPON_SPRITE = Sprite((
    "......##",
    ".....###",
    "....###.",
    "#..###..",
    ".####...",
    "..##....",
    ".#.##...",
    "#...#...",
))
ARMOUR_SPRITE = Sprite((
    "........",
    ".##..##.",
    "########",
    "#.####.#",
    "..####..",
    "..####..",
    "..####..",
    "........",
))
STAIRS_SPRITE = Sprite((
    "......##",
    "......#+",
    "....###+",
    "....#+++",
    "..###+++",
    "..#+++++",
    "###+++++",
    "++++++++",
))
DOOR_SPRITE = Sprite((
    ".######.",
    "#......#",
    "#.####.#",
    "#.#..#.#",
    "#.#..#.#",
    "#.#.##.#",
    "#.#..#.#",
    "########",
))

MONSTERS = {
    "rat": {"name": "rat", "hp": 3, "attack": 2, "accuracy": 55, "xp": 1, "depths": (1, 5), "weight": 10,
            "behaviour": "erratic", "sprite": RAT_SPRITE},
    "bat": {"name": "bat", "hp": 4, "attack": 2, "accuracy": 50, "xp": 2, "depths": (2, 9), "weight": 8,
            "behaviour": "flutter", "sprite": BAT_SPRITE},
    "goblin": {"name": "goblin", "hp": 7, "attack": 3, "accuracy": 65, "xp": 3, "depths": (2, 12), "weight": 10,
               "behaviour": "coward", "sprite": GOBLIN_SPRITE},
    "slime": {"name": "slime", "hp": 12, "attack": 3, "accuracy": 60, "xp": 4, "depths": (3, 14), "weight": 6,
              "behaviour": "slow", "sprite": SLIME_SPRITE},
    "mimic": {"name": "mimic", "hp": 10, "attack": 5, "accuracy": 70, "xp": 6, "depths": (4, 99), "weight": 3,
              "behaviour": "lurk", "sprite": GOBLIN_SPRITE},
    "archer": {"name": "skeleton archer", "hp": 6, "attack": 3, "accuracy": 55, "xp": 4, "depths": (4, 99), "weight": 6,
               "behaviour": "archer", "sprite": ARCHER_SPRITE},
    "ghost": {"name": "ghost", "hp": 8, "attack": 4, "accuracy": 60, "xp": 6, "depths": (5, 99), "weight": 5,
              "behaviour": "phase", "sprite": GHOST_SPRITE},
    "troll": {"name": "troll", "hp": 20, "attack": 6, "accuracy": 70, "xp": 10, "depths": (7, 99), "weight": 5,
              "behaviour": "regenerate", "sprite": TROLL_SPRITE},
}
MIMIC_SPRITE = Sprite((
    "........",
    "#.#..#.#",
    "..####..",
    ".#.##.#.",
    ".######.",
    "#.#..#.#",
    "#++++++#",
    ".######.",
))
MONSTERS["mimic"]["sprite"] = MIMIC_SPRITE

CONSUMABLES = {
    "healing": {"name": "potion of healing", "kind": "potion", "weight": 10},
    "might": {"name": "potion of might", "kind": "potion", "weight": 3},
    "vigour": {"name": "potion of vigour", "kind": "potion", "weight": 3},
    "mapping": {"name": "scroll of mapping", "kind": "scroll", "weight": 4},
    "teleport": {"name": "scroll of teleport", "kind": "scroll", "weight": 4},
    "fire": {"name": "scroll of fire", "kind": "scroll", "weight": 3},
}
WEAPONS = (("dagger", 1), ("short sword", 2), ("mace", 3), ("long sword", 4), ("war axe", 5))
ARMOURS = (("leather armour", 1), ("ring mail", 2), ("chain mail", 3), ("scale mail", 4), ("plate armour", 5))
ITEM_ICONS = {
    "healing": "alchemy:potion_round_full",
    "might": "alchemy:potion_bottle_triangle_full",
    "vigour": "alchemy:potion_life_full",
    "mapping": "map_markers:scroll_location",
    "teleport": "map_markers:scroll_blank",
    "fire": "tools_crafting:newspaper_scroll",
    "weapon": "rpg:item_melee",
    "armour": "rpg:item_armor",
}
ITEM_SPRITES = {"potion": POTION_SPRITE, "scroll": SCROLL_SPRITE, "weapon": WEAPON_SPRITE, "armour": ARMOUR_SPRITE,
                "gold": GOLD_SPRITE}


def weighted_choice(options):
    total = sum(weight for _, weight in options)
    roll = random.randrange(total)
    for value, weight in options:
        roll -= weight
        if roll < 0:
            return value
    return options[-1][0]


def item_kind(item):
    kind = item["type"]
    if kind in CONSUMABLES:
        return CONSUMABLES[kind]["kind"]
    return kind


def item_name(item):
    kind = item["type"]
    if kind == "gold":
        return "{} gold".format(item["amount"])
    if kind == "weapon":
        name, bonus = WEAPONS[item["tier"]]
        return "{} +{}".format(name, bonus)
    if kind == "armour":
        name, bonus = ARMOURS[item["tier"]]
        return "{} [{}]".format(name, bonus)
    return CONSUMABLES[kind]["name"]


def article(name):
    return ("an " if name[:1] in "aeiou" else "a ") + name


def sign(value):
    return (value > 0) - (value < 0)


def line_cells(x0, y0, x1, y1):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    step_x = 1 if x0 < x1 else -1
    step_y = 1 if y0 < y1 else -1
    error = dx + dy
    while True:
        yield x0, y0
        if x0 == x1 and y0 == y1:
            return
        doubled = 2 * error
        if doubled >= dy:
            error += dy
            x0 += step_x
        if doubled <= dx:
            error += dx
            y0 += step_y


class Game:
    def __init__(self, saved=None):
        self.log = []
        if saved:
            self.restore(saved)
        else:
            self.new_game()

    def new_game(self):
        self.depth = 1
        self.hp = 20
        self.max_hp = 20
        self.level = 1
        self.xp = 0
        self.might = 0
        self.gold = 0
        self.turns = 0
        self.kills = 0
        self.pack = []
        self.weapon = None
        self.armour = None
        self.dead = False
        self.killer = ""
        self.log = []
        self.fresh = []
        self.build_level()
        self.say("Find the stairs down. MENU opens your pack.")

    @property
    def attack(self):
        bonus = WEAPONS[self.weapon["tier"]][1] if self.weapon else 0
        return 2 + self.level + self.might + bonus

    @property
    def defence(self):
        return ARMOURS[self.armour["tier"]][1] if self.armour else 0

    @property
    def xp_needed(self):
        return self.level * 6

    def say(self, text):
        self.fresh.append(text)
        self.log.append(text)
        if len(self.log) > LOG_LENGTH:
            self.log.pop(0)

    def message(self):
        return "  ".join(self.fresh)

    def index(self, column, row):
        return row * MAP_W + column

    def in_bounds(self, column, row):
        return 0 <= column < MAP_W and 0 <= row < MAP_H

    def tile_at(self, column, row):
        if not self.in_bounds(column, row):
            return ROCK
        return self.tiles[row * MAP_W + column]

    def passable(self, column, row):
        return self.tile_at(column, row) in PASSABLE

    def blocks_sight(self, column, row):
        return self.tile_at(column, row) in SIGHT_BLOCKERS

    def build_level(self):
        self.tiles = bytearray(MAP_W * MAP_H)
        self.room_of = bytearray(MAP_W * MAP_H)
        self.explored = bytearray(MAP_W * MAP_H)
        self.visible = bytearray(MAP_W * MAP_H)
        self.rooms = []
        self.monsters = []
        self.items = []
        self.cave = self.depth % 4 == 0
        if self.cave:
            self.carve_cave()
        else:
            while len(self.rooms) < 5:
                self.tiles = bytearray(MAP_W * MAP_H)
                self.room_of = bytearray(MAP_W * MAP_H)
                self.rooms = []
                self.carve_rooms()
        self.add_walls()
        self.place_stairs()
        self.populate()
        self.look()

    def carve_rooms(self):
        for attempt in range(300):
            if len(self.rooms) >= 11:
                break
            width = random.randrange(4, 11)
            height = random.randrange(3, 7)
            left = random.randrange(2, MAP_W - width - 2)
            top = random.randrange(2, MAP_H - height - 2)
            room = (left, top, width, height)
            if any(self.rooms_overlap(room, other) for other in self.rooms):
                continue
            self.rooms.append(room)
            for row in range(top, top + height):
                for column in range(left, left + width):
                    self.tiles[self.index(column, row)] = FLOOR
                    self.room_of[self.index(column, row)] = len(self.rooms)
        self.rooms.sort(key=lambda room: room[0] + room[2] // 2)
        for number in range(len(self.rooms)):
            for column, row in self.room_cells(self.rooms[number]):
                self.room_of[self.index(column, row)] = number + 1
        for number in range(1, len(self.rooms)):
            self.connect(self.rooms[number - 1], self.rooms[number])
        for extra in range(2):
            first = random.randrange(len(self.rooms))
            second = random.randrange(len(self.rooms))
            if abs(first - second) > 1:
                self.connect(self.rooms[first], self.rooms[second])
        self.add_doors()
        first_room = self.rooms[0]
        self.player_x, self.player_y = self.room_centre(first_room)

    def rooms_overlap(self, room, other):
        margin = 2
        return (room[0] - margin < other[0] + other[2] and other[0] - margin < room[0] + room[2]
                and room[1] - margin < other[1] + other[3] and other[1] - margin < room[1] + room[3])

    def room_cells(self, room):
        left, top, width, height = room
        for row in range(top, top + height):
            for column in range(left, left + width):
                yield column, row

    def room_centre(self, room):
        return room[0] + room[2] // 2, room[1] + room[3] // 2

    def dig(self, column, row):
        at = self.index(column, row)
        if self.tiles[at] == ROCK:
            self.tiles[at] = CORRIDOR

    def connect(self, first, second):
        x0, y0 = self.room_centre(first)
        x1, y1 = self.room_centre(second)
        if random.randrange(2):
            corridor_row, corridor_column = y0, x1
        else:
            corridor_row, corridor_column = y1, x0
        for column in range(min(x0, x1), max(x0, x1) + 1):
            self.dig(column, corridor_row)
        for row in range(min(y0, y1), max(y0, y1) + 1):
            self.dig(corridor_column, row)

    def add_doors(self):
        for left, top, width, height in self.rooms:
            ring = []
            for column in range(left, left + width):
                ring.append((column, top - 1, 1, 0))
                ring.append((column, top + height, 1, 0))
            for row in range(top, top + height):
                ring.append((left - 1, row, 0, 1))
                ring.append((left + width, row, 0, 1))
            for column, row, along_x, along_y in ring:
                if self.tile_at(column, row) != CORRIDOR:
                    continue
                before = self.tile_at(column - along_x, row - along_y)
                after = self.tile_at(column + along_x, row + along_y)
                if before in (ROCK, WALL) and after in (ROCK, WALL) and not self.door_near(column, row) and random.randrange(3):
                    self.tiles[self.index(column, row)] = DOOR

    def door_near(self, column, row):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if self.tile_at(column + dx, row + dy) == DOOR:
                    return True
        return False

    def carve_cave(self):
        column, row = MAP_W // 2, MAP_H // 2
        target = MAP_W * MAP_H * 36 // 100
        carved = 0
        while carved < target:
            at = self.index(column, row)
            if self.tiles[at] == ROCK:
                self.tiles[at] = CAVE_FLOOR
                carved += 1
            dx, dy = STEPS[random.randrange(4)]
            column = min(MAP_W - 3, max(2, column + dx))
            row = min(MAP_H - 3, max(2, row + dy))
        self.player_x, self.player_y = MAP_W // 2, MAP_H // 2

    def add_walls(self):
        wall = CAVE_WALL if self.cave else WALL
        for row in range(MAP_H):
            for column in range(MAP_W):
                if self.tiles[self.index(column, row)] != ROCK:
                    continue
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if self.tile_at(column + dx, row + dy) in PASSABLE:
                            self.tiles[self.index(column, row)] = wall
                            break
                    else:
                        continue
                    break

    def distances_from(self, column, row):
        distances = bytearray(b"\xff" * (MAP_W * MAP_H))
        start = self.index(column, row)
        distances[start] = 0
        queue = [start]
        head = 0
        while head < len(queue):
            at = queue[head]
            head += 1
            here = distances[at]
            if here >= 254:
                continue
            for offset in (-MAP_W, MAP_W, -1, 1):
                neighbour = at + offset
                if distances[neighbour] != 255 or self.tiles[neighbour] not in PASSABLE:
                    continue
                distances[neighbour] = here + 1
                queue.append(neighbour)
        return distances

    def place_stairs(self):
        distances = self.distances_from(self.player_x, self.player_y)
        best = None
        best_distance = -1
        for at in range(MAP_W * MAP_H):
            tile = self.tiles[at]
            if tile not in (FLOOR, CAVE_FLOOR) or distances[at] == 255:
                continue
            score = distances[at] + random.randrange(8)
            if score > best_distance:
                best_distance = score
                best = at
        self.tiles[best] = STAIRS
        self.stairs = (best % MAP_W, best // MAP_W)

    def free_floor(self, away_from_player=6):
        for attempt in range(400):
            column = random.randrange(1, MAP_W - 1)
            row = random.randrange(1, MAP_H - 1)
            if self.tiles[self.index(column, row)] not in (FLOOR, CAVE_FLOOR):
                continue
            if abs(column - self.player_x) + abs(row - self.player_y) < away_from_player:
                continue
            if self.monster_at(column, row) or self.item_at(column, row):
                continue
            return column, row
        return None

    def monster_choices(self):
        return [(kind, stats["weight"]) for kind, stats in MONSTERS.items()
                if stats["depths"][0] <= self.depth <= stats["depths"][1]]

    def spawn_monster(self, kind, column, row):
        stats = MONSTERS[kind]
        hp = stats["hp"] + self.depth // 3
        self.monsters.append({"kind": kind, "col": column, "row": row, "hp": hp, "max_hp": hp,
                              "awake": False, "disguised": kind == "mimic", "rested": False})

    def random_item(self):
        roll = random.randrange(10)
        if roll < 2:
            return {"type": "weapon", "tier": min(len(WEAPONS) - 1, (self.depth + random.randrange(3)) // 3)}
        if roll < 4:
            return {"type": "armour", "tier": min(len(ARMOURS) - 1, (self.depth + random.randrange(3)) // 3)}
        return {"type": weighted_choice([(kind, info["weight"]) for kind, info in CONSUMABLES.items()])}

    def drop_on_floor(self, item, column, row):
        item["col"] = column
        item["row"] = row
        self.items.append(item)

    def populate(self):
        choices = self.monster_choices()
        for count in range(min(12, 3 + self.depth)):
            spot = self.free_floor(8)
            if spot:
                self.spawn_monster(weighted_choice(choices), *spot)
        for count in range(3 + self.depth // 3):
            spot = self.free_floor(2)
            if spot:
                self.drop_on_floor(self.random_item(), *spot)
        for count in range(3 + random.randrange(3)):
            spot = self.free_floor(2)
            if spot:
                amount = random.randrange(2, 8) * self.depth + random.randrange(5)
                self.drop_on_floor({"type": "gold", "amount": amount}, *spot)

    def monster_at(self, column, row):
        for monster in self.monsters:
            if monster["col"] == column and monster["row"] == row:
                return monster
        return None

    def item_at(self, column, row):
        for item in self.items:
            if item["col"] == column and item["row"] == row:
                return item
        return None

    def look(self):
        visible = self.visible = bytearray(MAP_W * MAP_H)
        explored = self.explored
        room = self.room_of[self.index(self.player_x, self.player_y)]
        if room:
            left, top, width, height = self.rooms[room - 1]
            for row in range(top - 1, top + height + 1):
                for column in range(left - 1, left + width + 1):
                    at = self.index(column, row)
                    visible[at] = 1
                    explored[at] = 1
        radius = CAVE_SIGHT if self.cave else SIGHT
        limit = radius * radius + radius
        targets = []
        for offset in range(-radius, radius + 1):
            targets.append((self.player_x + offset, self.player_y - radius))
            targets.append((self.player_x + offset, self.player_y + radius))
            targets.append((self.player_x - radius, self.player_y + offset))
            targets.append((self.player_x + radius, self.player_y + offset))
        for target_x, target_y in targets:
            for column, row in line_cells(self.player_x, self.player_y, target_x, target_y):
                if not self.in_bounds(column, row):
                    break
                dx = column - self.player_x
                dy = row - self.player_y
                if dx * dx + dy * dy > limit:
                    break
                at = self.index(column, row)
                visible[at] = 1
                explored[at] = 1
                if self.blocks_sight(column, row) and (column, row) != (self.player_x, self.player_y):
                    break

    def is_visible(self, column, row):
        return self.in_bounds(column, row) and self.visible[self.index(column, row)]

    def clear_line(self, x0, y0, x1, y1):
        for column, row in line_cells(x0, y0, x1, y1):
            if (column, row) != (x0, y0) and (column, row) != (x1, y1) and self.blocks_sight(column, row):
                return False
        return True

    def monster_name(self, monster):
        return MONSTERS[monster["kind"]]["name"]

    def take_turn(self, dx, dy):
        if self.dead:
            return False
        self.fresh = []
        target_x = self.player_x + dx
        target_y = self.player_y + dy
        monster = self.monster_at(target_x, target_y)
        if monster:
            self.strike(monster)
        elif self.passable(target_x, target_y):
            self.player_x = target_x
            self.player_y = target_y
            self.arrive()
        else:
            return False
        self.end_turn()
        return True

    def arrive(self):
        item = self.item_at(self.player_x, self.player_y)
        if item:
            if item["type"] == "gold":
                self.gold += item["amount"]
                self.items.remove(item)
                self.say("You pick up {} gold.".format(item["amount"]))
                sound.beep(1400, 20)
            elif len(self.pack) < PACK_SIZE:
                self.items.remove(item)
                del item["col"]
                del item["row"]
                self.pack.append(item)
                self.say("You pick up {}.".format(article(item_name(item))))
                self.auto_equip(item)
            else:
                self.say("Your pack is full. {} lies here.".format(item_name(item)))
        if (self.player_x, self.player_y) == self.stairs:
            self.say("Stairs down. Enter to descend.")

    def auto_equip(self, item):
        if item["type"] == "weapon" and self.weapon is None:
            self.weapon = item
            self.say("You wield it.")
        elif item["type"] == "armour" and self.armour is None:
            self.armour = item
            self.say("You put it on.")

    def rest(self):
        if self.dead:
            return
        self.fresh = []
        self.end_turn()

    def on_stairs(self):
        return (self.player_x, self.player_y) == self.stairs

    def descend(self):
        if self.dead or not self.on_stairs():
            return False
        self.depth += 1
        self.fresh = []
        self.build_level()
        self.say("You descend to depth {}.".format(self.depth))
        if self.cave:
            self.say("A dark cavern.")
        sound.play("C5 G4 C4", 60)
        return True

    def strike(self, monster):
        stats = MONSTERS[monster["kind"]]
        name = stats["name"]
        if monster["disguised"]:
            monster["disguised"] = False
            self.say("The gold was a mimic!")
        monster["awake"] = True
        if random.randrange(100) >= 80:
            self.say("You miss the {}.".format(name))
            return
        damage = random.randrange(self.attack // 2 + 1, self.attack + 1)
        monster["hp"] -= damage
        if monster["hp"] <= 0:
            self.monsters.remove(monster)
            self.kills += 1
            self.say("You kill the {}.".format(name))
            sound.beep(500, 30)
            self.gain_xp(stats["xp"])
            if monster["kind"] == "mimic":
                self.drop_on_floor({"type": "gold", "amount": random.randrange(10, 20) * self.depth},
                                   monster["col"], monster["row"])
        else:
            self.say("You hit the {}.".format(name))
            sound.beep(900, 15)

    def gain_xp(self, amount):
        self.xp += amount
        while self.xp >= self.xp_needed:
            self.xp -= self.xp_needed
            self.level += 1
            self.max_hp += 5
            self.hp = min(self.max_hp, self.hp + 5)
            self.say("You reach level {}.".format(self.level))
            sound.play("C5 E5 G5", 60)

    def hurt(self, amount, source):
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            self.killer = source
            self.say("You die.")
            sound.play("G4 E4 C4:2", 120)

    def monster_attack(self, monster, verb="hits"):
        stats = MONSTERS[monster["kind"]]
        name = stats["name"]
        if random.randrange(100) >= stats["accuracy"]:
            self.say("The {} misses.".format(name))
            return
        damage = random.randrange(1, stats["attack"] + 1) - random.randrange(0, self.defence + 1)
        if damage <= 0:
            self.say("Your armour turns the {}.".format(name))
            return
        self.say("The {} {} you.".format(name, verb))
        self.hurt(damage, article(name))

    def end_turn(self):
        self.turns += 1
        if self.turns % REGEN_TURNS == 0 and self.hp < self.max_hp:
            self.hp += 1
        self.look()
        self.monsters_act()
        self.look()

    def monsters_act(self):
        if not self.monsters:
            return
        distances = None
        for monster in list(self.monsters):
            if self.dead:
                return
            if monster not in self.monsters:
                continue
            if not monster["awake"]:
                self.maybe_wake(monster)
                if not monster["awake"]:
                    continue
            if distances is None:
                distances = self.distances_from(self.player_x, self.player_y)
            self.act(monster, distances)

    def maybe_wake(self, monster):
        near = abs(monster["col"] - self.player_x) + abs(monster["row"] - self.player_y)
        if monster["disguised"]:
            if near == 1:
                monster["disguised"] = False
                monster["awake"] = True
                self.say("The gold was a mimic!")
            return
        if self.is_visible(monster["col"], monster["row"]) and random.randrange(100) < 70:
            monster["awake"] = True
        elif near <= 2:
            monster["awake"] = True

    def adjacent(self, monster):
        return abs(monster["col"] - self.player_x) + abs(monster["row"] - self.player_y) == 1

    def act(self, monster, distances):
        behaviour = MONSTERS[monster["kind"]]["behaviour"]
        if behaviour == "regenerate" and monster["hp"] < monster["max_hp"]:
            monster["hp"] += 1
        if behaviour in ("slow", "lurk"):
            monster["rested"] = not monster["rested"]
            if monster["rested"] and not self.adjacent(monster):
                return
        if behaviour == "flutter":
            for flap in range(2):
                if self.dead:
                    return
                if random.randrange(2):
                    self.wander(monster)
                else:
                    self.advance(monster, distances)
            return
        if behaviour == "erratic" and random.randrange(3) == 0:
            self.wander(monster)
            return
        if behaviour == "coward" and monster["hp"] * 3 <= monster["max_hp"]:
            if self.flee(monster, distances):
                return
        if behaviour == "archer" and not self.adjacent(monster) and self.can_shoot(monster):
            self.monster_attack(monster, "shoots")
            return
        if behaviour == "phase":
            self.drift(monster)
            return
        self.advance(monster, distances)

    def can_shoot(self, monster):
        dx = monster["col"] - self.player_x
        dy = monster["row"] - self.player_y
        return (self.is_visible(monster["col"], monster["row"]) and dx * dx + dy * dy <= 25
                and self.clear_line(monster["col"], monster["row"], self.player_x, self.player_y))

    def step_monster(self, monster, column, row):
        if (column, row) == (self.player_x, self.player_y):
            self.monster_attack(monster)
            return True
        if self.monster_at(column, row):
            return False
        monster["col"] = column
        monster["row"] = row
        return True

    def wander(self, monster):
        dx, dy = STEPS[random.randrange(4)]
        column = monster["col"] + dx
        row = monster["row"] + dy
        if self.passable(column, row):
            self.step_monster(monster, column, row)

    def advance(self, monster, distances):
        if self.adjacent(monster):
            self.monster_attack(monster)
            return
        here = distances[self.index(monster["col"], monster["row"])]
        options = []
        for dx, dy in STEPS:
            column = monster["col"] + dx
            row = monster["row"] + dy
            if not self.in_bounds(column, row):
                continue
            distance = distances[self.index(column, row)]
            if distance < here and not self.monster_at(column, row):
                options.append((column, row))
        if options:
            self.step_monster(monster, *options[random.randrange(len(options))])

    def flee(self, monster, distances):
        here = distances[self.index(monster["col"], monster["row"])]
        for dx, dy in STEPS:
            column = monster["col"] + dx
            row = monster["row"] + dy
            if not self.in_bounds(column, row):
                continue
            distance = distances[self.index(column, row)]
            if here < distance < 255 and not self.monster_at(column, row):
                self.step_monster(monster, column, row)
                return True
        return False

    def drift(self, monster):
        dx = self.player_x - monster["col"]
        dy = self.player_y - monster["row"]
        if abs(dx) + abs(dy) == 1:
            self.monster_attack(monster, "chills")
            return
        if abs(dx) >= abs(dy):
            column, row = monster["col"] + sign(dx), monster["row"]
        else:
            column, row = monster["col"], monster["row"] + sign(dy)
        if 1 <= column < MAP_W - 1 and 1 <= row < MAP_H - 1:
            self.step_monster(monster, column, row)

    def item_actions(self, item):
        kind = item_kind(item)
        actions = []
        if kind == "potion":
            actions.append("Quaff")
        elif kind == "scroll":
            actions.append("Read")
        elif item is self.weapon or item is self.armour:
            actions.append("Take off")
        else:
            actions.append("Equip")
        actions.append("Drop")
        return actions

    def item_detail(self, item):
        if item is self.weapon:
            return "wielded"
        if item is self.armour:
            return "worn"
        return ""

    def use(self, item, action):
        if self.dead or item not in self.pack:
            return
        self.fresh = []
        if action == "Drop":
            self.drop(item)
        elif action == "Equip":
            self.equip(item)
        elif action == "Take off":
            if item is self.weapon:
                self.weapon = None
            if item is self.armour:
                self.armour = None
            self.say("You take off the {}.".format(item_name(item)))
        else:
            self.pack.remove(item)
            self.consume(item)
        self.end_turn()

    def drop(self, item):
        if self.item_at(self.player_x, self.player_y) or self.on_stairs():
            self.say("There's no room to drop it here.")
            return
        if item is self.weapon:
            self.weapon = None
        if item is self.armour:
            self.armour = None
        self.pack.remove(item)
        self.drop_on_floor(item, self.player_x, self.player_y)
        self.say("You drop the {}.".format(item_name(item)))

    def equip(self, item):
        if item["type"] == "weapon":
            self.weapon = item
            self.say("You wield the {}.".format(item_name(item)))
        else:
            self.armour = item
            self.say("You put on the {}.".format(item_name(item)))

    def consume(self, item):
        kind = item["type"]
        if kind == "healing":
            healed = min(self.max_hp - self.hp, 8 + self.depth * 2)
            self.hp += healed
            self.say("You feel better. +{} HP.".format(healed))
        elif kind == "might":
            self.might += 1
            self.say("You feel mighty. Attack +1.")
        elif kind == "vigour":
            self.max_hp += 4
            self.hp = min(self.max_hp, self.hp + 8)
            self.say("You feel hardy. Max HP +4.")
        elif kind == "mapping":
            for at in range(MAP_W * MAP_H):
                if self.tiles[at] != ROCK:
                    self.explored[at] = 1
            self.say("The level's layout comes to you.")
        elif kind == "teleport":
            spot = self.free_floor(10)
            if spot:
                self.player_x, self.player_y = spot
            self.say("The world lurches.")
        elif kind == "fire":
            burned = 0
            for monster in list(self.monsters):
                if self.is_visible(monster["col"], monster["row"]):
                    monster["awake"] = True
                    monster["disguised"] = False
                    monster["hp"] -= 6 + self.depth
                    burned += 1
                    if monster["hp"] <= 0:
                        self.monsters.remove(monster)
                        self.kills += 1
                        self.gain_xp(MONSTERS[monster["kind"]]["xp"])
            self.say("Flames fill the air, scorching {} foe{}.".format(burned, "" if burned == 1 else "s"))
        self.look()

    def quaff_healing(self):
        for item in self.pack:
            if item["type"] == "healing":
                self.use(item, "Quaff")
                return True
        self.fresh = ["You have no potion of healing."]
        return False

    def score(self):
        return self.gold + self.depth * 100 + self.kills * 5

    def snapshot(self):
        pack = [dict(item) for item in self.pack]
        return {
            "depth": self.depth, "hp": self.hp, "max_hp": self.max_hp, "level": self.level, "xp": self.xp,
            "might": self.might, "gold": self.gold, "turns": self.turns, "kills": self.kills, "pack": pack,
            "weapon": self.pack.index(self.weapon) if self.weapon in self.pack else -1,
            "armour": self.pack.index(self.armour) if self.armour in self.pack else -1,
            "player": [self.player_x, self.player_y], "stairs": list(self.stairs), "cave": self.cave,
            "tiles": "".join(chr(48 + tile) for tile in self.tiles),
            "explored": "".join("1" if seen else "0" for seen in self.explored),
            "rooms": [list(room) for room in self.rooms],
            "monsters": self.monsters, "items": self.items, "log": self.log[-10:],
        }

    def restore(self, saved):
        for name in ("depth", "hp", "max_hp", "level", "xp", "might", "gold", "turns", "kills", "cave"):
            setattr(self, name, saved[name])
        self.pack = saved["pack"]
        self.weapon = self.pack[saved["weapon"]] if saved["weapon"] >= 0 else None
        self.armour = self.pack[saved["armour"]] if saved["armour"] >= 0 else None
        self.player_x, self.player_y = saved["player"]
        self.stairs = tuple(saved["stairs"])
        self.tiles = bytearray(ord(char) - 48 for char in saved["tiles"])
        self.explored = bytearray(1 if char == "1" else 0 for char in saved["explored"])
        self.visible = bytearray(MAP_W * MAP_H)
        self.rooms = [tuple(room) for room in saved["rooms"]]
        self.room_of = bytearray(MAP_W * MAP_H)
        for number, room in enumerate(self.rooms):
            for column, row in self.room_cells(room):
                self.room_of[self.index(column, row)] = number + 1
        self.monsters = saved["monsters"]
        self.items = saved["items"]
        self.log = saved.get("log", [])
        self.fresh = ["Welcome back to depth {}.".format(self.depth)]
        self.dead = False
        self.killer = ""
        self.look()


class DungeonView(ui.View):
    def __init__(self):
        super().__init__()
        record = store.load(SAVE_NAME, {})
        self.best_depth = record.get("best_depth", 0)
        self.best_score = record.get("best_score", 0)
        saved = record.get("game")
        self.game = None
        if saved:
            try:
                self.game = Game(saved)
            except (KeyError, IndexError, TypeError, ValueError) as error:
                print("dungeon: could not resume:", error)
        if self.game is None:
            self.game = Game()
        self.recorded = False

    def persist(self):
        game = self.game
        record = {"best_depth": self.best_depth, "best_score": self.best_score,
                  "game": None if game.dead else game.snapshot()}
        store.save(SAVE_NAME, record)

    def record_death(self):
        if self.recorded:
            return
        self.recorded = True
        self.best_depth = max(self.best_depth, self.game.depth)
        self.best_score = max(self.best_score, self.game.score())
        self.persist()

    def new_game(self):
        self.game = Game()
        self.recorded = False
        self.persist()
        self.refresh()

    def after_turn(self, descended=False):
        if self.game.dead:
            self.record_death()
        elif descended or self.game.turns % AUTOSAVE_TURNS == 0:
            self.best_depth = max(self.best_depth, self.game.depth)
            self.persist()
        self.refresh()

    def key(self, key):
        game = self.game
        char = key.char
        if game.dead:
            if key.code == keys.ENTER or char == " ":
                self.new_game()
                return True
            return False
        code = keys.pad(key)
        step = MOVES.get(code) or LETTER_MOVES.get(char)
        if step:
            game.take_turn(*step)
            self.after_turn()
            return True
        if code == keys.ENTER or char in (" ", ">"):
            if game.on_stairs():
                self.after_turn(game.descend())
            else:
                game.rest()
                self.after_turn()
        elif char in (".", "5", "s"):
            game.rest()
            self.after_turn()
        elif char in ("i", "I"):
            self.open_pack()
        elif char in ("m", "M"):
            self.open_map()
        elif char in ("q", "Q"):
            game.quaff_healing()
            self.after_turn()
        else:
            return False
        return True

    def descend(self):
        self.after_turn(self.game.descend())

    def wait(self):
        self.game.rest()
        self.after_turn()

    def open_pack(self):
        game = self.game
        if not game.pack:
            ui.alert("Your pack is empty.", title="Pack")
            return
        listing = ui.List(game.pack, label=item_name, detail=game.item_detail,
                          icon=lambda item: ITEM_ICONS[item["type"]], on_select=self.pick_item)
        ui.push(ui.Screen("Pack", listing, status="{}/{}".format(len(game.pack), PACK_SIZE),
                          footer="ENTER: use or drop", footer_status=lambda: "ATK {}  DEF {}".format(game.attack, game.defence)))

    def pick_item(self, item, index):
        def chosen(action, position):
            ui.pop()
            self.game.use(item, action)
            self.after_turn()

        ui.choose(item_name(item), self.game.item_actions(item), chosen)

    def open_map(self):
        ui.push(ui.Screen("Map, depth {}".format(self.game.depth), MapView(self.game), status="ESC: back"))

    def open_log(self):
        view = ui.TextView("\n".join(reversed(self.game.log)) or "Nothing yet.")
        ui.push(ui.Screen("Messages", view, status="newest first"))

    def menu(self):
        game = self.game
        if game.dead:
            return [("New game", self.new_game)]
        entries = [("Pack ({}/{})".format(len(game.pack), PACK_SIZE), self.open_pack)]
        if game.on_stairs():
            entries.append(("Descend", self.descend))
        entries.append(("Wait a turn", self.wait))
        entries.append(("Map", self.open_map))
        entries.append(("Messages", self.open_log))
        entries.append(("New game", lambda: ui.confirm("Abandon this dungeon?", self.new_game)))
        return entries

    def title(self):
        game = self.game
        if game.dead:
            return "Dungeon"
        return game.message() or "Dungeon, depth {}".format(game.depth)

    def status(self):
        if self.game.fresh or not self.best_depth:
            return ""
        return "Best D{}".format(self.best_depth)

    def footer(self):
        game = self.game
        return "HP {}/{}  ATK {}  DEF {}  LV {}".format(game.hp, game.max_hp, game.attack, game.defence, game.level)

    def footer_status(self):
        return "D{}  ${}".format(self.game.depth, self.game.gold)

    def camera(self, columns, rows):
        game = self.game
        left = min(max(0, game.player_x - columns // 2), MAP_W - columns)
        top = min(max(0, game.player_y - rows // 2), MAP_H - rows)
        return left, top

    def draw(self):
        if self.game.dead:
            self.draw_grave()
            return
        game = self.game
        columns = min(MAP_W, self.w // TILE)
        rows = min(MAP_H, self.h // TILE)
        origin_x = self.x + (self.w - columns * TILE) // 2
        origin_y = self.y + (self.h - rows * TILE) // 2
        camera_x, camera_y = self.camera(columns, rows)
        tiles = game.tiles
        explored = game.explored
        visible = game.visible
        for row in range(rows):
            base = (camera_y + row) * MAP_W + camera_x
            screen_y = origin_y + row * TILE
            for column in range(columns):
                at = base + column
                if not explored[at]:
                    continue
                tile = tiles[at]
                lit = visible[at]
                screen_x = origin_x + column * TILE
                look = TILE_LOOKS.get(tile)
                if look:
                    pattern, colour = look[0] if lit else look[1]
                    lcd.fill(screen_x, screen_y, TILE, TILE, colour, pattern)
                elif tile == STAIRS:
                    lcd.blit(STAIRS_SPRITE.lit if lit else STAIRS_SPRITE.dim, screen_x, screen_y, TILE, TILE)
                elif tile == DOOR:
                    lcd.blit(DOOR_SPRITE.lit if lit else DOOR_SPRITE.dim, screen_x, screen_y, TILE, TILE)

        def on_screen(column, row):
            return camera_x <= column < camera_x + columns and camera_y <= row < camera_y + rows

        def put(sprite, column, row, lit):
            lcd.blit(sprite.lit if lit else sprite.dim, origin_x + (column - camera_x) * TILE,
                     origin_y + (row - camera_y) * TILE, TILE, TILE)

        for item in game.items:
            at = game.index(item["col"], item["row"])
            if explored[at] and on_screen(item["col"], item["row"]):
                put(ITEM_SPRITES[item_kind(item)], item["col"], item["row"], visible[at])
        for monster in game.monsters:
            at = game.index(monster["col"], monster["row"])
            if not on_screen(monster["col"], monster["row"]):
                continue
            if monster["disguised"]:
                if explored[at]:
                    put(GOLD_SPRITE, monster["col"], monster["row"], visible[at])
            elif visible[at]:
                put(MONSTERS[monster["kind"]]["sprite"], monster["col"], monster["row"], True)
        put(PLAYER_SPRITE, game.player_x, game.player_y, True)
        if game.hp * 4 <= game.max_hp:
            lcd.rect(origin_x + (game.player_x - camera_x) * TILE - 1, origin_y + (game.player_y - camera_y) * TILE - 1,
                     TILE + 2, TILE + 2, INK, 3)

    def draw_grave(self):
        game = self.game
        stone_w = 76
        stone_x = 14
        top = 8
        bottom = self.h - 6
        self.fill(stone_x + 6, top, stone_w - 12, 6, MID, 21)
        self.fill(stone_x, top + 6, stone_w, bottom - top - 6, MID, 21)
        self.fill(stone_x + 2, top + 2, 2, 4, MID, 21)
        self.fill(stone_x + stone_w - 4, top + 2, 2, 4, MID, 21)
        self.line(stone_x + 6, top, stone_x + stone_w - 7, top)
        self.line(stone_x + 6, top, stone_x, top + 6)
        self.line(stone_x + stone_w - 7, top, stone_x + stone_w - 1, top + 6)
        self.line(stone_x, top + 6, stone_x, bottom)
        self.line(stone_x + stone_w - 1, top + 6, stone_x + stone_w - 1, bottom)
        self.fill(stone_x - 8, bottom, stone_w + 16, self.h - bottom, INK, 8)
        plaque_x = stone_x + 12
        self.fill(plaque_x, top + 12, stone_w - 24, 22, CLEAR)
        self.rect(plaque_x, top + 12, stone_w - 24, 22, INK)
        self.text("RIP", plaque_x + (stone_w - 24 - large.measure("RIP")) // 2, top + 16, INK, large)
        text_x = stone_x + stone_w + 16
        lines = (
            ("Slain by {}".format(game.killer), INK),
            ("on depth {} after {} turns.".format(game.depth, game.turns), INK),
            ("{} gold, {} kills, level {}.".format(game.gold, game.kills, game.level), INK),
            ("Score {}".format(game.score()), INK),
            ("Best: depth {}, score {}".format(self.best_depth, self.best_score), MID),
            ("Enter: descend again", MID),
        )
        for number, (line, colour) in enumerate(lines):
            self.text(line, text_x, 10 + number * (small.line_height + 3), colour)


class MapView(ui.View):
    CELL_W = 4
    CELL_H = 3

    def __init__(self, game):
        super().__init__()
        self.game = game

    def draw(self):
        game = self.game
        left = self.x + (self.w - MAP_W * self.CELL_W) // 2
        top = self.y + (self.h - MAP_H * self.CELL_H) // 2
        colours = {WALL: INK, CAVE_WALL: INK, FLOOR: LIGHT, CORRIDOR: MID, CAVE_FLOOR: LIGHT, DOOR: MID, STAIRS: INK}
        for row in range(MAP_H):
            for column in range(MAP_W):
                at = game.index(column, row)
                if not game.explored[at]:
                    continue
                colour = colours.get(game.tiles[at])
                if colour is not None:
                    lcd.fill(left + column * self.CELL_W, top + row * self.CELL_H, self.CELL_W, self.CELL_H, colour)
        stairs_x, stairs_y = game.stairs
        if game.explored[game.index(stairs_x, stairs_y)]:
            lcd.rect(left + stairs_x * self.CELL_W - 2, top + stairs_y * self.CELL_H - 2, self.CELL_W + 4, self.CELL_H + 4, INK)
        player_x = left + game.player_x * self.CELL_W
        player_y = top + game.player_y * self.CELL_H
        lcd.fill(player_x - 1, player_y - 1, self.CELL_W + 2, self.CELL_H + 2, CLEAR)
        lcd.fill(player_x, player_y, self.CELL_W, self.CELL_H, INK)


def launch():
    view = DungeonView()
    return ui.Screen(view.title, view, status=view.status, menu=view.menu, on_close=view.persist,
                     footer=view.footer, footer_status=view.footer_status)
