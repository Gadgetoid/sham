import random

import host
from system import keys, ui
from system.gfx import CLEAR, LIGHT, MID, INK, small

TITLE = "Mines"
ICON = "rpg:minesweeper"
ORDER = 71

CELL = 9
MINE_RATIO = 0.15

FLAG = (
    "..#....",
    "..###..",
    "..####.",
    "..#....",
    "..#....",
    ".###...",
)

MINE = (
    "...#...",
    ".#####.",
    ".##.##.",
    "#######",
    ".#####.",
    ".#####.",
    "...#...",
)

MOVES = {
    keys.UP: (0, -1),
    keys.DOWN: (0, 1),
    keys.LEFT: (-1, 0),
    keys.RIGHT: (1, 0),
}


class Mines(ui.View):
    def layout(self):
        self.columns = self.w // CELL
        self.rows = self.h // CELL
        self.left = (self.w - self.columns * CELL) // 2
        self.top = (self.h - self.rows * CELL) // 2
        self.reset()

    def reset(self):
        count = self.columns * self.rows
        self.mine_count = int(count * MINE_RATIO)
        self.mines = None
        self.revealed = bytearray(count)
        self.flagged = bytearray(count)
        self.cursor = (self.columns // 2, self.rows // 2)
        self.state = "playing"
        self.started = None
        self.finished = None
        self.refresh()

    def index(self, x, y):
        return y * self.columns + x

    def neighbours(self, x, y):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if (dx or dy) and 0 <= nx < self.columns and 0 <= ny < self.rows:
                    yield nx, ny

    def lay_mines(self, safe_x, safe_y):
        safe = {(safe_x, safe_y)} | set(self.neighbours(safe_x, safe_y))
        candidates = [(x, y) for y in range(self.rows) for x in range(self.columns) if (x, y) not in safe]
        self.mines = bytearray(self.columns * self.rows)
        for _ in range(self.mine_count):
            x, y = candidates.pop(random.randrange(len(candidates)))
            self.mines[self.index(x, y)] = 1
        self.started = host.ticks_ms()

    def adjacent(self, x, y):
        return sum(self.mines[self.index(nx, ny)] for nx, ny in self.neighbours(x, y))

    def reveal(self, x, y):
        if self.mines is None:
            self.lay_mines(x, y)
        pending = [(x, y)]
        while pending:
            cx, cy = pending.pop()
            at = self.index(cx, cy)
            if self.revealed[at] or self.flagged[at]:
                continue
            self.revealed[at] = 1
            if self.mines[at]:
                self.finish("lost")
                return
            if self.adjacent(cx, cy) == 0:
                pending.extend(self.neighbours(cx, cy))
        if sum(self.revealed) == len(self.revealed) - self.mine_count:
            self.finish("won")

    def chord(self, x, y):
        flags = sum(self.flagged[self.index(nx, ny)] for nx, ny in self.neighbours(x, y))
        if flags == self.adjacent(x, y):
            for nx, ny in self.neighbours(x, y):
                if self.state == "playing":
                    self.reveal(nx, ny)

    def finish(self, outcome):
        self.state = outcome
        self.finished = host.ticks_ms()

    def elapsed(self):
        if self.started is None:
            return 0
        return ((self.finished or host.ticks_ms()) - self.started) // 1000

    def status(self):
        if self.state == "won":
            return "Cleared in {}s".format(self.elapsed())
        if self.state == "lost":
            return "Boom"
        return "{}/{}  {}s".format(sum(self.flagged), self.mine_count, self.elapsed())

    def key(self, key):
        if self.state != "playing":
            if key.code == keys.ENTER or key.char == " ":
                self.reset()
                return True
            return False
        x, y = self.cursor
        at = self.index(x, y)
        if key.code in MOVES:
            dx, dy = MOVES[key.code]
            self.cursor = ((x + dx) % self.columns, (y + dy) % self.rows)
        elif key.code == keys.ENTER or key.char == " ":
            if self.revealed[at]:
                self.chord(x, y)
            else:
                self.reveal(x, y)
        elif key.char in ("f", "F"):
            if not self.revealed[at]:
                self.flagged[at] ^= 1
        else:
            return False
        self.refresh()
        return True

    def tick(self, now):
        if self.state == "playing" and self.started is not None and now // 1000 != getattr(self, "last_second", -1):
            self.last_second = now // 1000
            self.refresh()

    def sprite(self, rows, x, y, colour):
        for dy, row in enumerate(rows):
            for dx, char in enumerate(row):
                if char == "#":
                    self.pixel(x + dx, y + dy, colour)

    def draw_cell(self, cx, cy):
        at = self.index(cx, cy)
        x = self.left + cx * CELL
        y = self.top + cy * CELL
        show_mine = self.mines is not None and self.mines[at] and self.state != "playing"
        if not self.revealed[at]:
            self.fill(x, y, CELL - 1, CELL - 1, LIGHT)
            if self.flagged[at]:
                wrong = self.state == "lost" and not self.mines[at]
                self.sprite(FLAG, x + 1, y + 1, MID if wrong else INK)
            elif show_mine:
                self.sprite(MINE, x + 1, y + 1, MID)
            return
        if self.mines[at]:
            self.fill(x, y, CELL - 1, CELL - 1, INK)
            self.sprite(MINE, x + 1, y + 1, CLEAR)
            return
        count = self.adjacent(cx, cy)
        if count:
            digit = str(count)
            self.text(digit, x + (CELL - 1 - small.measure(digit)) // 2 + 1, y, INK if count > 1 else MID)

    def draw(self):
        for cy in range(self.rows):
            for cx in range(self.columns):
                self.draw_cell(cx, cy)
        if self.state == "playing":
            x, y = self.cursor
            self.rect(self.left + x * CELL - 1, self.top + y * CELL - 1, CELL + 1, CELL + 1, INK)


def launch():
    game = Mines()
    return ui.Screen("Mines", game, status=game.status, menu=[("New game", game.reset)])
