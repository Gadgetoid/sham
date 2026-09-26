import random

from system import keys, sound, ui
from system.gfx import CLEAR, LIGHT, MID, INK, small

TITLE = "Solitaire"
ICON = "boardgames:cards"
CATEGORY = "Games"
ORDER = 78

CARD_W = 30
CARD_H = 26
COLUMN_X = 2
COLUMN_STEP = 33
RIGHT_X = 233
RIGHT_STEP = 33
ROW_STEP = 30
DOWN_STEP = 3
UP_STEP = 9

RANKS = ("", "A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
SPADES, HEARTS, DIAMONDS, CLUBS = range(4)

SUITS = (
    ("..#..", ".###.", "#####", "..#..", ".###."),
    (".#.#.", "#####", "#####", ".###.", "..#.."),
    ("..#..", ".###.", "#####", ".###.", "..#.."),
    (".###.", ".###.", "#####", "#####", "..#.."),
)


def is_red(card):
    return card[1] in (HEARTS, DIAMONDS)


class Solitaire(ui.View):
    def __init__(self):
        super().__init__()
        self.new_game()

    def new_game(self):
        deck = [(rank, suit) for suit in range(4) for rank in range(1, 14)]
        for index in range(len(deck) - 1, 0, -1):
            other = random.randrange(index + 1)
            deck[index], deck[other] = deck[other], deck[index]
        self.tableau = []
        for column in range(7):
            pile = [[deck.pop(), False] for _ in range(column + 1)]
            pile[-1][1] = True
            self.tableau.append(pile)
        self.stock = deck
        self.waste = []
        self.foundations = [[] for _ in range(4)]
        self.cursor = ("tableau", 0)
        self.depth = 1
        self.held = None
        self.moves = 0
        self.won = False
        self.refresh()

    def face_up_count(self, column):
        return sum(1 for card, up in self.tableau[column] if up)

    def cards_at(self, place, count=1):
        kind, index = place
        if kind == "tableau":
            return [card for card, up in self.tableau[index][-count:]]
        if kind == "waste":
            return self.waste[-1:]
        if kind == "foundation":
            return self.foundations[index][-1:]
        return []

    def remove(self, place, count):
        kind, index = place
        if kind == "tableau":
            del self.tableau[index][-count:]
            if self.tableau[index] and not self.tableau[index][-1][1]:
                self.tableau[index][-1][1] = True
        elif kind == "waste":
            self.waste.pop()
        elif kind == "foundation":
            self.foundations[index].pop()

    def can_drop(self, cards, place):
        kind, index = place
        first = cards[0]
        if kind == "tableau":
            pile = self.tableau[index]
            if not pile:
                return first[0] == 13
            top, up = pile[-1]
            return up and top[0] == first[0] + 1 and is_red(top) != is_red(first)
        if kind == "foundation":
            pile = self.foundations[index]
            return len(cards) == 1 and first[1] == index and first[0] == len(pile) + 1
        return False

    def drop(self, cards, place):
        kind, index = place
        if kind == "tableau":
            self.tableau[index].extend([card, True] for card in cards)
        else:
            self.foundations[index].extend(cards)
        self.moves += 1
        if all(len(pile) == 13 for pile in self.foundations):
            self.won = True
            sound.play("C5 E5 G5 C6 G5 C6:3", 90)
        else:
            sound.beep(1300, 12)

    def draw_stock(self):
        if self.stock:
            self.waste.append(self.stock.pop())
        else:
            self.stock = self.waste[::-1]
            self.waste = []
        self.moves += 1
        sound.beep(700, 8)

    def auto_foundation(self, place):
        cards = self.cards_at(place)
        if not cards:
            return False
        target = ("foundation", cards[0][1])
        if place != target and self.can_drop(cards, target):
            self.remove(place, 1)
            self.drop(cards, target)
            return True
        return False

    def activate(self):
        place = self.cursor
        kind, index = place
        if self.held:
            source, count = self.held
            cards = self.cards_at(source, count)
            self.held = None
            if source != place and self.can_drop(cards, place):
                self.remove(source, count)
                self.drop(cards, place)
            elif source != place:
                sound.beep(300, 60)
            return
        if kind == "stock":
            self.draw_stock()
        elif kind == "tableau":
            pile = self.tableau[index]
            if pile and not pile[-1][1]:
                pile[-1][1] = True
            elif pile:
                self.held = (place, min(self.depth, self.face_up_count(index)))
        elif self.cards_at(place):
            self.held = (place, 1)

    def move_cursor(self, dx, dy):
        kind, index = self.cursor
        right = [("stock", 0), ("waste", 0), ("foundation", 0), ("foundation", 1), ("foundation", 2), ("foundation", 3)]
        if kind == "tableau":
            if dx:
                index += dx
                if index > 6:
                    self.cursor = right[0]
                elif index < 0:
                    self.cursor = right[1]
                else:
                    self.cursor = ("tableau", index)
            else:
                self.depth = max(1, min(self.face_up_count(index), self.depth - dy))
                return
        else:
            position = right.index(self.cursor)
            row, column = position // 2, position % 2
            if dy:
                row = (row + dy) % 3
                self.cursor = right[row * 2 + column]
            elif column + dx > 1:
                self.cursor = ("tableau", 0)
            elif column + dx < 0:
                self.cursor = ("tableau", 6)
            else:
                self.cursor = right[row * 2 + column + dx]
        self.depth = 1

    def key(self, key):
        code = key.code
        char = key.char
        if self.won:
            if code == keys.ENTER or char == " ":
                self.new_game()
                return True
            return False
        moves = {keys.UP: (0, -1), keys.DOWN: (0, 1), keys.LEFT: (-1, 0), keys.RIGHT: (1, 0)}
        if code in moves:
            self.move_cursor(*moves[code])
        elif code == keys.ENTER:
            self.activate()
        elif char == " ":
            self.held = None
            if not self.auto_foundation(self.cursor):
                sound.beep(300, 40)
        elif code == keys.ESC and self.held:
            self.held = None
        else:
            return False
        self.refresh()
        return True

    def draw_card(self, card, x, y, height, up=True):
        self.fill(x, y, CARD_W, height, CLEAR)
        self.rect(x, y, CARD_W, height, INK)
        if not up:
            for dy in range(2, height - 1, 2):
                for dx in range(2 + (dy // 2) % 2, CARD_W - 1, 2):
                    self.pixel(x + dx, y + dy, MID)
            return
        colour = MID if is_red(card) else INK
        rank = RANKS[card[0]]
        width = self.text(rank, x + 2, y + 1, colour)
        self.sprite(SUITS[card[1]], x + width + 3, y + 3, colour)
        if height >= CARD_H:
            self.sprite(SUITS[card[1]], x + CARD_W - 7, y + height - 7, colour)

    def draw_slot(self, x, y, suit=None):
        self.rect(x, y, CARD_W, CARD_H, LIGHT)
        if suit is not None:
            self.sprite(SUITS[suit], x + (CARD_W - 5) // 2, y + (CARD_H - 5) // 2, LIGHT)

    def column_steps(self, column):
        pile = self.tableau[column]
        down = sum(1 for card, up in pile if not up)
        up = len(pile) - down
        down_step, up_step = DOWN_STEP, UP_STEP
        if up > 1 and down * down_step + (up - 1) * up_step + CARD_H > self.h:
            up_step = max(4, (self.h - CARD_H - down * down_step) // (up - 1))
        if down * down_step + (up - 1) * up_step + CARD_H > self.h:
            down_step = 1
        return down_step, up_step

    def place_rect(self, place, count=1):
        kind, index = place
        if kind == "tableau":
            pile = self.tableau[index]
            x = COLUMN_X + index * COLUMN_STEP
            if not pile:
                return x, 0, CARD_H
            down_step, up_step = self.column_steps(index)
            y = 0
            first = len(pile) - count
            for position, (card, up) in enumerate(pile[:first]):
                y += up_step if up else down_step
            height = self.card_y_end(index) - y
            return x, y, height
        slots = {"stock": (0, 0), "waste": (1, 0)}
        if kind in slots:
            column, row = slots[kind]
        else:
            column, row = index % 2, 1 + index // 2
        return RIGHT_X + column * RIGHT_STEP, row * ROW_STEP, CARD_H

    def card_y_end(self, column):
        pile = self.tableau[column]
        down_step, up_step = self.column_steps(column)
        y = 0
        for card, up in pile[:-1]:
            y += up_step if up else down_step
        return y + CARD_H

    def draw(self):
        for column, pile in enumerate(self.tableau):
            x = COLUMN_X + column * COLUMN_STEP
            if not pile:
                self.draw_slot(x, 0)
                continue
            down_step, up_step = self.column_steps(column)
            y = 0
            for position, (card, up) in enumerate(pile):
                last = position == len(pile) - 1
                step = up_step if up else down_step
                self.draw_card(card, x, y, CARD_H if last else step + 1, up)
                y += step

        stock_x, stock_y, _ = self.place_rect(("stock", 0))
        if self.stock:
            self.draw_card(None, stock_x, stock_y, CARD_H, up=False)
        else:
            self.draw_slot(stock_x, stock_y)
            self.sprite(("..#..", ".#.#.", "#...#", ".#.#.", "..#.."), stock_x + 9, stock_y + 7, LIGHT)
        waste_x, waste_y, _ = self.place_rect(("waste", 0))
        if self.waste:
            self.draw_card(self.waste[-1], waste_x, waste_y, CARD_H)
        else:
            self.draw_slot(waste_x, waste_y)
        for suit in range(4):
            x, y, _ = self.place_rect(("foundation", suit))
            if self.foundations[suit]:
                self.draw_card(self.foundations[suit][-1], x, y, CARD_H)
            else:
                self.draw_slot(x, y, suit)

        if self.held:
            source, count = self.held
            x, y, height = self.place_rect(source, count)
            self.invert(x + 1, y + 1, CARD_W - 2, height - 2)
        count = self.depth if self.cursor[0] == "tableau" else 1
        x, y, height = self.place_rect(self.cursor, max(1, min(count, len(self.tableau[self.cursor[1]]) if self.cursor[0] == "tableau" else 1)))
        self.rect(x - 1, y, CARD_W + 2, height, INK)
        self.rect(x - 2, y, CARD_W + 4, height, INK if self.held else MID)
        if self.won:
            self.banner("You won in {} moves!".format(self.moves), "Enter: deal again")


def launch():
    game = Solitaire()
    return ui.Screen("Solitaire", game,
                     status=lambda: "{} moves  {} left".format(game.moves, len(game.stock)),
                     menu=[("New deal", game.new_game)])
