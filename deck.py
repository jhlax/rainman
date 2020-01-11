import random

from collections import namedtuple

from loguru import logger

Card = namedtuple("Card", ["rank", "suit"])

vneg = "2 3 4 5 6".split()
vpos = "10 J Q K A".split()
vnet = "7 8 9".split()


def count_card(card):
    if card in vneg:
        return 1

    if card in vpos:
        return -1

    if card in vnet:
        return 0


class FrenchDeck:
    """
    the french deck class
    """

    ranks = [str(n) for n in range(2, 11)] + list('JQKA')
    suits = 'spades diamonds clubs hearts'.split()

    def __init__(self):
        self._cards = [Card(rank, suit) for suit in self.suits
                       for rank in self.ranks]

    def __len__(self):
        return len(self._cards)

    def __getitem__(self, position):
        return self._cards[position]


def choose(deck):
    return random.choose(deck)


if __name__ == "__main__":
    deck = FrenchDeck()
    logger.info(f"deck, count_card(deck[0])")
    print(random.choice(deck))

