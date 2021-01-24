# coding: utf-8

'''
Base class for game tick time.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, Optional
from veredi.base.null import NullNoneOr
if TYPE_CHECKING:
    from veredi.ecs.base     import System
    from veredi.base.context import VerediContext


from abc import ABC, abstractmethod

from decimal import Decimal


from veredi.base               import numbers


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

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''

        self._ticks: int = -1
        '''
        Just some counter for keeping track of delta ticks. This starts at zero
        at the beginning of each TICKS_START engine life-cycle and
        monotonically increases by one each time `delta()` is called.
        '''

    def __init__(self, context: Optional['VerediContext']) -> None:
        '''
        New TickBase. Will get its current_seconds from repository eventually
        once repo and config are both ready (i.e. when `TickBase.config()` is
        called).
        '''
        self._define_vars()

        self._configure(context)

    @abstractmethod
    def _configure(self, context: Optional['VerediContext']) -> None:
        '''
        Get current-seconds from repository, and whatever else sub-class needs
        from repo, config, etc.
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.configure() "
                                  "is not implemented in base class. "
                                  "Subclasses should implement it.")

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def count(self) -> int:
        '''
        Current tick number / count of the times we have been told
        to `delta()`.

        For keeping track of delta ticks. This starts at zero
        at the beginning of each TICKS_START engine life-cycle and
        monotonically increases by one each time `delta()` is called.
        '''
        return self._ticks

    @property
    @abstractmethod
    def current_seconds(self) -> Decimal:
        '''
        Get current seconds. Can be a generic definition of "current", for
        example if a round-and-turn-based ticker, this could be the round's
        current_seconds.
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.current_seconds "
                                  "getter property is not implemented in base "
                                  "class. Subclasses should get it defined "
                                  "via @register, or else define "
                                  "it themselves.")

    @current_seconds.setter
    @abstractmethod
    def current_seconds(self, value: numbers.DecimalTypes) -> None:
        '''
        Set current seconds. Can be a generic definition of "current", for
        example if a round-and-turn-based ticker, this could be the round's
        current_seconds.
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.current_seconds "
                                  "getter property is not implemented in base "
                                  "class. Subclasses should get it defined "
                                  "via @register, or else define "
                                  "it themselves.")

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

    def delta(self) -> Decimal:
        '''
        This is the function to tick every SystemTick.TIME. This "advances"
        time by one "delta" - a time amount that has no meaning here
        (subclasses must decide its meaning).

        NOTE: Subclasses can/should adjust this as needed. E.g. to add a fixed
        amount of time to self._current_seconds if on a fixed time tick.

        Get ready for this game run ticks cycle. Increment tick,
        current_seconds, or whatever by one delta amount.

        Returns self._ticks after this time step.
        '''
        self._ticks += 1
        self._delta()
        return self._ticks

    @abstractmethod
    def _delta(self) -> None:
        '''
        Called by `delta()` after `self._ticks` is updated.

        Subclasses should implement as needed, or just `pass`. E.g. to add a
        fixed amount of time to self._current_seconds if on a fixed time tick.
        '''
        raise NotImplementedError(f"{self.__class__.__name__}._delta() "
                                  "is not implemented in base class. "
                                  "Subclasses should define it themselves.")

    @property
    def error_tick_info(self) -> str:
        '''
        Returns tick, tick num, machine time.
        '''
        return (f"{self.__class__.__name__}: {self.seconds} tick seconds, "
                f"{self.tick_num} tick number, "
                f"{self.machine.stamp_to_str()}")
