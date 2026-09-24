import math

from system import keys, store, ui
from system.gfx import CLEAR, MID, INK, small

TITLE = "Breakout"
ICON = "map_markers:building_wall"
CATEGORY = "Games"
ORDER = 72

BRICK_W = 18
BRICK_H = 4
BRICK_ROWS = 4
BRICK_TOP = 4
PADDLE_W = 26
PADDLE_SPEED = 150
PADDLE_NUDGE = 8
BALL = 2
START_SPEED = 70
ROW_COLOURS = (INK, INK, MID, MID)
ROW_POINTS = (7, 5, 3, 1)


class Breakout(ui.View):
    def __init__(self):
        super().__init__()
        self.best = store.load("breakout", {}).get("best", 0)
        self.score = 0
        self.lives = 3
        self.level = 1

    def layout(self):
        self.columns = (self.w - 1) // (BRICK_W + 1)
        self.brick_left = (self.w - self.columns * (BRICK_W + 1) + 1) // 2
        self.paddle_y = self.h - 4
        self.new_game()

    def new_game(self):
        self.score = 0
        self.lives = 3
        self.level = 1
        self.build_wall()
        self.serve()
        self.state = "ready"

    def build_wall(self):
        self.bricks = []
        for row in range(BRICK_ROWS):
            for column in range(self.columns):
                x = self.brick_left + column * (BRICK_W + 1)
                y = BRICK_TOP + row * (BRICK_H + 1)
                self.bricks.append([x, y, row])

    def serve(self):
        self.paddle_x = (self.w - PADDLE_W) / 2
        self.stuck = True
        self.speed = START_SPEED + (self.level - 1) * 12
        self.place_on_paddle()
        self.last = None

    def place_on_paddle(self):
        self.ball_x = self.paddle_x + PADDLE_W / 2 - BALL / 2
        self.ball_y = self.paddle_y - BALL - 1

    def launch_ball(self):
        self.stuck = False
        angle = math.radians(60)
        self.vx = self.speed * math.cos(angle)
        self.vy = -self.speed * math.sin(angle)

    def key(self, key):
        code = key.code
        if code in (keys.LEFT, keys.RIGHT):
            if not keys.held(code):
                self.paddle_x += PADDLE_NUDGE if code == keys.RIGHT else -PADDLE_NUDGE
                self.clamp_paddle()
            if self.state == "ready":
                self.state = "playing"
            self.refresh()
            return True
        if code == keys.ENTER or key.char == " " or code == keys.UP:
            if self.state == "over":
                self.new_game()
            elif self.state == "ready":
                self.state = "playing"
                self.launch_ball()
            elif self.state == "paused":
                self.state = "playing"
            elif self.stuck:
                self.launch_ball()
            elif code != keys.UP:
                self.state = "paused"
            self.refresh()
            return True
        return False

    def clamp_paddle(self):
        self.paddle_x = max(0, min(self.w - PADDLE_W, self.paddle_x))
        if self.stuck:
            self.place_on_paddle()

    def overlaps(self, x, y, w, h):
        return self.ball_x < x + w and self.ball_x + BALL > x and self.ball_y < y + h and self.ball_y + BALL > y

    def hit_brick(self):
        for brick in self.bricks:
            if self.overlaps(brick[0], brick[1], BRICK_W, BRICK_H):
                self.bricks.remove(brick)
                self.score += ROW_POINTS[brick[2]] * self.level
                return True
        return False

    def bounce_off_paddle(self):
        centre = self.paddle_x + PADDLE_W / 2
        offset = (self.ball_x + BALL / 2 - centre) / (PADDLE_W / 2)
        offset = max(-0.9, min(0.9, offset))
        self.vx = self.speed * offset
        self.vy = -math.sqrt(self.speed * self.speed - self.vx * self.vx)
        self.ball_y = self.paddle_y - BALL

    def advance(self, dt):
        steps = max(1, int(self.speed * dt) + 1)
        for _ in range(steps):
            self.ball_x += self.vx * dt / steps
            if self.ball_x <= 0 or self.ball_x >= self.w - BALL:
                self.ball_x = max(0, min(self.w - BALL, self.ball_x))
                self.vx = -self.vx
            elif self.hit_brick():
                self.vx = -self.vx
            self.ball_y += self.vy * dt / steps
            if self.ball_y <= 0:
                self.ball_y = 0
                self.vy = -self.vy
            elif self.hit_brick():
                self.vy = -self.vy
            if self.vy > 0 and self.overlaps(self.paddle_x, self.paddle_y, PADDLE_W, 2):
                self.bounce_off_paddle()
            if self.ball_y > self.h:
                self.lose_life()
                return
        if not self.bricks:
            self.level += 1
            self.build_wall()
            self.serve()

    def lose_life(self):
        self.lives -= 1
        if self.lives <= 0:
            self.state = "over"
            if self.score > self.best:
                self.best = self.score
                store.save("breakout", {"best": self.best})
        else:
            self.serve()

    def tick(self, now):
        if self.state != "playing":
            self.last = None
            return
        dt = 0 if self.last is None else min(0.05, (now - self.last) / 1000)
        self.last = now
        direction = keys.held(keys.RIGHT) - keys.held(keys.LEFT)
        if direction:
            self.paddle_x += direction * PADDLE_SPEED * dt
            self.clamp_paddle()
        if not self.stuck:
            self.advance(dt)
        self.refresh()

    def banner(self, *lines):
        width = max(small.measure(line) for line in lines) + 10
        height = len(lines) * small.line_height + 6
        x = (self.w - width) // 2
        y = self.h - height - 10
        self.fill(x, y, width, height, CLEAR)
        self.rect(x, y, width, height, INK)
        for index, line in enumerate(lines):
            self.text(line, x + (width - small.measure(line)) // 2, y + 3 + index * small.line_height)

    def draw(self):
        for x, y, row in self.bricks:
            self.fill(x, y, BRICK_W, BRICK_H, ROW_COLOURS[row])
        paddle_x = int(self.paddle_x)
        self.fill(paddle_x, self.paddle_y, PADDLE_W, 2, INK)
        self.fill(paddle_x + 2, self.paddle_y + 2, PADDLE_W - 4, 1, MID)
        self.fill(int(self.ball_x), int(self.ball_y), BALL, BALL, INK)
        if self.state == "ready":
            self.banner("Enter to serve, arrows move", "Best {}".format(self.best))
        elif self.state == "paused":
            self.banner("Paused")
        elif self.state == "over":
            self.banner("Game over, {} points".format(self.score), "Enter: again  Esc: quit")


def launch():
    game = Breakout()
    return ui.Screen("Breakout", game,
                     status=lambda: "L{}  {}  Balls {}".format(game.level, game.score, game.lives))
