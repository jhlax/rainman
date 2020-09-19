"""
asrm.py - advanced systems rainman

the successor to the original rainman by John Harrington, utilizing the same core
code base, but with a more refined, complex, and modular architecture.

additional features include:

* better redis schema
* realistic emulation of a blackjack table
* strategy implementations and interfaces
* web front end
* money management
* enhanced statistics
"""
from enum import Enum

import redis
from loguru import logger


class SCHEMA:
    STATUS = "status"


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


class DatabaseIface:
    """
    the asrm database interface (redis)
    """

    CHANNEL = 'rainman'

    _redis_default_config = {
        # Redis configuration
        "host": "127.0.0.1",
        "port": "6379",
        "db": 0,
    }

    def __init__(self, config=None, clear=False):
        logger.info(f"creating redis database interface")
        if config is None:
            config = {}

        self._db = redis.StrictRedis(
            charset="utf-8",
            decode_responses=True,
            **config
        )

        if clear is True:
            logger.warning("clear is True, which will flush the database upon instantiation")
            self.clear_session(flushall=True)

        self.config = self._redis_default_config
        self.connect(self.config)

    @property
    def db(self):
        return self._db

    @db.setter
    def db(self, config):
        self._db = redis.StrictRedis(
            **config,
            charset="utf-8",
            decode_responses=True,
        )

    def connect(self, config=None):
        """
        connect to the database
        """

        if config is None:
            config = self.config

        self.db = config

        return self.db

    def clear_session(self, flushall=False):
        """
        Flushes the DB with option to flush all DBs.
        """

        logger.warning("clearing session.")
        self.db.publish(self.CHANNEL, "clear_session")

        if flushall:
            logger.warning("clearing all sessions.")
            self.db.flushall()

        else:
            self.db.flushdb()

        self.change_status(Status.NONE)

        logger.success("cleared session and flushed db.")

        return True

    def change_status(self, stat):
        """
        changes the status of the algorithm to 'stat'
        """

        logger.info("Status changed to " + stat.name)
        self.db.set(SCHEMA.STATUS, stat.name)  # FIXME
        self.db.publish(self.CHANNEL, "Status." + stat.name)

        return stat


iface = DatabaseIface(clear=True)
iface.connect()
