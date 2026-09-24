import random

from system import keys, sound, ui
from system.gfx import LIGHT, MID, INK, small, large

TITLE = "Hangman"
ICON = "boardgames:scrabble"
CATEGORY = "Games"
ORDER = 76

WORDS = (
    "ORGANISER", "MODEM", "FLOPPY", "PAGER", "BACKLIGHT", "STYLUS", "INFRARED", "DATABANK",
    "SPREADSHEET", "KEYBOARD", "BATTERY", "CALCULATOR", "PIXEL", "CURSOR", "SCHEDULE", "MEMORY",
    "PROGRAM", "DIARY", "ALARM", "EXPENSE", "BINARY", "SERIAL", "CABLE", "DISPLAY", "HINGE",
    "PALMTOP", "POCKET", "SYNC", "BEEPER", "CONTRAST", "ADDRESS", "AGENDA", "WIZARD", "PSION",
    "RECHARGE", "MEGABYTE", "KILOBYTE", "EPROM", "PROCESSOR", "CLAMSHELL", "DOCKING", "TRAVEL",
    "CONVERSION", "CURRENCY", "PASSWORD", "NETWORK", "DIALUP", "EMAIL", "BROWSER", "SOFTWARE",
)

MISSES = 6


class Hangman(ui.View):
    def __init__(self):
        super().__init__()
        self.new_game()

    def new_game(self):
        self.word = random.choice(WORDS)
        self.guessed = set()
        self.state = "playing"
        self.refresh()

    @property
    def misses(self):
        return len([letter for letter in self.guessed if letter not in self.word])

    def guess(self, letter):
        if letter in self.guessed:
            return
        self.guessed.add(letter)
        if letter in self.word:
            sound.beep(1500, 30)
            if all(c in self.guessed for c in self.word):
                self.state = "won"
                sound.play("C5 E5 G5:2", 90)
        else:
            sound.beep(400, 80)
            if self.misses >= MISSES:
                self.state = "lost"
                sound.play("E4 C4:3", 150)

    def key(self, key):
        if self.state != "playing":
            if key.code == keys.ENTER or key.char == " ":
                self.new_game()
                return True
            return False
        char = key.char
        if char and char.isalpha() and len(char) == 1:
            self.guess(char.upper())
            self.refresh()
            return True
        return False

    def draw_gallows(self):
        base_y = self.h - 4
        self.line(4, base_y, 40, base_y)
        self.line(12, base_y, 12, 3)
        self.line(12, 3, 36, 3)
        self.line(12, 11, 20, 3)
        self.line(36, 3, 36, 10)
        misses = self.misses
        if misses > 0:
            self.rect(32, 10, 9, 9, INK)
        if misses > 1:
            self.line(36, 19, 36, 36)
        if misses > 2:
            self.line(36, 23, 29, 30)
        if misses > 3:
            self.line(36, 23, 43, 30)
        if misses > 4:
            self.line(36, 36, 30, 46)
        if misses > 5:
            self.line(36, 36, 42, 46)
            self.pixel(34, 13)
            self.pixel(38, 13)

    def draw(self):
        self.draw_gallows()
        reveal = self.state == "lost"
        x = 56
        for letter in self.word:
            shown = letter in self.guessed or reveal
            if shown:
                colour = MID if reveal and letter not in self.guessed else INK
                self.text(letter, x + (12 - large.measure(letter)) // 2 + 1, 6, colour, large)
            self.fill(x, 26, 11, 2, INK)
            x += 15
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for index, letter in enumerate(alphabet):
            px = 56 + (index % 13) * 13
            py = 38 + (index // 13) * 12
            if letter in self.guessed:
                colour = LIGHT if letter not in self.word else MID
            else:
                colour = INK
            self.text(letter, px, py, colour)
        if self.state == "won":
            self.banner("Got it!", "Enter: another word", bottom=True)
        elif self.state == "lost":
            self.banner("Hanged.", "Enter: another word", bottom=True)


def launch():
    game = Hangman()
    return ui.Screen("Hangman", game,
                     status=lambda: "Misses {}/{}".format(game.misses, MISSES),
                     menu=[("New word", game.new_game)])
