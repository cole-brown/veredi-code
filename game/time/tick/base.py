# coding: utf-8

'''
Base class for game tick time.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union
from veredi.base.null import Null, Nullable, NullNoneOr

from abc import ABC, abstractmethod

import decimal
from decimal import Decimal

from veredi.base import numbers
from veredi.data.config.config import Configuration


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Game Time
# -----------------------------------------------------------------------------

class TickBase(ABC):
    '''
    Keep a game tick clock. Base class is quite generic to allow subclasses
    like:
      - Round/Turn-based Ticking
      - Fixed-Time (Real-Time) Ticking
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    _PRECISION = 6
    '''
    Precision for our Decimals.
    See Python docs for `decimal.getcontext().prec`.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''

        self._current_seconds: Decimal = 0
        '''
        Current Game/Tick time in seconds.
        '''

        self._ticks: Decimal = 0
        '''
        Just some counter for keeping track of delta ticks. This starts at zero
        each game session.
        '''

    def __init__(self) -> None:
        '''
        New TickBase. Will get its current_seconds from repository eventually
        once repo and config are both ready (i.e. when `TickBase.config()` is
        called).
        '''
        self._define_vars()

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

    @abstractmethod
    def configure(self,
                  config: NullNoneOr[Configuration]) -> None:
        '''
        Get current-seconds from repository, and whatever else sub-class needs
        from repo, config, etc.
        '''
        raise NotImplementedError(f"{klass.__name__}.dotted() "
                                  "is not implemented in base class. "
                                  "Subclasses should implement it.")

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def current_seconds(self) -> Decimal:
        return self._seconds

    @current_seconds.setter
    def current_seconds(self, value: numbers.DecimalTypes) -> None:
        decimal.setcontext(self._context_extended)
        self._seconds = Decimal(value)
        decimal.setcontext(self._context_basic)

    # -------------------------------------------------------------------------
    # Identification
    # -------------------------------------------------------------------------

    @classmethod
    @abstractmethod
    def dotted(klass: 'System') -> str:
        """
        The dotted name this system has. If the system uses '@register', you
        still have to implement dotted, but you get klass._DOTTED for free
        (the @register decorator sets it).

        E.g.
          @register('veredi', 'jeff', 'system')
        would be:
          klass._DOTTED = 'veredi.jeff.system'

        So just implement like this:

            @classmethod
            def dotted(klass: 'JeffSystem') -> str:
                '''
                Returns our dotted name.
                '''
                # klass._DOTTED magically provided by @register
                return klass._DOTTED
        """
        raise NotImplementedError(f"{klass.__name__}.dotted() "
                                  "is not implemented in base class. "
                                  "Subclasses should get it defined via "
                                  "@register, or else define it themselves.")

    # -------------------------------------------------------------------------
    # Ticking
    # -------------------------------------------------------------------------
    #
    # `TickBase.delta()` is the function to tick every SystemTick.TIME. This
    # "advances" time by one "delta" - a time amount that has no meaning here
    # (subclasses must decide its meaning).

    @abstractmethod
    def delta(self) -> Decimal:
        '''
        This is the function to tick every SystemTick.TIME. This "advances"
        time by one "delta" - a time amount that has no meaning here
        (subclasses must decide its meaning).

        NOTE: Subclasses can/should adjust this as needed. E.g. to add a fixed
        amount of time to self._seconds if on a fixed time tick.

        Get ready for this game run ticks cycle. Increment tick,
        current_seconds, or whatever by one delta amount.

        Returns self._ticks after this time step.
        '''
        self._ticks += 1
        return self._ticks
