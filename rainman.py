import random
import redis
import esper
from enum import Enum
from loguru import logger
from collections import namedtuple


#
#   Constants
#
NEG = "10 J Q K A".split()
NUL = "7 8 9".split()
POS = "2 3 4 5 6".split()
C_ALL = POS + NUL + NEG

CHANNEL = "rainman"


#
#   Default Configuration
#
_default_config = {
    # Redis configuration
    "red_host": "127.0.0.1",
    "red_port": "6379",
    "red_db": 0,
    # Base information for algorithm
    "decks": 6,
    "splits": 1,
    "shuffles": 8,
}


#
#   Indicators
#
class Status(Enum):
    """
    Status code for the system
    """

    NONE = 0
    INIT = 1
    ACTIVE = 2
    PAUSED = 3
    RESTART = 4
    CLOSING = 5
    BETTING = 6
    WAITING = 7


class Rank(Enum):
    TWO = 0
    THREE = 1
    FOUR = 2
    FIVE = 3
    SIX = 4
    SEVEN = 5
    EIGHT = 6
    NINE = 7
    TEN = 8
    JACK = 9
    QUEEN = 10
    KING = 11
    ACE = 12


def change_status(s, stat):
    logger.info("Status changed to " + stat.name)
    s.set(":status", "Status." + stat.name)
    s.publish(CHANNEL, "Status." + stat.name)
    return stat


#
#   Redis Session Functions
#
def get_redis_session(host=None, port=None, db=None):
    """
    Connects and returns a Redis session for use by the algorithm.
    """

    host = host or _default_config["red_host"]
    port = port or _default_config["red_port"]
    db = db or _default_config["red_db"]

    return redis.Redis(host=host, port=port, db=db)


def clear_session(s, flushall=False):
    """
    Flushes the DB with option to flush all DBs.
    """

    logger.warning("clearing session.")
    s.publish(CHANNEL, "clear_session")

    if flushall:
        logger.warning("clearing all sessions.")
        s.flushall()

    else:
        s.flushdb()

    change_status(s, Status.NONE)

    logger.success("cleared session and flushed db.")

    return True


def session_status(s, reinit=True):
    """
    Checks to see if there is a current session in the DB, and potentially
    reinitializes the database.
    """

    logger.info("checking session status.")

    s_exists = bool(s.exists(":status"))  # TODO: Potential redundancy

    if s_exists:
        # Returns a status indicator
        result = change_status(s, Status.ACTIVE)
        return result

    else:
        result = change_status(s, Status.NONE)
        return result


def init_session(s, decks=None, splits=None, shuffles=None):
    """
    Initializes a session in the datavase.
    """

    decks = decks or _default_config["decks"]

    s.flushdb()
    s.set(":status", "init")
    s.publish(CHANNEL, "Status.INIT")

    logger.info("initializing session.")

    """
    1. create constants (reference deck, positives and negatives, etc.)
    2. set session configuration variables
    3. generate shoe
    4. create weights for splits and shuffles
    5. initialize count
    """

    # reference deck
    deck = FrenchDeck()

    # positives and negatives
    logger.info("creating valuation data points for each card.")
    s.publish(CHANNEL, "calc_valuations")

    for card in deck.cards:
        key = "card:value:" + card.rank
        s.set(key, card.value)

    # ranks
    logger.info("storing rank information.")
    s.publish(CHANNEL, "calc_ranks")

    for rank in deck.ranks:
        s.lpush(":ranks", rank)

    # suits
    logger.info("storing suit information.")
    s.publish(CHANNEL, "calc_suits")

    for suit in deck.suits:
        s.lpush(":suits", suit)

    # session config variables
    logger.info("setting configuration variables.")
    s.publish(CHANNEL, "set_config_vars")

    s.set(":decks", _default_config["decks"])
    s.set(":shuffles", _default_config["shuffles"])
    s.set(":splits", _default_config["splits"])

    #
    #   Initialization of real-time counting algorithm data
    #

    # generate the shoe
    logger.info("generating shoe.")
    s.publish(CHANNEL, "generate_shoe")

    shoe = deck.cards * decks
    left = len(shoe)

    s.set("::left", left)
    s.publish(CHANNEL, f"DECK:{decks},{left}")

    for rank in deck.ranks:
        s.incrby("shoe:" + rank + ":", decks * 4)

    # outputting total for each card
    # logger.info("number of cards for each rank:")

    # for card in deck.ranks:
    #     count = int(s.get("shoe:" + card + ":"))
    #     print(f"  {card:3s}: {count}")
    card_counts(s)

    change_status(s, Status.ACTIVE)
    # s.set(":status", Status.ACTIVE.value)
    # s.publish(CHANNEL, Status.ACTIVE.value)


#
#   Cards, Decks, and Counts
#


def card_value(rank=None):
    rank = rank.strip().upper()

    if rank in NEG:
        return -1.0

    elif rank in NUL:
        return 0.0

    elif rank in POS:
        return 1.0

    else:
        logger.warning(f"{rank} has no value.")
        return 0.0


def card_count(s, rank=None):
    if rank in C_ALL:
        count = int(s.get("shoe:" + rank + ":"))
        s.publish(CHANNEL, f"Cn,{rank}:{count}")
        return count

    return "count not available"


def card_counts(s):
    # outputting total for each card
    logger.info("Number of cards for each rank:")

    for card in C_ALL:
        count = int(s.get("shoe:" + card + ":"))
        total = int(s.get("::left"))

        print(f"{card:3s}: {count} ({100 * count / total:.2f}%)")


def shoe_length(s):
    length = int(s.get("::left"))
    logger.info(f"{length} cards left.")
    s.publish(CHANNEL, f"Cn:{length}")
    return length


def run(s):
    running = int(s.get("::run"))
    logger.info(f"run of {running}")
    s.publish(CHANNEL, f"RUN:{running}")
    return running


#
#   Removing, Replacing, and Other Operations
#


def clean_rank(func):
    def wrapper(*args, **kwargs):
        kwargs["rank"] = kwargs["rank"].upper().strip()
        return func(*args, **kwargs)

    return wrapper


@clean_rank
def remove_card(s, rank=None, n=1):
    """
    remove a deck from the deck.
    """

    if rank in C_ALL:
        shoe = s.decrby("shoe:" + rank + ":", n)
        left = s.decrby("::left", n)
        s.incrby("::run", int(card_value(rank) * n))
        s.publish(CHANNEL, f"RCn{n},{rank}:{shoe},{left}")
        logger.success(f"removed {rank} from the deck.")

    else:
        logger.warning(f"card {rank} does not exist.")
        s.publish(CHANNEL, f"ERR:Could not remove {rank} from shoe.")


@clean_rank
def replace_card(s, rank=None, n=1):
    """
    put a card back into the deck.
    """

    if rank in C_ALL:
        shoe = s.incrby("shoe:" + rank + ":", n)
        left = s.incrby("::left", n)
        s.incrby("::run", int(card_value(rank) * n))
        s.publish(CHANNEL, f"ACn{n},{rank}:{shoe},{left}")
        logger.success(f"replaced {rank} into the deck.")

    else:
        logger.warning(f"card {rank} does not exist.")
        s.publish(CHANNEL, f"ERR:Could not replace {rank} into shoe.")


#
#   Classes and important contexts
#

Card = namedtuple("Card", "rank suit value")


class FrenchDeck:
    """
    Simple, functioning french deck
    """

    ranks = [str(r) for r in range(2, 11)] + list("JQKA")
    suits = "hearts diamonds clubs spades".split()

    def __init__(self):
        self.cards = [
            Card(rank, suit, card_value(rank))
            for suit in self.suits
            for rank in self.ranks
        ]


#
#   Main function when ran
#


"""
Click command-line interface for use
"""


import click


@click.group()
@click.option("--db", "-D", type=int, default=0)
@click.option("--log", "-L", is_flag=True, default=True)
@click.pass_context
def rainman(ctx, db, log):
    r = get_redis_session(db=db)

    if not log:
        logger.disable("__main__")
        logger.disable("rainman")

    ctx.ensure_object(dict)

    ctx.obj["SESSION"] = r
    ctx.obj["DB"] = db


class Command(Enum):
    REMOVE = 0  # remove card(s)
    REPLACE = 1  # replace card(s)
    TOTAL = 2  # total number of cards left
    RUNNING = 3  # running count
    REAL = 4  # real count
    DECKS = 5  # number of decks
    FUNDS = 7  # get or set funds
    STATS = 8  # get statistics on for the system
    INIT = 9  # reinitialize the deck
    BET = 10  # make a bet
    WIN = 11  # signify a win
    LOSS = 12  # loss
    REPL = 13  # read, eval, prompt, loop


@rainman.command()
@click.argument("cards", nargs=-1, type=str)
@click.pass_context
def rm(ctx, cards):
    for card in cards:
        remove_card(ctx.obj["SESSION"], rank=card)


@rainman.command()
@click.argument("cards", nargs=-1, type=str)
@click.pass_context
def put(ctx, cards):
    for card in cards:
        replace_card(ctx.obj["SESSION"], rank=card)


@rainman.command()
@click.argument("decks", type=int, default=6)
@click.pass_context
def init(ctx, decks):
    init_session(ctx.obj["SESSION"], decks)


@rainman.command()
@click.pass_context
def counts(ctx):
    card_counts(ctx.obj["SESSION"])


if __name__ == "__main__":
    # logger.info("connecting to redis session.")
    # session = get_redis_session()

    # Check database state status
    # session_status(session)
    # init_session(session)

    # Testing code
    # replace_card(session, "3")
    # remove_card(session, "7")
    # shoe_length(session)
    # remove_card(session, "J")
    # remove_card(session, "3")
    # remove_card(session, "3")
    # card_counts(session)
    # remove_card(session, "J")
    # replace_card(session, "J")
    # remove_card(session, "J")
    # remove_card(session, "6")
    # remove_card(session, "3")
    # remove_card(session, "J")
    # remove_card(session, "10")
    # shoe_length(session)
    # run(session)
    # shoe_length(session)
    # card_counts(session)
    try:
        rainman()
    finally:
        # clear_session(session)
        pass
