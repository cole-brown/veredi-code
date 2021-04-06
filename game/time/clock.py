# coding: utf-8

'''
In game, "real-time" clock. For if you want to keep a campaign calendar or
something.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Callable

from datetime import datetime, timezone


from veredi.base.strings.mixin import NamesMixin


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO: conversion strings as config data?


# -----------------------------------------------------------------------------
# Clock for In Game DateTime
# -----------------------------------------------------------------------------

class Clock(NamesMixin,
            name_dotted='veredi.game.time.clock',
            name_string='clock'):
    '''
    Keeps a time stamp & time zone. I.e. wall clock/calendar time.
    This is not a real, actual clock. It gets ticked manually and
    ignores IRL time.
    '''

    def __init__(self,
                 date_time: datetime = None,
                 time_zone: timezone = None,
                 convert_fn: Callable[[datetime], float] = None) -> None:
        convert_fn = convert_fn or self._to_game
        self.time_zone = time_zone or timezone.utc
        date_time = date_time or datetime.now(self.time_zone)
        self.time_stamp = convert_fn(date_time)

    def _to_game(self, date_time):
        game_time = date_time.replace(hour=0,
                                      minute=0,
                                      second=0,
                                      microsecond=0)
        return game_time.timestamp()

    def tick(self, step: float) -> float:
        self.time_stamp += step
        return self.time_stamp

    @property
    def datetime(self):
        return datetime.fromtimestamp(self.time_stamp, self.time_zone)

    @datetime.setter
    def datetime(self, value: datetime):
        self.time_stamp = value.timestamp(self.time_zone)
