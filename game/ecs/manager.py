# coding: utf-8

'''
Manager interface for ECS managers.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .event import EventManager

from veredi.base.const import VerediHealth
from .const            import SystemTick


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class EcsManager:
    '''
    Interface for ECS Managers.
    '''

    def _define_vars(self) -> None:
        self._health: VerediHealth = VerediHealth.HEALTHY
        '''Overall Health of Manager.'''

    def __init__(self) -> None:
        self._define_vars()

    def subscribe(self, event_manager: 'EventManager') -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        raise NotImplementedError

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

          - INVALID -> TICKS_START:
            - INVALID -> GENESIS
            - GENESIS -> INTRA_SYSTEM

          - TICKS_START -> TICKS_RUN

          - ??? -> TICKS_END:
            - ???        -> APOPTOSIS
            - APOPTOSIS  -> APOCALYPSE
            - APOCALYPSE -> THE_END

        NOTE: This is only called if there is a valid life-cycle/tick-cycle of
        interest.

        Updates self._health with result of life-cycle function. Returnns
        result of life-cycle function (not necessarily what self._health is).
        '''
        health = VerediHealth.HEALTHY

        # A New Beginning.
        if cycle_to == SystemTick.TICKS_START:
            if tick_to == SystemTick.GENESIS:
                health = health.update(self._cycle_genesis())
            elif tick_to == SystemTick.INTRA_SYSTEM:
                health = health.update(self._cycle_intrasystem())

        # A Duty To Fulfill.
        elif cycle_to == SystemTick.TICKS_RUN:
            health = health.update(self._cycle_game_loop())

        # A Hero's End.
        elif cycle_to == SystemTick.TICKS_END:
            if tick_to == SystemTick.APOPTOSIS:
                health = health.update(self._cycle_apoptosis())
            elif tick_to == SystemTick.APOCALYPSE:
                health = health.update(self._cycle_apocalypse())
            elif tick_to == SystemTick.THE_END:
                health = health.update(self._cycle_the_end())

        # Death Comes for All...
        elif (cycle_from == SystemTick.TICKS_END
              and cycle_to == SystemTick.FUNERAL
              and tick_from == SystemTick.THE_END
              and tick_to == SystemTick.FUNERAL):
            health = health.update(self._cycle_thanatos())

        self._health = self._health.update(health)
        return self._health

    def _cycle_genesis(self) -> VerediHealth:
        '''
        Entering TICKS_START life-cycle's first tick: genesis. System creation,
        initializing stuff, etc.
        '''
        return VerediHealth.HEALTHY

    def _cycle_intrasystem(self) -> VerediHealth:
        '''
        Entering TICKS_START life-cycle's next tick - intra-system
        communication, loading, configuration...
        '''
        return VerediHealth.HEALTHY

    def _cycle_game_loop(self) -> VerediHealth:
        '''
        Entering TICKS_RUN life-cycle, aka the main game loop.

        Prepare for the main event.
        '''
        return VerediHealth.HEALTHY

    def _cycle_apoptosis(self) -> VerediHealth:
        '''
        Entering TICKS_END life-cycle's first tick: apoptosis. Initial
        structured shut-down tick cycle. Systems, managers, etc must still be
        in working order for this - saving data, unloading, final
        communications, etc.
        '''
        # We have VerediHealth values APOPTOSIS, APOPTOSIS_SUCCESSFUL, and
        # APOPTOSIS_FAILURE. But I'm not sure the ECS Managers should use
        # those... They should still be healthy.
        return VerediHealth.HEALTHY

    def _cycle_apocalypse(self) -> VerediHealth:
        '''
        Entering TICKS_END life-cycle's next tick: apocalypse. Systems can now
        become unresponsive. Managers must stay responsive.
        '''
        # We have VerediHealth values APOCALYPSE and APOCALYPSE_DONE. But I'm
        # not sure the ECS Managers should use those... They should still be
        # healthy.
        return VerediHealth.HEALTHY

    def _cycle_the_end(self) -> VerediHealth:
        '''
        Entering TICKS_END life-cycle's final tick: the_end.

        Managers must finish the tick, so don't kill yourself here... Not quite
        yet.
        '''
        # We have VerediHealth values THE_END and FATAL, but I think save those
        # for the next cycle... We're not quite dead yet.
        return VerediHealth.HEALTHY

    def _cycle_thanatos(self) -> VerediHealth:
        '''
        The God Of Death is here.

        You may die now.
        '''
        # Ok. Die well or poorly. Either way you're dead now.
        return VerediHealth.THE_END
