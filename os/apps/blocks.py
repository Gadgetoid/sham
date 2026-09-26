import random

from system import keys, store, ui
from system.gfx import CLEAR, LIGHT, MID, INK, small

TITLE = "Blocks"
ICON = "boardgames:tetris_t1"
CATEGORY = "Games"
ORDER = 73

COLUMNS = 10
ROWS = 20
CELL = 4
KICKS = ((0, 0), (-1, 0), (1, 0), (0, -1), (-2, 0), (2, 0))
LINE_POINTS = (0, 100, 300, 500, 800)
SOFT_DROP_MS = 40

SHAPES = {
    "I": ((0, 1), (1, 1), (2, 1), (3, 1)),
    "O": ((1, 0), (2, 0), (1, 1), (2, 1)),
    "T": ((1, 0), (0, 1), (1, 1), (2, 1)),
    "S": ((1, 0), (2, 0), (0, 1), (1, 1)),
    "Z": ((0, 0), (1, 0), (1, 1), (2, 1)),
    "J": ((0, 0), (0, 1), (1, 1), (2, 1)),
    "L": ((2, 0), (0, 1), (1, 1), (2, 1)),
}
BOX = {"I": 4, "O": 4}


def rotations(name):
    size = BOX.get(name, 3)
    cells = SHAPES[name]
    result = [cells]
    if name == "O":
        return result * 4
    for _ in range(3):
        cells = tuple((size - 1 - y, x) for x, y in cells)
        result.append(cells)
    return result


ROTATIONS = {name: rotations(name) for name in SHAPES}


class Piece:
    def __init__(self, name):
        self.name = name
        self.rotation = 0
        self.x = 3
        self.y = 0

    def cells(self, rotation=None, x=None, y=None):
        rotation = self.rotation if rotation is None else rotation
        x = self.x if x is None else x
        y = self.y if y is None else y
        return [(x + cx, y + cy) for cx, cy in ROTATIONS[self.name][rotation % 4]]


class Blocks(ui.View):
    def __init__(self):
        super().__init__()
        self.best = store.load("blocks", {}).get("best", 0)
        self.new_game()

    def layout(self):
        self.board_x = (self.w - COLUMNS * CELL) // 2
        self.board_y = (self.h - ROWS * CELL) // 2

    def new_game(self):
        self.board = [[0] * COLUMNS for _ in range(ROWS)]
        self.bag = []
        self.queue = [self.draw_from_bag() for _ in range(3)]
        self.held_piece = None
        self.hold_used = False
        self.score = 0
        self.lines = 0
        self.state = "ready"
        self.last_fall = 0
        self.spawn()

    @property
    def level(self):
        return self.lines // 10 + 1

    def draw_from_bag(self):
        if not self.bag:
            self.bag = list(SHAPES)
            for index in range(len(self.bag) - 1, 0, -1):
                other = random.randrange(index + 1)
                self.bag[index], self.bag[other] = self.bag[other], self.bag[index]
        return self.bag.pop()

    def spawn(self, name=None):
        if name is None:
            name = self.queue.pop(0)
            self.queue.append(self.draw_from_bag())
        self.piece = Piece(name)
        if not self.fits(self.piece.cells()):
            self.state = "over"
            if self.score > self.best:
                self.best = self.score
                store.save("blocks", {"best": self.best})

    def fits(self, cells):
        for x, y in cells:
            if x < 0 or x >= COLUMNS or y >= ROWS:
                return False
            if y >= 0 and self.board[y][x]:
                return False
        return True

    def move(self, dx, dy):
        cells = self.piece.cells(x=self.piece.x + dx, y=self.piece.y + dy)
        if self.fits(cells):
            self.piece.x += dx
            self.piece.y += dy
            return True
        return False

    def rotate(self, step):
        rotation = self.piece.rotation + step
        for kx, ky in KICKS:
            if self.fits(self.piece.cells(rotation, self.piece.x + kx, self.piece.y + ky)):
                self.piece.rotation = rotation % 4
                self.piece.x += kx
                self.piece.y += ky
                return

    def drop_distance(self):
        distance = 0
        while self.fits(self.piece.cells(y=self.piece.y + distance + 1)):
            distance += 1
        return distance

    def lock(self):
        for x, y in self.piece.cells():
            if y >= 0:
                self.board[y][x] = 1
        full = [row for row in range(ROWS) if all(self.board[row])]
        for row in full:
            del self.board[row]
            self.board.insert(0, [0] * COLUMNS)
        self.score += LINE_POINTS[len(full)] * self.level
        self.lines += len(full)
        self.hold_used = False
        self.spawn()

    def hard_drop(self):
        distance = self.drop_distance()
        self.piece.y += distance
        self.score += distance * 2
        self.lock()

    def hold(self):
        if self.hold_used:
            return
        current = self.piece.name
        if self.held_piece:
            self.spawn(self.held_piece)
        else:
            self.spawn()
        self.held_piece = current
        self.hold_used = True

    def key(self, key):
        code = key.code
        char = key.char
        if self.state in ("ready", "over"):
            if code == keys.ENTER or char == " ":
                if self.state == "over":
                    self.new_game()
                self.state = "playing"
                self.refresh()
                return True
            return False
        if self.state == "paused":
            if code == keys.ENTER or char in ("p", "P"):
                self.state = "playing"
                self.refresh()
                return True
            return False
        if code == keys.LEFT:
            self.move(-1, 0)
        elif code == keys.RIGHT:
            self.move(1, 0)
        elif code == keys.UP or char in ("x", "X"):
            self.rotate(1)
        elif char in ("z", "Z"):
            self.rotate(-1)
        elif code == keys.DOWN:
            if self.move(0, 1):
                self.score += 1
        elif char == " " or code == keys.ENTER:
            self.hard_drop()
        elif char in ("c", "C"):
            self.hold()
        elif char in ("p", "P"):
            self.state = "paused"
        else:
            return False
        self.refresh()
        return True

    def pause(self):
        if self.state == "playing":
            self.state = "paused"
            self.refresh()

    def tick(self, now):
        if self.state != "playing":
            return
        interval = max(80, 800 - (self.level - 1) * 70)
        if keys.held(keys.DOWN):
            interval = min(interval, SOFT_DROP_MS)
        if now - self.last_fall < interval:
            return
        self.last_fall = now
        if not self.move(0, 1):
            self.lock()
        self.refresh()

    def block(self, x, y, colour=INK):
        if colour == INK:
            self.fill(x, y, CELL, CELL, MID)
            self.fill(x, y, CELL - 1, CELL - 1, INK)
        else:
            self.fill(x, y, CELL, CELL, colour)

    def board_block(self, column, row, colour=INK):
        if row >= 0:
            self.block(self.board_x + column * CELL, self.board_y + row * CELL, colour)

    def preview(self, name, x, y):
        for cx, cy in SHAPES[name]:
            self.block(x + cx * CELL, y + cy * CELL)

    def draw(self):
        board_w = COLUMNS * CELL
        self.rect(self.board_x - 2, self.board_y - 2, board_w + 4, ROWS * CELL + 4, INK)
        for row in range(ROWS):
            for column in range(COLUMNS):
                if self.board[row][column]:
                    self.board_block(column, row)
        if self.state != "over":
            distance = self.drop_distance()
            for x, y in self.piece.cells(y=self.piece.y + distance):
                self.board_block(x, y, LIGHT)
            for x, y in self.piece.cells():
                self.board_block(x, y)

        left = self.board_x - 60
        self.text("HOLD", left, 2, MID)
        if self.held_piece:
            self.preview(self.held_piece, left, 16)
        self.text("LINES {}".format(self.lines), left, 44, MID)
        self.text("LEVEL {}".format(self.level), left, 58, MID)

        right = self.board_x + board_w + 12
        self.text("NEXT", right, 2, MID)
        for index, name in enumerate(self.queue[:2]):
            self.preview(name, right + index * (4 * CELL + 4), 16)
        self.text("BEST {}".format(self.best), right, 44, MID)
        self.text("P pause", right, 58, MID)

        if self.state == "ready":
            self.banner("Enter to start", "Up/X Z rotate", "Space drop C hold")
        elif self.state == "paused":
            self.banner("Paused")
        elif self.state == "over":
            self.banner("Game over", "{} points".format(self.score), "Enter: again")


def launch():
    game = Blocks()
    return ui.Screen("Blocks", game, status=lambda: "Score {}".format(game.score))
