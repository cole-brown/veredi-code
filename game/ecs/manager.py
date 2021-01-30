# coding: utf-8

'''
Manager interface for ECS managers.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING
from veredi.base.null import NullNoneOr, Null
if TYPE_CHECKING:
    from .event import EventManager


from abc import ABC, abstractmethod


from veredi.base.const   import VerediHealth
from veredi.logger.mixin import LogMixin
from veredi.debug.const  import DebugFlag
from veredi.data         import background

from .const              import SystemTick, tick_healthy


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class EcsManager(LogMixin, ABC):
    '''
    Interface for ECS Managers.
    '''

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        self._health: VerediHealth = VerediHealth.HEALTHY
        '''Overall Health of Manager.'''

        self._debug: DebugFlag = None
        '''Debugging flags.'''

    def __init__(self,
                 debug_flags: NullNoneOr[DebugFlag]) -> None:

        self._define_vars()
        self._debug = debug_flags or Null()

        # ---
        # Logger!
        # ---
        # Set up ASAP so that we have self._log_*() working... ASAP? Yeah.
        self._log_config(self.dotted())

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @classmethod
    @abstractmethod
    def dotted(klass: 'EcsManager') -> str:
        '''
        The dotted name this Manager has. E.g. 'veredi.game.ecs.manager.entity'
        '''
        raise NotImplementedError(f"{klass.__name__}.dotted() "
                                  "is not implemented in base class. "
                                  "Subclasses should defined it themselves.")

    @abstractmethod
    def get_background(self):
        '''
        Data for the Veredi Background context.
        '''
        raise NotImplementedError(f"{self.__class__.__name__}."
                                  "get_background() "
                                  "is not implemented in base class. "
                                  "Subclasses should defined it themselves.")

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def health(self) -> VerediHealth:
        return self._health

    @health.setter
    def health(self, update_value: VerediHealth) -> None:
        '''
        Sets self._health to the worst of current value and `update_value`.
        '''
        self._health = self._health.update(update_value)

    def _healthy(self, tick: SystemTick) -> bool:
        '''
        Are we in a healthy/runnable state?

        For ticks at end of game (TICKS_DEATH), this is just any 'runnable'
        health.

        For the rest of the ticks (namely TICKS_LIFE), this is only the 'best'
        of health.
        '''
        return tick_healthy(tick, self._health)

    # -------------------------------------------------------------------------
    # Life-Cycle Transitions
    # -------------------------------------------------------------------------

    def life_cycle(self,
                   cycle_from: SystemTick,
                   cycle_to:   SystemTick,
                   tick_from:  SystemTick,
                   tick_to:    SystemTick) -> VerediHealth:
        '''
        Engine calls this for a valid life-cycle transition and for valid tick
        transitions of interest.

        Valid life-cycle transitions are best checked in engine's
        _run_trans_validate(), but here's a summary of both life-cycle and tick
        transitions:

          - INVALID -> TICKS_BIRTH:
            - INVALID   -> SYNTHESIS
            - SYNTHESIS -> MITOSIS

          - TICKS_BIRTH -> TICKS_LIFE

          - ??? -> TICKS_DEATH:
            - ???       -> AUTOPHAGY
            - AUTOPHAGY -> APOPTOSIS
            - APOPTOSIS -> NECROSIS

        NOTE: This is only called if there is a valid life-cycle/tick-cycle of
        interest.

        Updates self._health with result of life-cycle function. Returnns
        result of life-cycle function (not necessarily what self._health is).
        '''
        health = VerediHealth.HEALTHY

        # A New Beginning.
        if cycle_to == SystemTick.TICKS_BIRTH:
            if tick_to == SystemTick.SYNTHESIS:
                health = health.update(self._cycle_synthesis())
            elif tick_to == SystemTick.MITOSIS:
                health = health.update(self._cycle_mitosis())

        # A Duty To Fulfill.
        elif cycle_to == SystemTick.TICKS_LIFE:
            health = health.update(self._cycle_game_loop())

        # A Hero's End.
        elif cycle_to == SystemTick.TICKS_DEATH:
            if tick_to == SystemTick.AUTOPHAGY:
                health = health.update(self._cycle_autophagy())
            elif tick_to == SystemTick.APOPTOSIS:
                health = health.update(self._cycle_apoptosis())
            elif tick_to == SystemTick.NECROSIS:
                health = health.update(self._cycle_necrosis())

        # Death Comes for All...
        elif (cycle_from == SystemTick.TICKS_DEATH
              and cycle_to == SystemTick.FUNERAL
              and tick_from == SystemTick.NECROSIS
              and tick_to == SystemTick.FUNERAL):
            health = health.update(self._cycle_thanatos())

        self._health = self._health.update(health)
        return self._health

    def _cycle_synthesis(self) -> VerediHealth:
        '''
        Entering TICKS_BIRTH life-cycle's first tick: synthesis. System
        creation, initializing stuff, etc.
        '''
        return VerediHealth.HEALTHY

    def _cycle_mitosis(self) -> VerediHealth:
        '''
        Entering TICKS_BIRTH life-cycle's next tick - mitosis
        communication, loading, configuration...
        '''
        return VerediHealth.HEALTHY

    def _cycle_game_loop(self) -> VerediHealth:
        '''
        Entering TICKS_LIFE life-cycle, aka the main game loop.

        Prepare for the main event.
        '''
        return VerediHealth.HEALTHY

    def _cycle_autophagy(self) -> VerediHealth:
        '''
        Entering TICKS_DEATH life-cycle's first tick: autophagy. Initial
        structured shut-down tick cycle. Systems, managers, etc must still be
        in working order for this - saving data, unloading, final
        communications, etc.
        '''
        # We have VerediHealth values AUTOPHAGY, AUTOPHAGY_SUCCESSFUL, and
        # AUTOPHAGY_FAILURE. But I'm not sure the ECS Managers should use
        # those... They should still be healthy.
        return VerediHealth.HEALTHY

    def _cycle_apoptosis(self) -> VerediHealth:
        '''
        Entering TICKS_DEATH life-cycle's next tick: apoptosis. Systems can now
        become unresponsive. Managers must stay responsive.
        '''
        # We have VerediHealth values APOPTOSIS and APOPTOSIS_DONE. But I'm
        # not sure the ECS Managers should use those... They should still be
        # healthy.
        return VerediHealth.HEALTHY

    def _cycle_necrosis(self) -> VerediHealth:
        '''
        Entering TICKS_DEATH life-cycle's final tick: necrosis.

        Managers must finish the tick, so don't kill yourself here... Not quite
        yet.
        '''
        # We have VerediHealth values NECROSIS and FATAL, but I think save those
        # for the next cycle... We're not quite dead yet.
        return VerediHealth.HEALTHY

    def _cycle_thanatos(self) -> VerediHealth:
        '''
        The God Of Death is here.

        You may die now.
        '''
        # Ok. Die well or poorly. Either way you're dead now.
        return VerediHealth.NECROSIS
