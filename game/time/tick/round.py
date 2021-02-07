# coding: utf-8

'''
Tick class for Round-&-Turn-Based games.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, Optional, Iterable, List
from veredi.base.null import Null, Nullable, NullNoneOr, null_or_none


from decimal import Decimal


from veredi.logger               import log

from veredi.base.context         import VerediContext, UnitTestContext
from veredi.base.strings         import label
from veredi.base                 import numbers

from veredi.data                 import background
from veredi.data.config.registry import register

from veredi                      import time

from veredi.math                 import mathing

from .base                       import TickBase
from ...ecs.base.identity        import EntityId


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Game Time
# -----------------------------------------------------------------------------

@register('veredi', 'game', 'time', 'tick', 'round')
class TickRounds(TickBase):
    '''
    Keep a game tick clock for Round/Turn-Based games, where entities are
    assigned a turn order in a round and cannot act (generally) until it is
    their turn.

    Time is ticked by "deltas" - meaningless time amounts that have no bearing
    on turn or round or in-game time. It just keeps ticking deltas so that
    events, chat, data updates, whatever can be processed while the entity
    whose turn it is figures out their action(s).
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        super()._define_vars()

        self._seconds_per_round: Decimal = None
        '''
        How long in seconds that a round takes.

        It is definition data.
        '''

        self._current_round: int = -1
        '''
        The number of the current round. Multiply by `self._seconds_per_round`
        to get `self._current_seconds`.

        It is saved data.
        '''

        self._turn_order: Nullable[List[EntityId]] = Null()
        '''
        The current round's turn order for entities.
        '''

        self._turn_index: int = 0
        '''
        Where in the current round's turn order we are.
        '''

    def _configure(self, context: Optional['VerediContext']) -> None:
        '''
        Get rounds-per-tick and current-seconds from repository.
        '''
        # ------------------------------
        # UNIT-TEST HACKS
        # ------------------------------
        if isinstance(context, UnitTestContext):
            # If constructed specifically with a UnitTestContext, don't do
            # _configure() as we have no DataManager.
            ctx = context.sub_get(self.dotted())
            self._seconds_per_round = time.to_decimal(ctx['seconds-per-round'])
            self._current_round = numbers.to_decimal(ctx['current-round'])
            return

        # ------------------------------
        # Grab our config from DataManager's Game Rules.
        # ------------------------------
        # Game Rules has both the game definition and the game saved records.
        rules = background.manager.data.game

        # ------------------------------
        # Definitions
        # ------------------------------
        # Round Time will be stored in game rules definition data.

        # Get round time duration.
        key_round_time = ('time', 'round')  # definition.game -> time.round
        round_time =  rules.definition.get(*key_round_time)
        if null_or_none(round_time):
            msg = ("Could not get Round Time from RulesGame's Definition "
                   f"data: {label.normalize(*key_round_time)} "
                   f"{round_time}")
            raise background.config.exception(None, msg)
        self._seconds_per_round = time.to_decimal(round_time)

        # ------------------------------
        # Saved Data
        # ------------------------------
        # Current Time will be stored in game rules saved data.

        # Get current round number.
        key_round_number = ('time', 'round')  # saved.game -> time.round
        round_num = rules.saved.get(*key_round_number)
        if null_or_none(round_num) or not numbers.is_number(round_num):
            msg = ("Could not get Current Round (or it is not a number) "
                   "from RulesGame's Saved data: "
                   f"{label.normalize(key_round_number)} "
                   f"{round_num}")
            raise background.config.exception(None, msg)
        self._current_round = numbers.to_decimal(round_num)

    def _init_bg_data(self) -> None:
        '''
        Initialize our background data dict with useful info about us.
        '''
        super()._init_bg_data()
        # Parent creates 'loaded' entry, so just add to it:
        loaded = self._bg_data.setdefault('loaded', {})
        loaded['seconds-per-round'] = self._seconds_per_round
        loaded['current-round']     = self._current_round
        return self._bg_data

    def _bg_data_current(self) -> None:
        '''
        Updated self._bg_data['current'] and return self._bg_data.
        '''
        # Replace whatever's there with new data.
        self._bg_data['current'] = {
            'snapshot':        time.machine.stamp_to_str(),
            'current-seconds': self.current_seconds,
            'exact-seconds':   self.exact_seconds,
            'turn-order':      self.turn_order,
            'turn':            self.turn,
        }
        return self._bg_data

    # -------------------------------------------------------------------------
    # Round Functions
    # -------------------------------------------------------------------------

    @property
    def current_seconds(self) -> Decimal:
        '''
        Get the /round's/ current seconds.

        For the turn's current seconds, use `exact_seconds()`.
        '''
        return self._current_round * self._seconds_per_round

    @current_seconds.setter
    def current_seconds(self, value: numbers.DecimalTypes) -> None:
        '''
        Set the /round's/ current seconds.

        This will also update `exact_seconds()` as it is based on
        current_seconds().
        '''
        # Determine our updated round number. Do not allow fractional rounds
        # (use floordiv (int div) not truediv (float/Decimal div).
        self._current_round = (
            numbers.to_decimal(value) // self._seconds_per_round)

    # -------------------------------------------------------------------------
    # Turn Functions
    # -------------------------------------------------------------------------

    @property
    def turn_order(self) -> NullNoneOr[Iterable[EntityId]]:
        '''
        Getter for the turn order list.
        '''
        return self._turn_order

    def set_turn_order(self,
                       turn_order:    NullNoneOr[Iterable[EntityId]],
                       preserve_turn: bool = True) -> None:
        '''
        Setter for the turn order list.

        If `preserve_turn` is True, this will try to keep the current turn on
        whatever entity it was on before the set.
          - This can fail and raise a ValueError if entity no longer exists in
            the list.

        If `preserve_turn` is False, this resets the turn order so that it is
        now the turn of the first entity in the new list.
        '''
        # First, if we're in a turn_order, and being set to a new one (as
        # opposed to it being deleted): check to see if we can/should
        # `preserve_turn`.
        new_index = 0
        if preserve_turn and self._turn_order and turn_order:
            curr_ent = self.turn
            if (curr_ent != EntityId.INVALID
                    and curr_ent in turn_order):
                # Save their spot in the new list.
                new_index = turn_order.index(curr_ent)

        self._turn_order = turn_order or Null()
        self._turn_index = new_index

    @property
    def turn(self) -> EntityId:
        '''
        Returns EntityId of entity whose turn it is now.
        '''
        if not self._turn_order:
            return EntityId.INVALID

        return self._turn_order[self._turn_index]

    @property
    def exact_seconds(self) -> Decimal:
        '''
        Given current round's time (`TickRounds.current_seconds`), round length
        (`TickRounds._seconds_per_round`), and current entity's place in the
        turn order, return the exact time it is in this part of the round.

        E.g.: If it is currently (round) time T=30s (with 6 second rounds) and
        the turn of the 2nd of 5 entities, then this will return (exact) time
        of 1/5th into the round that started at 30s.
          - 1/5th because 1st entity is done and second is acting, but not
            done.
            T=30+((2-1)/5*6)=31.2s
          - Or for the last entity:
            T=30+((5-1)/5*6)=34.8s
          - Next round starts at T=36s in this example.

        Returns `current_seconds` if there is currently no turn order.
        '''
        curr_time = self.current_seconds
        if not self._turn_order:
            return curr_time

        # Index being zero based helps us out here. We want what the exact time
        # is, at the start of this entity's turn. So that the 5th of 5 entities
        # has an 'exact_seconds' in _this_ round instead of at the start of
        # _next_ round.
        num_actors = len(self._turn_order)
        curr_actor = self._turn_index

        return curr_time + (curr_actor / num_actors * self._seconds_per_round)

    # -------------------------------------------------------------------------
    # Identification
    # -------------------------------------------------------------------------

    @classmethod
    def dotted(klass: 'TickRounds') -> str:
        '''
        Returns our dotted name.
        '''
        # klass._DOTTED magically provided by @register
        return klass._DOTTED

    # -------------------------------------------------------------------------
    # Getting Through A Round
    # -------------------------------------------------------------------------
    #
    # `tick.delta()` is the function to tick every SystemTick.TIME. This
    # "advances" time by one "delta" - a meaningless time amount for the
    # round/turn based game. It allows events, chat, data updates, whatever to
    # be processed while the entity whose turn it is figures out their
    # action(s).

    def _delta(self) -> None:
        '''
        Called by `delta()` after `self._ticks` is updated.
        '''
        # Don't need to do anything, currently.
        pass

    def acted(self, entity_id) -> Decimal:
        '''
        Step to next entity's turn. Maybe it's the same round; maybe not.

        Returns current seconds.
        '''
        # Can't do anything?
        if not self._turn_order:
            log.warning("No turn order - cannot update turns/rounds "
                        "based on action.")
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

        Returns current seconds.
        '''
        self._seconds += self._tick_amt
        self._num_ticks += mathing.sign(self._tick_amt)
        return self._seconds
