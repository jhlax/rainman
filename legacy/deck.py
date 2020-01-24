import random

from collections import namedtuple

from loguru import logger

Card = namedtuple("Card", ["rank", "suit"])

vneg = "2 3 4 5 6".split()
vpos = "10 J Q K A".split()
vnet = "7 8 9".split()


def count_card(card):
    # logger.warning(f"{card}")
    if card.rank in vneg:
        return -1

    if card.rank in vpos:
        return +1

    if card.rank in vnet:
        return 0


class FrenchDeck:
    """
    the french deck class
    """

    ranks = [str(n) for n in range(2, 11)] + list("JQKA")
    suits = "spades diamonds clubs hearts".split()

    @classmethod
    def decks(cls, n=4):
        cards = FrenchDeck()._cards
        for i in range(n - 1):
            cards += FrenchDeck()._cards
        deck = FrenchDeck()
        deck._cards = cards

        return deck

    def __init__(self):
        self._cards = [Card(rank, suit) for suit in self.suits for rank in self.ranks]

    def __len__(self):
        return len(self._cards)

    def __getitem__(self, position):
        return self._cards[position]

    def __setitem__(self, x, y):
        self._cards[x] = y

    def __str__(self):
        # return f"{len(self)} card(s) with running count of {self.running} and a total count of {self.total}"
        return f"{self.total}"

    @property
    def running(self):
        return sum(count_card(z) for z in self)

    @property
    def total(self):
        return self.running / (len(self) / 52) if len(self) else 0

    def shuffle(self, n=1):
        logger.info(f"shuffling {len(self)} card(s) {n} times")
        for i in range(n):
            random.shuffle(self)

    def next(self, n=1):
        out = []
        for i in range(n):
            out += [self._cards.pop()]
        return out

    def choose(self):
        return random.choose(self)

    def nleft(self, card):
        return len([_ for _ in self._cards if _.rank == card.upper().strip()])

    def prank(self, card):
        nleft = self.nleft(card)
        return nleft / len(self._cards)

    def kill(self, card):
        for idx, i in enumerate(self._cards):
            if i.rank == card.upper().strip():
                self._cards.pop(idx)
                return
        logger.warning(f"no more of {card}")

    def cut(self, by=2):
        new = FrenchDeck()
        new._cards = self._cards[len(self._cards) // 2 :]
        return new

    def pull(self, card):
        try:
            idx = [
                i for i, z in enumerate(self._cards) if z.rank == card.upper().strip()
            ][0]
            return self._cards.pop(idx)
        except:
            logger.error(f"{card} not in deck")
            return Card(rank="None", suit="None")
            pass


if __name__ == "__main__":
    deck = FrenchDeck.decks(8)
    logger.info(f"deck, count_card(deck[0])")
    deck.shuffle(8)
    deck = deck.cut()
    # deck = deck.cut()

    emu = False

    if emu:
        while input("enter to hit, else quit: ") == "":
            card = deck.next()
            card = card[0]
            rcard = count_card(card)
            logger.info(f"CARD:  {card.rank}")
            logger.info(f"DELTA: {rcard}")
            logger.info(f"RUN:   {deck.running}")
            logger.info(f"NLEFT: {len(deck)}")
            logger.success(
                f"TOTAL: {round(deck.total, 1)} ({deck.total * 100 / 52:.1f}% advantage)"
            )
            # logger.info(f"{card}, {rcard}, {deck}")
            nlefts = {k: v for k, v in map(lambda r: (r, deck.nleft(r)), deck.ranks)}
            pranks = {
                k: round(v * 100, 2)
                for k, v in map(lambda r: (r, deck.prank(r)), deck.ranks)
            }
            logger.warning(nlefts)
            logger.warning(pranks)

    else:
        card_in = input("card entrance: ")

        while card_in != "Z":

            if card_in == "":
                card_in = input("card entrance: ").strip().upper()
                continue
            if card_in[0] == "-":
                deck._cards.append(Card(rank=card_in[1:], suit="None"))
                card_in = input("card entrance: ").strip().upper()
                continue

            card = deck.pull(card_in.strip().upper())
            rcard = count_card(card)
            logger.info(f"CARD:  {card.rank}")
            logger.info(f"DELTA: {rcard}")
            logger.info(f"RUN:   {deck.running}")
            logger.info(f"NLEFT: {len(deck)}")
            logger.success(
                f"TOTAL: {round(deck.total, 1)} ({deck.total * 100 / 52:.1f}% advantage)"
            )

            # logger.info(f"{card}, {rcard}, {deck}")

            nlefts = {k: v for k, v in map(lambda r: (r, deck.nleft(r)), deck.ranks)}
            pranks = {
                k: round(v * 100, 2)
                for k, v in map(lambda r: (r, deck.prank(r)), deck.ranks)
            }

            logger.warning(nlefts)
            logger.warning(pranks)

            card_in = input("card entrance: ").strip().upper()
