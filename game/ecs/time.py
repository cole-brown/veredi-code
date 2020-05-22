# coding: utf-8

'''
Timing info for game.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Callable

from datetime import datetime, timezone
import time as py_time
import decimal

from veredi.logger import log
from .const import SystemHealth
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

        self._num_ticks = 0

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

        Adds -1, 0, or 1 to `self._num_ticks`, depending on what self._tick_amt
        is.

        Returns self.seconds after this time step.
        '''
        self._seconds += self._tick_amt
        self._num_ticks += mathing.sign(self._tick_amt)
        return self._seconds

    @property
    def tick_num(self) -> int:
        return self._num_ticks

    @tick_num.setter
    def tick_num(self, value: int) -> None:
        self._num_ticks = value


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


class MonotonicTimer:
    '''
    Uses time.monotonic() to track elapsed time.
    '''
    def __init__(self):
        self.reset()

    def reset(self):
        self._start: float = self._current
        self._end:   float = None

    @property
    def _current(self):
        return py_time.monotonic()

    def start(self):
        '''Saves current monotonic time as the start time.'''
        self._start = self._current

    def stop(self):
        '''Saves current monotonic time as the end time.'''
        self._end = self._current

    @property
    def timing(self):
        '''Not stopped and have a start time means probably timing something.'''
        return (self._start and not self._end)

    @property
    def elapsed(self):
        '''
        If timer has been stopped, returns elapsed from start to end.

        Otherwise, returns elapsed from start to now.
        '''
        if self._end:
            return self._end - self._start
        return self._current - self._start


class TimeManager:
    '''
    This class has the potential to be saved to data fields. Let it control its
    timezones. Convert to user-friendly elsewhere.

    NOTE: IMITATES / DUCK-TYPES EcsManagerWithEvents, almost. Doesn't include
    the 'TimeManager' in whatever functions have it, as... well. I am Time.
    '''
    _DEFAULT_TICK_STEP = decimal.Decimal(6)
    _DEFAULT_TIMEOUT_SEC = 10

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

    def subscribe(self, event_manager: 'EventManager') -> SystemHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        return SystemHealth.HEALTY

    def apoptosis(self) -> SystemHealth:
        '''
        Game is ending gracefully. Do graceful end-of-the-world stuff...
        '''
        # Anything to do, time-wise?

        return SystemHealth.APOPTOSIS

    # ---
    # Timer
    # ---

    def start_timeout(self) -> None:
        if not self._timer:
            self._timer = MonotonicTimer()

        self._timer.start()

    def end_timeout(self) -> None:
        if not self._timer:
            return

        self._timer.end()
        elapsed = self._timer.elapsed
        self._timer.reset()
        return elapsed

    def is_timed_out(self, timeout=None) -> None:
        '''
        Returns true if timeout timer is:
          - Falsy.
          - Not timing.
          - Past timeout value.
            - or past _DEFAULT_TIMEOUT_SEC if timeout value is None.
        '''
        if not self._timer or not self._timer.timing:
            return True

        if not timeout or timeout <= 0:
            timeout = self._DEFAULT_TIMEOUT_SEC
        return self._timer.elapsed < timeout

    # ---
    # Ticking Time
    # ---

    def step(self) -> decimal.Decimal:
        return self.tick.step()

    # ---
    # Getters & Setters
    # ---

    @property
    def tick_seconds(self) -> decimal.Decimal:
        return self.tick.seconds

    @tick_seconds.setter
    def tick_seconds(self, value: TickTypes) -> None:
        self.tick.seconds = value

    @property
    def tick_num(self) -> int:
        return self.tick.tick_num

    @tick_num.setter
    def tick_num(self, value: int) -> None:
        self.tick.tick_num = value

    @property
    def datetime(self) -> datetime:
        return self.clock.datetime

    @datetime.setter
    def datetime(self, value: datetime) -> None:
        self.clock.datetime = value
