import random

from system import keys, sound, ui
from system.gfx import CLEAR, LIGHT, MID, INK, small

TITLE = "Codebreaker"
ICON = "tools_crafting:padlock"
CATEGORY = "Games"
ORDER = 75

PEGS = 4
SYMBOLS = 6
TURNS = 10
COLUMN_W = 13
SLOT_H = 12

SHAPES = (
    (".###.", "#####", "#####", "#####", ".###."),
    (".###.", "#...#", "#...#", "#...#", ".###."),
    ("#####", "#####", "#####", "#####", "#####"),
    ("#####", "#...#", "#...#", "#...#", "#####"),
    ("..#..", ".###.", ".###.", "#####", "#####"),
    ("#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
)


def score(secret, guess):
    exact = sum(1 for s, g in zip(secret, guess) if s == g)
    common = sum(min(secret.count(symbol), guess.count(symbol)) for symbol in range(SYMBOLS))
    return exact, common - exact


class Codebreaker(ui.View):
    def __init__(self):
        super().__init__()
        self.new_game()

    def new_game(self):
        self.secret = [random.randrange(SYMBOLS) for _ in range(PEGS)]
        self.guesses = []
        self.current = [None] * PEGS
        self.slot = 0
        self.state = "playing"
        self.refresh()

    def submit(self):
        if None in self.current:
            sound.beep(300, 60)
            return
        result = score(self.secret, self.current)
        self.guesses.append((self.current, result))
        self.current = [None] * PEGS
        self.slot = 0
        if result[0] == PEGS:
            self.state = "won"
            sound.play("C5 E5 G5 C6:2", 90)
        elif len(self.guesses) >= TURNS:
            self.state = "lost"
            sound.play("G4 E4 C4:2", 120)
        else:
            sound.beep(1400, 30)

    def key(self, key):
        code = key.code
        char = key.char
        if self.state != "playing":
            if code == keys.ENTER or char == " ":
                self.new_game()
                return True
            return False
        if char and "1" <= char <= str(SYMBOLS):
            self.current[self.slot] = int(char) - 1
            self.slot = min(PEGS - 1, self.slot + 1)
        elif code == keys.UP:
            self.slot = (self.slot - 1) % PEGS
        elif code == keys.DOWN:
            self.slot = (self.slot + 1) % PEGS
        elif code in (keys.LEFT, keys.RIGHT):
            step = -1 if code == keys.LEFT else 1
            value = self.current[self.slot]
            self.current[self.slot] = (step if value is None else value + step) % SYMBOLS
        elif code == keys.BACKSPACE:
            self.current[self.slot] = None
            self.slot = max(0, self.slot - 1)
        elif code == keys.ENTER:
            self.submit()
        else:
            return False
        self.refresh()
        return True

    def draw_pegs(self, pegs, x, highlight_slot=None):
        for slot, symbol in enumerate(pegs):
            y = 2 + slot * SLOT_H
            if symbol is None:
                self.fill(x + 3, y + 3, 1, 1, MID)
            else:
                self.sprite(SHAPES[symbol], x + 1, y + 1)
            if slot == highlight_slot:
                self.rect(x - 1, y - 1, 9, 9, INK)

    def draw_feedback(self, result, x):
        exact, near = result
        marks = ["exact"] * exact + ["near"] * near
        for index in range(PEGS):
            px = x + 1 + (index % 2) * 4
            py = 54 + (index // 2) * 4
            if index < len(marks):
                if marks[index] == "exact":
                    self.fill(px, py, 3, 3, INK)
                else:
                    self.rect(px, py, 3, 3, INK)
            else:
                self.pixel(px + 1, py + 1, LIGHT)

    def draw(self):
        for turn in range(TURNS):
            x = 3 + turn * COLUMN_W
            if turn < len(self.guesses):
                pegs, result = self.guesses[turn]
                self.draw_pegs(pegs, x)
                self.draw_feedback(result, x)
            elif turn == len(self.guesses) and self.state == "playing":
                self.fill(x - 2, 0, COLUMN_W - 1, self.h, LIGHT)
                self.draw_pegs(self.current, x, self.slot)
            else:
                self.draw_pegs([None] * PEGS, x)
            self.text(str(turn + 1), x + (7 - small.measure(str(turn + 1))) // 2, 70, MID)

        panel = 3 + TURNS * COLUMN_W + 6
        self.fill(panel - 4, 0, 1, self.h, MID)
        for symbol in range(SYMBOLS):
            px = panel + (symbol % 2) * 34
            py = 2 + (symbol // 2) * 13
            self.text(str(symbol + 1), px, py + 1, MID)
            self.sprite(SHAPES[symbol], px + 8, py + 1)
        if self.state == "playing":
            self.text("Enter: guess", panel, 46, MID)
            self.text("1-6 or arrows", panel, 60, MID)
        else:
            self.text("You cracked it" if self.state == "won" else "Code was", panel, 46)
            for slot, symbol in enumerate(self.secret):
                self.sprite(SHAPES[symbol], panel + slot * 9, 60)


def launch():
    game = Codebreaker()
    return ui.Screen("Codebreaker", game,
                     status=lambda: "Guess {}/{}".format(min(len(game.guesses) + 1, TURNS), TURNS),
                     menu=[("New game", game.new_game)])
