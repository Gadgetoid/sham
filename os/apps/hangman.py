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

    def scaled(self, value):
        return int(value * (self.h - 7) / 57 + 0.5)

    def draw_gallows(self):
        s = self.scaled
        base_y = self.h - 4
        self.line(s(4), base_y, s(40), base_y)
        self.line(s(12), base_y, s(12), s(3))
        self.line(s(12), s(3), s(36), s(3))
        self.line(s(12), s(11), s(20), s(3))
        self.line(s(36), s(3), s(36), s(10))
        misses = self.misses
        if misses > 0:
            self.rect(s(32), s(10), s(9), s(9), INK)
        if misses > 1:
            self.line(s(36), s(19), s(36), s(36))
        if misses > 2:
            self.line(s(36), s(23), s(29), s(30))
        if misses > 3:
            self.line(s(36), s(23), s(43), s(30))
        if misses > 4:
            self.line(s(36), s(36), s(30), s(46))
        if misses > 5:
            self.line(s(36), s(36), s(42), s(46))
            self.pixel(s(34), s(13))
            self.pixel(s(38), s(13))

    def draw(self):
        self.draw_gallows()
        reveal = self.state == "lost"
        left = self.scaled(40) + 16
        x = left
        for letter in self.word:
            shown = letter in self.guessed or reveal
            if shown:
                colour = MID if reveal and letter not in self.guessed else INK
                self.text(letter, x + (12 - large.measure(letter)) // 2 + 1, 12, colour, large)
            self.fill(x, 32, 11, 2, INK)
            x += 15
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for index, letter in enumerate(alphabet):
            px = left + (index % 13) * 13
            py = 48 + (index // 13) * 14
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
