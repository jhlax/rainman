import collections
import random
import time
from pprint import pprint

# card namedtuple
Card = collections.namedtuple("Card", ["rank", "suit"])


def format_card(card):
    """
    returns a formatted str of a card as its "{rank} of {suit}"
    """
    cardfmt = "{0:2s} of {1:8s}"
    return cardfmt.format(*card)


def card_value(card):
    """
    returns its +1, 0 -1 in terms of counting
    """
    if card.rank in "23456":
        return 1
    elif card.rank in "789":
        return 0
    else:
        return -1


class FrenchDeck:
    """
    the french deck class
    """

    ranks = [str(n) for n in range(2, 11)] + list("JQKA")
    suits = "spades diamonds clubs hearts".split()

    def __init__(self):
        self._cards = [Card(rank, suit) for suit in self.suits for rank in self.ranks]

    def __len__(self):
        return len(self._cards)

    def __getitem__(self, position):
        return self._cards[position]


# reference deck
ADECK = FrenchDeck()
# number of cards in the reference deck
DECKN = len(ADECK)


def create_stack(decks):
    """
    returns a dict of the {rank: number} of the initial values for
    each rank
    """
    stack = {k: 0 for k in ADECK.ranks}
    for card in decks:
        stack[card[0].split()[0]] += 1
    return stack


def createdecks(ndecks, shuffles, shuffle=True):
    """
    generates a `ndecks` number of FrenchDecks, with `shuffles` number
    of shuffles if `shuffle`
    """
    decks = []

    for i in range(ndecks):
        deck = FrenchDeck()
        decks.extend(deck._cards)

    # if we want to shuffle
    if shuffle:
        for i in range(shuffles):
            random.shuffle(decks)
            # to allow random number generator some time
            time.sleep(0.137 ** 2 + 0.137)

    return decks


def cardsdown(stack, *cards):
    """
    removes any cards from the stack if found
    """
    for card in cards:
        card = card.upper().strip()
        stack[card] -= 1


def assign_values(decks):
    """
    returns an array that assigns values for the decks given
    """
    fmts = [_ for _ in map(format_card, decks)]
    ccts = [_ for _ in map(card_value, decks)]
    values = [_ for _ in zip(fmts, ccts)]

    return values


def check_zero_sum(values):
    """
    makes sure the sum of the values for the decks are 0
    """
    return sum(map(lambda v: v[1], values))


def truecount(stack, ndecks):
    """
    returns the true count spread for the stack
    """
    negs = sum(1 * stack[v] for v in stack if v in "2 3 4 5 6".split())
    poss = sum(-1 * stack[v] for v in stack if v in "10 J Q K A".split())
    zers = sum(0 * stack[v] for v in stack if v in "7 8 9".split())

    total = sum([negs, poss, zers]) / ndecks

    return total


if __name__ == "__main__":
    emu = False
    ndecks = 4
    shuffles = 4

    decks = createdecks(ndecks, shuffles, shuffle=True)  # create decks
    values = assign_values(decks)  # create value assignments
    stack = create_stack(values)  # creates the stack
    z = check_zero_sum(values)  # gets the zero sum
    assert z == 0  # zero sum must be 0
    pprint(stack)  # pring the stack

    run = 0.0
    idx = 0
    # inc = input("Q to exit, else any key:")
    # if inc == 'Q':
    # 	exit(0)
    # run += values[idx][1]
    # stack[values[idx][0].split()[0]] -= 1
    # print(f"{values[idx][0]:20s}: {values[idx][1]:3.0f} count for running of {run}")
    # idx += 1

    """
	live card counting
	"""

    if not emu:
        choice = [c.upper().strip() for c in input("enter value: ").split()]
        while choice != "quit":
            for v in choice:
                stack[v] -= 1
                print(v, stack[v])
            # TODO: must fix the ndecks
            print(f"{truecount(stack, ndecks):3.3f}")
            pprint(stack)
            # print total number of cards left
            print(sum(v for k, v in stack.items()))
            choice = [c.upper().strip() for c in input("enter values: ").split()]

    """
	emulated card counting
	"""

    if emu:
        inc = input("Q to exit, else any key:")
        while inc != "Q" and idx < len(values):
            if not idx % DECKN:
                ndecks -= 1
            run += values[idx][1]
            stack[values[idx][0].split()[0]] -= 1
            print(
                f"{values[idx][0]:20s}: {-values[idx][1]:3.0f} count for running of {-run:4.1f} and a true run of {-run / (ndecks + 1):4.2f} and NDECKS = {ndecks}"
            )
            idx += 1
            inc = input("Q to exit, else any key:")
            pprint(stack)
