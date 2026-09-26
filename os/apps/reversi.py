import host
from system import keys, sound, ui
from system.gfx import CLEAR, LIGHT, MID, INK, small

TITLE = "Reversi"
ICON = "boardgames:chip_counter"
CATEGORY = "Games"
ORDER = 74

SIZE = 8
CELL = 10
EMPTY, BLACK, WHITE = 0, 1, 2
CPU_DELAY_MS = 450

DIRECTIONS = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]

WEIGHTS = (
    (100, -20, 10, 5, 5, 10, -20, 100),
    (-20, -50, -2, -2, -2, -2, -50, -20),
    (10, -2, 1, 1, 1, 1, -2, 10),
    (5, -2, 1, 0, 0, 1, -2, 5),
    (5, -2, 1, 0, 0, 1, -2, 5),
    (10, -2, 1, 1, 1, 1, -2, 10),
    (-20, -50, -2, -2, -2, -2, -50, -20),
    (100, -20, 10, 5, 5, 10, -20, 100),
)

DISC = (
    "..###..",
    ".#####.",
    "#######",
    "#######",
    "#######",
    ".#####.",
    "..###..",
)

RING = (
    "..###..",
    ".#...#.",
    "#.....#",
    "#.....#",
    "#.....#",
    ".#...#.",
    "..###..",
)


def opponent(player):
    return WHITE if player == BLACK else BLACK


def flips(board, x, y, player):
    if board[y][x] != EMPTY:
        return []
    other = opponent(player)
    flipped = []
    for dx, dy in DIRECTIONS:
        run = []
        cx, cy = x + dx, y + dy
        while 0 <= cx < SIZE and 0 <= cy < SIZE and board[cy][cx] == other:
            run.append((cx, cy))
            cx += dx
            cy += dy
        if run and 0 <= cx < SIZE and 0 <= cy < SIZE and board[cy][cx] == player:
            flipped.extend(run)
    return flipped


def legal_moves(board, player):
    return [(x, y) for y in range(SIZE) for x in range(SIZE) if flips(board, x, y, player)]


def count(board, player):
    return sum(row.count(player) for row in board)


def choose_move(board, player):
    best = None
    for x, y in legal_moves(board, player):
        trial = [row[:] for row in board]
        for fx, fy in flips(trial, x, y, player) + [(x, y)]:
            trial[fy][fx] = player
        replies = len(legal_moves(trial, opponent(player)))
        score = WEIGHTS[y][x] + len(flips(board, x, y, player)) - replies * 2
        if best is None or score > best[0]:
            best = (score, x, y)
    return best[1:] if best else None


class Reversi(ui.View):
    def __init__(self):
        super().__init__()
        self.new_game()

    def layout(self):
        self.left = 6
        self.top = (self.h - SIZE * CELL) // 2

    def new_game(self):
        self.board = [[EMPTY] * SIZE for _ in range(SIZE)]
        self.board[3][3] = self.board[4][4] = WHITE
        self.board[3][4] = self.board[4][3] = BLACK
        self.turn = BLACK
        self.cursor = (2, 3)
        self.over = False
        self.message = "Your move"
        self.cpu_at = None
        self.refresh()

    def play(self, x, y, player):
        flipped = flips(self.board, x, y, player)
        for fx, fy in flipped + [(x, y)]:
            self.board[fy][fx] = player
        sound.beep(1600 if player == BLACK else 1100, 25)
        self.advance(opponent(player))

    def advance(self, player):
        if legal_moves(self.board, player):
            self.turn = player
        elif legal_moves(self.board, opponent(player)):
            self.turn = opponent(player)
            self.message = "{} must pass".format("You" if player == BLACK else "CPU")
        else:
            self.finish()
            return
        if self.turn == WHITE:
            self.cpu_at = host.ticks_ms() + CPU_DELAY_MS
        elif not self.message.endswith("pass"):
            self.message = "Your move"

    def finish(self):
        self.over = True
        mine, theirs = count(self.board, BLACK), count(self.board, WHITE)
        if mine > theirs:
            self.message = "You win {}-{}".format(mine, theirs)
        elif theirs > mine:
            self.message = "CPU wins {}-{}".format(theirs, mine)
        else:
            self.message = "Draw {}-{}".format(mine, theirs)

    def tick(self, now):
        if self.cpu_at is not None and now >= self.cpu_at and not self.over:
            self.cpu_at = None
            move = choose_move(self.board, WHITE)
            if move:
                self.message = "CPU played"
                self.play(move[0], move[1], WHITE)
            self.refresh()

    def key(self, key):
        code = key.code
        if self.over:
            if code == keys.ENTER or key.char == " ":
                self.new_game()
                return True
            return False
        x, y = self.cursor
        moves = {keys.UP: (0, -1), keys.DOWN: (0, 1), keys.LEFT: (-1, 0), keys.RIGHT: (1, 0)}
        if code in moves:
            dx, dy = moves[code]
            self.cursor = ((x + dx) % SIZE, (y + dy) % SIZE)
        elif code == keys.ENTER or key.char == " ":
            if self.turn != BLACK:
                return True
            if flips(self.board, x, y, BLACK):
                self.message = ""
                self.play(x, y, BLACK)
            else:
                sound.beep(300, 60)
        else:
            return False
        self.refresh()
        return True

    def draw(self):
        board_px = SIZE * CELL
        self.rect(self.left - 1, self.top - 1, board_px + 1, board_px + 1, MID)
        for i in range(1, SIZE):
            self.fill(self.left + i * CELL - 1, self.top, 1, board_px, LIGHT)
            self.fill(self.left, self.top + i * CELL - 1, board_px, 1, LIGHT)
        hints = legal_moves(self.board, BLACK) if self.turn == BLACK and not self.over else []
        for y in range(SIZE):
            for x in range(SIZE):
                px = self.left + x * CELL
                py = self.top + y * CELL
                cell = self.board[y][x]
                if cell == BLACK:
                    self.sprite(DISC, px + 1, py + 1, INK)
                elif cell == WHITE:
                    self.sprite(DISC, px + 1, py + 1, CLEAR)
                    self.sprite(RING, px + 1, py + 1, INK)
                elif (x, y) in hints:
                    self.fill(px + 4, py + 4, 1, 1, MID)
        if not self.over:
            cx, cy = self.cursor
            self.rect(self.left + cx * CELL - 1, self.top + cy * CELL - 1, CELL + 1, CELL + 1, INK)

        panel = self.left + board_px + 16
        self.sprite(DISC, panel, 8, INK)
        self.text("You  {}".format(count(self.board, BLACK)), panel + 11, 8)
        self.sprite(RING, panel, 22, INK)
        self.text("CPU  {}".format(count(self.board, WHITE)), panel + 11, 22)
        if self.turn == WHITE and not self.over:
            self.text("Thinking...", panel, 44, MID)
        else:
            self.text(self.message, panel, 44)
        self.text("Enter: new game" if self.over else "Enter: place", panel, 70, MID)


def launch():
    game = Reversi()
    return ui.Screen("Reversi", game, status="You are black", menu=[("New game", game.new_game)])
