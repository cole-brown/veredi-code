# coding: utf-8

'''
Timing info for game.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Tuple

from datetime import datetime

from decimal import Decimal

from veredi.logger import log
from veredi.base.const import VerediHealth
from . import exceptions

from .event import EcsManagerWithEvents

from ..time.clock import Clock
from veredi.time.machine import MachineTime
from veredi.time.timer import MonotonicTimer
from ..time.tick.round import TickRounds, TickTypes


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO [2020-06-29]: Move time classes to time module.


# --------------------------------TimeManager----------------------------------
# --                               Dr. Time?                                 --
# ------------------------------"Just the Time."-------------------------------

class TimeManager(EcsManagerWithEvents):
    '''
    This class has the potential to be saved to data fields. Let it control its
    timezones. Convert to user-friendly elsewhere.
    '''
    _DEFAULT_TICK_STEP = Decimal(6)
    _DEFAULT_TIMEOUT_SEC = 10
    _SHORT_TIMEOUT_SEC = 1

    _METER_TIMEOUT_SEC = _DEFAULT_TICK_STEP * 4

    def __init__(self, tick_amount: Optional[TickTypes] = None) -> None:
        super().__init__()

        # TODO: Get our clocks, ticks, etc from config data?

        # defaults to midnight (00:00:00.0000) of current utc date
        self.clock = Clock()

        # defaults to zero start time, _DEFAULT_TICK_STEP tick step
        # zero is not an allowed tick amount so...
        tick_amount = tick_amount or self._DEFAULT_TICK_STEP
        if tick_amount <= 0:
            log.error("tick_amount should be `None` or a "
                      "non-zero, positive amount.")
            raise exceptions.SystemErrorV("tick_amount should be `None` or a "
                                          "non-zero, positive amount.",
                                          None, None)
        self.tick  = TickRounds(tick_amount)

        self.machine = MachineTime()
        self._timer = None

    def apoptosis(self) -> VerediHealth:
        '''
        Game is ending gracefully. Do graceful end-of-the-world stuff...
        '''
        # Anything to do, time-wise?

        return VerediHealth.APOPTOSIS

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

    @property
    def timing(self):
        '''
        Not stopped and have a start time means probably timing something.
        '''
        return self._timer.timing

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

        timed_out = self._timer.timed_out(timeout)
        return timed_out

    # ---
    # Ticking Time
    # ---

    def step(self) -> Decimal:
        return self.tick.step()

    # ---
    # Getters & Setters - Game Time
    # ---

    @property
    def seconds(self) -> Decimal:
        return self.tick.seconds

    @seconds.setter
    def seconds(self, value: TickTypes) -> None:
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

    # ---
    # Getters - System Time
    # ---

    # Use self.machine.jeff()

    # ---
    # Logging Despamifier Help
    # ---

    def metered(self, meter: Optional[Decimal]) -> Tuple[bool, Decimal]:
        '''
        Takes in a `metered` value from last call.
        Returns a tuple of:
          - bool:  True if meter is up and you can do a thing.
                   False if you should keep not doing a thing.
          - value: Meter value from last time we said you could do a thing.
                   You don't have to care about this; just keep passing and
                   updating it like:
                     do_the_thing, idk = self._time_manager.metered(idk)
                     if do_the_thing:
                         self.the_thing()
        '''
        if not meter:
            return True, self.seconds

        now = self.seconds
        if now > meter + self._METER_TIMEOUT_SEC:
            return True, now
        return False, meter
