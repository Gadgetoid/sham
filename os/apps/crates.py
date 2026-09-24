from system import keys, sound, store, ui
from system.gfx import CLEAR, LIGHT, MID, INK, small

TITLE = "Crates"
ICON = "tools_crafting:box"
CATEGORY = "Games"
ORDER = 77

TILE = 8

LEVELS = (
    """
########
#      #
# @$ . #
#      #
########
""",
    """
#########
#   #   #
# $   $ #
#  #@#  #
# .   . #
#########
""",
    """
#######
#.  ..#
# $$$ #
#  @  #
# $   #
#.    #
#######
""",
    """
 #########
##   #   ##
#  $ . $  #
# #.#@#.# #
#  $ . $  #
##   #   ##
 #########
""",
    """
  #######
###  .  #
# $ #$# #
# .   $.#
##@#  ###
 #    #
 ######
""",
    """
#######
#  .  #
# $#$ #
#. @ .#
# $#$ #
#  .  #
#######
""",
    """
##########
#        #
# $    $ #
## #..# ##
 # #..# #
## $  $ ##
#   @    #
##########
""",
    """
################
#      #       #
#  $ $ #  ..   #
# @ $ $   ..   #
#      #       #
################
""",
)

WALL = (
    "#######.",
    "#######.",
    "#######.",
    "........",
    "###.####",
    "###.####",
    "###.####",
    "........",
)

CRATE = (
    "#######.",
    "##...##.",
    "#.#.#.#.",
    "#..#..#.",
    "#.#.#.#.",
    "##...##.",
    "#######.",
    "........",
)

PLAYER = (
    "..##....",
    "..##....",
    ".####...",
    "#.##.#..",
    "..##....",
    ".#..#...",
    ".#..#...",
    "........",
)

GOAL = (
    "........",
    "........",
    "...#....",
    "..#.#...",
    "...#....",
    "........",
    "........",
    "........",
)

MOVES = {keys.UP: (0, -1), keys.DOWN: (0, 1), keys.LEFT: (-1, 0), keys.RIGHT: (1, 0)}


def parse(level):
    rows = level.strip("\n").split("\n")
    walls, goals, boxes, player = set(), set(), set(), (0, 0)
    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            if char == "#":
                walls.add((x, y))
            if char in ".*+":
                goals.add((x, y))
            if char in "$*":
                boxes.add((x, y))
            if char in "@+":
                player = (x, y)
    width = max(len(row) for row in rows)
    return walls, goals, boxes, player, width, len(rows)


class Crates(ui.View):
    def __init__(self):
        super().__init__()
        progress = store.load("crates", {})
        self.solved = set(progress.get("solved", []))
        self.load(min(progress.get("level", 0), len(LEVELS) - 1))

    def load(self, index):
        self.index = index
        self.walls, self.goals, self.boxes, self.player, self.width, self.height = parse(LEVELS[index])
        self.history = []
        self.moves = 0
        self.pushes = 0
        self.done = False
        store.save("crates", {"level": index, "solved": sorted(self.solved)})
        self.refresh()

    def step(self, dx, dy):
        x, y = self.player
        target = (x + dx, y + dy)
        if target in self.walls:
            return
        pushed = False
        if target in self.boxes:
            beyond = (target[0] + dx, target[1] + dy)
            if beyond in self.walls or beyond in self.boxes:
                return
            self.history.append((self.player, set(self.boxes), self.moves, self.pushes))
            self.boxes.remove(target)
            self.boxes.add(beyond)
            self.pushes += 1
            pushed = True
        else:
            self.history.append((self.player, set(self.boxes), self.moves, self.pushes))
        self.player = target
        self.moves += 1
        if pushed:
            sound.beep(900 if target not in self.goals else 1300, 15)
        if self.boxes == self.goals:
            self.done = True
            self.solved.add(self.index)
            store.save("crates", {"level": self.index, "solved": sorted(self.solved)})
            sound.play("C5 E5 G5 C6:2", 80)

    def undo(self):
        if self.history:
            self.player, self.boxes, self.moves, self.pushes = self.history.pop()
            self.done = False

    def key(self, key):
        code = key.code
        char = key.char
        if self.done and (code == keys.ENTER or char == " "):
            self.load((self.index + 1) % len(LEVELS))
            return True
        if code in MOVES and not self.done:
            self.step(*MOVES[code])
        elif code == keys.BACKSPACE or char in ("u", "U"):
            self.undo()
        elif char in ("r", "R"):
            self.load(self.index)
        elif code == keys.PGDN or char in ("n", "N"):
            self.load((self.index + 1) % len(LEVELS))
        elif code == keys.PGUP or char in ("p", "P"):
            self.load((self.index - 1) % len(LEVELS))
        else:
            return False
        self.refresh()
        return True

    def draw(self):
        left = (self.w - self.width * TILE) // 2
        top = (self.h - self.height * TILE) // 2
        for x, y in self.walls:
            self.sprite(WALL, left + x * TILE, top + y * TILE, MID)
        for x, y in self.goals:
            self.sprite(GOAL, left + x * TILE, top + y * TILE, INK)
        for x, y in self.boxes:
            px, py = left + x * TILE, top + y * TILE
            if (x, y) in self.goals:
                self.fill(px, py, TILE - 1, TILE - 1, INK)
                self.sprite(GOAL, px, py, CLEAR)
            else:
                self.sprite(CRATE, px, py, INK)
        self.sprite(PLAYER, left + self.player[0] * TILE, top + self.player[1] * TILE, INK)
        if self.done:
            self.banner("Level {} done in {} moves".format(self.index + 1, self.moves), "Enter: next level", bottom=True)


def launch():
    game = Crates()
    return ui.Screen("Crates", game,
                     status=lambda: "L{}/{}{}  {} moves".format(game.index + 1, len(LEVELS),
                                                              "*" if game.index in game.solved else "", game.moves),
                     menu=[("Restart level", lambda: game.load(game.index)),
                           ("Next level", lambda: game.load((game.index + 1) % len(LEVELS))),
                           ("Previous level", lambda: game.load((game.index - 1) % len(LEVELS)))])
