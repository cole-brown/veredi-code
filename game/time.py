# coding: utf-8

'''
Timing info for game.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Callable

from datetime import datetime, timezone
import decimal

from veredi.logger import log
from . import system
from . import exceptions

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# We will convert any of these into decimal.Decimal
TickTypes = Union[decimal.Decimal, int, float, str]


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Tick:
    '''
    Keep a game tick clock.
    '''

    def __init__(self,
                 tick_amount: TickTypes,
                 curr_secs: Optional[TickTypes] = None) -> None:
        # ---
        # Consts
        # ---
        self._PRECISION = 6

        # ---
        # Vars
        # ---
        curr_secs = curr_secs or 0
        self._seconds = decimal.Decimal(curr_secs)
        self._tick_amt = decimal.Decimal(tick_amount)

        # ---
        # Contexts
        # ---

        # ExtendedContext is more forgiving.
        decimal.setcontext(decimal.ExtendedContext)
        # Tune it to millisecond precision
        decimal.getcontext().prec = self._PRECISION
        self._context_extended = decimal.getcontext()

        # BasicContext is better for debugging... has more signal traps enabled.
        decimal.setcontext(decimal.BasicContext)
        # Tune it to millisecond precision
        decimal.getcontext().prec = self._PRECISION
        self._context_basic = decimal.getcontext()

        # And leave that context set, as we want that one usually.

    @property
    def seconds(self) -> decimal.Decimal:
        return self._seconds

    @seconds.setter
    def seconds(self, value: TickTypes) -> None:
        decimal.setcontext(self._context_extended)
        self._seconds = decimal.Decimal(value)
        decimal.setcontext(self._context_basic)

    @property
    def tick_amt(self) -> decimal.Decimal:
        return self._tick_amt

    @tick_amt.setter
    def tick_amt(self, value: TickTypes) -> None:
        decimal.setcontext(self._context_extended)
        self._tick_amt = decimal.Decimal(value)
        decimal.setcontext(self._context_basic)

    def step(self) -> decimal.Decimal:
        '''
        Add `self._tick_amt` seconds to the Tick counter.
        Positive, negative, whatever.
        Returns self.seconds after this time step.
        '''
        self._seconds += self._tick_amt
        return self._seconds


class Clock:
    '''
    Keeps a time stamp & time zone. I.e. wall clock/calendar time.
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

    def tick(step: float) -> float:
        self.time_stamp += step
        return self.time_stamp

    @property
    def datetime(self):
        return datetime.fromtimestamp(self.time_stamp, self.time_zone)

    @datetime.setter
    def datetime(self, value: datetime):
        self.time_stamp = value.timestamp(self.time_zone)


class TimeManager:
    '''
    This class has the potential to be saved to data fields. Let it control its
    timezones. Convert to user-friendly elsewhere.
    '''
    _DEFAULT_TICK_STEP = decimal.Decimal(6)

    def __init__(self, tick_amount: Optional[TickTypes] = None) -> None:
        super().__init__()
        # defaults to midnight (00:00:00.0000) of current utc date
        self.clock = Clock()

        # defaults to zero start time, _DEFAULT_TICK_STEP tick step
        # zero is not an allowed tick amount so...
        tick_amount = tick_amount or self._DEFAULT_TICK_STEP
        if tick_amount <= 0:
            log.error("tick_amount should be `None` or a "
                      "non-zero, positive amount.")
            raise exceptions.SystemError("tick_amount should be `None` or a "
                                         "non-zero, positive amount.",
                                         None, None)
        self.tick  = Tick(tick_amount)

    # ---
    # Ticking Time
    # ---

    def step(self) -> decimal.Decimal:
        return self.tick.step()

    # ---
    # Getters & Setters
    # ---

    def get_tick(self) -> decimal.Decimal:
        return self.tick.seconds

    def set_tick(self, value: TickTypes) -> None:
        self.tick.seconds = value

    def get_datetime(self) -> datetime:
        return self.clock.datetime

    def set_datetime(self, value: datetime) -> None:
        self.clock.datetime = value
