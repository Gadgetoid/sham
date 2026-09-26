import random

from system import keys, store, ui
from system.gfx import CLEAR, MID, INK, small

TITLE = "Snake"
ICON = "misc:snake_1"
CATEGORY = "Games"
ORDER = 70

CELL = 4
START_INTERVAL = 140
FASTEST_INTERVAL = 50

DIRECTIONS = {
    keys.UP: (0, -1),
    keys.DOWN: (0, 1),
    keys.LEFT: (-1, 0),
    keys.RIGHT: (1, 0),
}


class Snake(ui.View):
    def __init__(self):
        super().__init__()
        self.menu_paused = False
        self.best = store.load("snake", {}).get("best", 0)
        self.state = "ready"

    def layout(self):
        self.columns = (self.w - 2) // CELL
        self.rows = (self.h - 2) // CELL
        self.left = (self.w - self.columns * CELL) // 2
        self.top = (self.h - self.rows * CELL) // 2
        self.reset()

    def reset(self):
        middle_x, middle_y = self.columns // 2, self.rows // 2
        self.body = [(middle_x - i, middle_y) for i in range(4)]
        self.direction = (1, 0)
        self.queued = []
        self.score = 0
        self.interval = START_INTERVAL
        self.last_step = 0
        self.place_food()

    def place_food(self):
        occupied = set(self.body)
        while True:
            food = (random.randrange(self.columns), random.randrange(self.rows))
            if food not in occupied:
                self.food = food
                return

    def key(self, key):
        code = keys.pad(key) if self.state == "playing" else key.code
        if code in DIRECTIONS:
            if self.state == "ready":
                self.state = "playing"
            self.queued.append(DIRECTIONS[code])
            return True
        if key.code == keys.ENTER or key.char == " ":
            if self.state == "over":
                self.reset()
                self.state = "playing"
            elif self.state == "playing":
                self.state = "paused"
            else:
                self.state = "playing"
            self.refresh()
            return True
        return False

    def turn(self):
        while self.queued:
            dx, dy = self.queued.pop(0)
            if (dx, dy) != (-self.direction[0], -self.direction[1]) and (dx, dy) != self.direction:
                self.direction = (dx, dy)
                return

    def step(self):
        self.turn()
        head_x, head_y = self.body[0]
        head = (head_x + self.direction[0], head_y + self.direction[1])
        hit_wall = not (0 <= head[0] < self.columns and 0 <= head[1] < self.rows)
        if hit_wall or head in self.body[:-1]:
            self.state = "over"
            if self.score > self.best:
                self.best = self.score
                store.save("snake", {"best": self.best})
            return
        self.body.insert(0, head)
        if head == self.food:
            self.score += 1
            self.interval = max(FASTEST_INTERVAL, self.interval - 5)
            self.place_food()
        else:
            self.body.pop()

    def pause(self):
        self.menu_paused = self.state == "playing"
        if self.menu_paused:
            self.state = "paused"
            self.refresh()

    def resume(self):
        if self.menu_paused and self.state == "paused":
            self.state = "playing"
            self.refresh()
        self.menu_paused = False

    def tick(self, now):
        if self.state != "playing" or now - self.last_step < self.interval:
            return
        self.last_step = now
        self.step()
        self.refresh()

    def cell(self, position, colour):
        x, y = position
        self.fill(self.left + x * CELL, self.top + y * CELL, CELL - 1, CELL - 1, colour)

    def draw(self):
        self.rect(self.left - 1, self.top - 1, self.columns * CELL + 1, self.rows * CELL + 1, MID)
        fx, fy = self.food
        self.rect(self.left + fx * CELL, self.top + fy * CELL, CELL - 1, CELL - 1, INK)
        for index, segment in enumerate(self.body):
            self.cell(segment, INK if index == 0 or index % 3 else MID)
        if self.state == "ready":
            self.banner("Arrows to start", "Best {}".format(self.best))
        elif self.state == "paused":
            self.banner("Paused", "Enter to resume")
        elif self.state == "over":
            self.banner("Game over, {} points".format(self.score), "Enter: again  Esc: quit")


def launch():
    game = Snake()
    return ui.Screen("Snake", game, status=lambda: "Score {}  Best {}".format(game.score, game.best))
