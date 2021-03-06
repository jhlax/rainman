#!/usr/bin/env python3

import random
import os
import time
import redis
import esper
from enum import Enum
from loguru import logger
from collections import namedtuple
import uuid


def generate_session_token(s):
    """
    generates a token for the redis session.

    :param s: redis session
    """

    u = str(uuid.uuid4())

    logger.info(f"session token:     {u}")

    s.set("sys:token", u)


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
    s.set("sys:status", "Status." + stat.name)
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

    return redis.StrictRedis(host=host, port=port, db=db, charset="utf-8", decode_responses=True)


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

    s_exists = bool(s.exists("status"))  # TODO: Potential redundancy

    if s_exists:
        # Returns a status indicator
        return s.get("status")

    else:
        result = change_status(s, Status.NONE)
        return result


def init_session(s, decks=None, splits=None, shuffles=None):
    """
    Initializes a session in the datavase.
    """

    decks = decks or _default_config["decks"]

    s.flushdb()
    s.set("status", "init")
    s.publish(CHANNEL, "Status.INIT")

    logger.info("initializing session.")

    generate_session_token(s)

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
        s.lpush("sys:ranks", rank)

    # suits
    logger.info("storing suit information.")
    s.publish(CHANNEL, "calc_suits")

    for suit in deck.suits:
        s.lpush("sys:suits", suit)

    # session config variables
    logger.info("setting configuration variables.")
    s.publish(CHANNEL, "set_config_vars")

    s.set("decks", _default_config["decks"])
    s.set("shuffles", _default_config["shuffles"])
    s.set("splits", _default_config["splits"])

    #
    #   Initialization of real-time counting algorithm data
    #

    # generate the shoe
    logger.info("generating shoe.")
    s.publish(CHANNEL, "generate_shoe")

    shoe = deck.cards * decks
    left = len(shoe)

    s.set("left", left)
    s.publish(CHANNEL, f"Command.DECKS {decks}")
    s.set("run", 0)

    for rank in deck.ranks:
        s.incrby("shoe:" + rank, decks * 4)

    for d in range(decks):
        for i in range(4):
            for rank in deck.ranks:
                s.lpush("sim:shoe", str(rank))

    s.set("funds", 0)
    s.set("buyin", 500)

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
        count = int(s.get("shoe:" + rank))
        s.publish(CHANNEL, f"Cn,{rank}:{count}")
        return count

    return "count not available"


def card_counts(s):
    # outputting total for each card
    logger.info("Number of cards for each rank:")

    for card in C_ALL:
        try:
            count = int(s.get("shoe:" + card))
            total = int(s.get("left"))
        except TypeError:
            count = 0
            total = 0

        try:
            print(f"{card:3s}: {count} ({100 * count / total:.2f}%)")
        except ZeroDivisionError:
            print(f"{card:3s}: {count} ({0}%)")


def shoe_length(s):
    try:
        length = int(s.get("left"))
        logger.info(f"{length} cards left.")
    except TypeError:
        logger.info("no cards left.")
        return 0
    s.publish(CHANNEL, f"{Command.CARDS} {length}")
    return length


def running_count(s):
    try:
        running = int(s.get("run"))
    except TypeError:
        running = 0
    logger.info(f"run of {running}")
    s.publish(CHANNEL, f"{Command.RUNNING} {running}")
    return running


def real_count(s):
    try:
        real = float(s.get("run") or 0) / (float(s.get("left")) / 52)
        logger.info(f"real of {real}")
        s.publish(CHANNEL, f"{Command.REAL} {real}")
        return real
    except (ZeroDivisionError, TypeError):
        logger.error(f"no cards left in the shoe.")
        return 0


def decks_left(s, exact=True):
    try:
        if exact:
            decks = round(float(s.get("left")) / 52)
        else:
            decks = float(s.get("left")) / 52
    except TypeError:
        return -1
    logger.info(f"{decks} decks left")
    s.publish(CHANNEL, f"{Command.DECKS} {decks}")
    return decks


#
#   Fund operations
#


def withdraw_funds(s, amount):
    amount = float(amount)
    amount *= 100
    amount = int(amount)

    s.decrby("::funds", amount)
    logger.info(f"withdrew ${amount / 100:.2f} from funds.")
    s.publish(CHANNEL, f"{Command.FUNDS} ADD {amount / 100:.2f}")


def add_funds(s, amount):
    amount = float(amount)
    amount *= 100
    amount = int(amount)

    s.incrby("funds", amount)
    logger.info(f"added ${amount / 100:.2f} to funds.")
    s.publish(CHANNEL, f"{Command.FUNDS} ADD {amount / 100:.2f}")


def get_funds(s):
    amount = float(s.get("funds")) / 100
    logger.info(f"${amount:.2f} funds left")
    return amount


def get_buyin(s):
    amount = float(s.get("buyin")) / 100
    logger.info(f"Buy in is ${amount:.2f}")
    return amount


def set_buyin(s, buyin):
    amount = int(buyin * 100)
    logger.info(f"setting buy in to ${buyin:.2f}")
    s.set("buyin", amount)
    return buyin


#
#   Removing, Replacing, and Other Operations
#


def clean_rank(func):
    def wrapper(*args, **kwargs):
        try:
            kwargs["rank"] = kwargs["rank"].upper().strip()
        except AttributeError:
            logger.error("No rank found.")
        return func(*args, **kwargs)

    return wrapper


@clean_rank
def remove_card(s, rank=None, n=1):
    """
    remove a deck from the deck.
    """

    if rank in C_ALL:
        shoe = s.decrby("shoe:" + rank, n)
        left = s.decrby("left", n)
        s.incrby("run", int(card_value(rank) * n))
        s.publish(CHANNEL, f"{Command.REMOVE} {rank}")
        logger.success(f"removed {rank} from the deck.")
        return rank

    else:
        logger.warning(f"card {rank} does not exist.")
        s.publish(CHANNEL, f"ERR:Could not remove {rank} from shoe.")


@clean_rank
def replace_card(s, rank=None, n=1):
    """
    put a card back into the deck.
    """

    if rank in C_ALL:
        shoe = s.incrby("shoe:" + rank, n)
        left = s.incrby("left", n)
        # s.incrby("::run", int(card_value(rank) * n))
        s.decrby("run", int(card_value(rank) * n))
        s.publish(CHANNEL, f"{Command.REPLACE} {rank}")
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


class Command(Enum):
    REMOVE = 0  # remove card(s)
    REPLACE = 1  # replace card(s)
    CARDS = 2  # total number of cards left
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
