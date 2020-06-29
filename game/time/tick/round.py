# coding: utf-8

'''
Tick class for Round-&-Turn-Based games.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Iterable, List
from veredi.base.null import Null, Nullable, NullNoneOr

from decimal import Decimal

from veredi.math import mathing

from .base import TickBase, TickTypes
from ...ecs.base.identity import EntityId


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Game Time
# -----------------------------------------------------------------------------

# TODO [2020-06-29]: Round/Turn based Tick
#   - make time module
#   - move this file there
#   - move Tick class to time/tick.py
#   - subclass tick for RoundTurnTick? TurnTick?

class TickRounds(TickBase):
    '''
    Keep a game tick clock.
    '''

    def __init__(self,
                 round_secs: TickTypes,
                 curr_secs:  Optional[TickTypes] = None) -> None:
        '''
        New TickRounds class that advances time `round_secs` per round and
        starts off time at `curr_secs`.
        '''
        curr_secs = curr_secs or 0
        super().__init__(round_secs, curr_secs)

        self._turn_order: Nullable[List[EntityId]] = Null()
        self._turn_index: int = 0

    # ------------------------------
    # Getters / Setters
    # ------------------------------

    def set_turn_order(self,
                       entities: NullNoneOr[Iterable[EntityId]]) -> None:
        '''
        Set the turn order for tick rounds to use.
        '''
        self._turn_order = entities or Null()
        self._turn_index: int = 0

    @property
    def turn(self) -> EntityId:
        '''
        Returns EntityId of entity whose turn it is now.
        '''
        if not self._turn_order:
            return EntityId.INVALID

        return self._turn_order[self._turn_index]

    # ------------------------------
    # Stepping Through a Round
    # ------------------------------

    def step(self) -> Decimal:
        '''
        Step to next entity's turn. Maybe it's the same round; maybe not.
        '''
        # Can't do anything?
        if not self._turn_order:
            return self._seconds

        next_turn = (self._turn_index + 1) % len(self._turn_order)
        if next_turn == 0:
            self._step_round()

        self._turn_index = next_turn
        return self._seconds

    def _step_round(self) -> Decimal:
        '''
        Increment the tick by the tick amount in order to advance to the next
        round.
        '''
        self._seconds += self._tick_amt
        self._num_ticks += mathing.sign(self._tick_amt)
        return self._seconds
