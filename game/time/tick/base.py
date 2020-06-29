# coding: utf-8

'''
Base class for game tick time.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union

import decimal
from decimal import Decimal

from veredi.math import mathing


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# We will convert any of these into Decimal
TickTypes = Union[Decimal, int, float, str]


# -----------------------------------------------------------------------------
# Game Time
# -----------------------------------------------------------------------------

class TickBase:
    '''
    Keep a game tick clock.
    '''

    _PRECISION = 6
    '''
    Precision for our Decimals.
    See Python docs for `decimal.getcontext().prec`.
    '''

    def __init__(self,
                 tick_amount: TickTypes,
                 curr_secs: Optional[TickTypes] = None) -> None:
        '''
        New TickBase class that advances time `tick_amount` each tick and
        starts off time at `curr_secs`.
        '''
        curr_secs = curr_secs or 0
        self._seconds = Decimal(curr_secs)
        self._tick_amt = Decimal(tick_amount)

        self._num_ticks = 0

        # ---
        # Decimal Context Set-Up (Not VeredicContexts)
        # ---

        # ExtendedContext is more forgiving.
        decimal.setcontext(decimal.ExtendedContext)
        # Tune it to millisecond precision
        decimal.getcontext().prec = self._PRECISION
        self._context_extended = decimal.getcontext()

        # BasicContext is better for debugging...
        # has more signal traps enabled.
        decimal.setcontext(decimal.BasicContext)
        # Tune it to millisecond precision
        decimal.getcontext().prec = self._PRECISION
        self._context_basic = decimal.getcontext()

        # And leave that context set, as we want that one usually.

    @property
    def seconds(self) -> Decimal:
        return self._seconds

    @seconds.setter
    def seconds(self, value: TickTypes) -> None:
        decimal.setcontext(self._context_extended)
        self._seconds = Decimal(value)
        decimal.setcontext(self._context_basic)

    @property
    def tick_amt(self) -> Decimal:
        return self._tick_amt

    @tick_amt.setter
    def tick_amt(self, value: TickTypes) -> None:
        decimal.setcontext(self._context_extended)
        self._tick_amt = Decimal(value)
        decimal.setcontext(self._context_basic)

    def step(self) -> Decimal:
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
