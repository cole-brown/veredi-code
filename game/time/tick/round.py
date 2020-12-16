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


from veredi.data.config.registry import register
from veredi.data.config.config   import Configuration
from veredi.data.context         import DataLoadContext

from veredi.math                 import mathing

from .base                       import TickBase, TickTypes
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
    assigned a turn order in a round and cannot act until it is their turn.

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
        '''

        self._turn_order: Nullable[List[EntityId]] = Null()
        '''
        The current round's turn order for entities.
        '''

        self._turn_index: int = 0
        '''
        Where in the current round's turn order we are.
        '''

    def configure(self,
                  config: NullNoneOr[Configuration]) -> None:
        '''
        Get rounds-per-tick and current-seconds from repository.
        '''
        # ---
        # Round Time
        # ---
        # Round Time will be stored in game systems/rules definition.

        # TODO: get this from game definition, not from config itself!
        key_round_time = ('engine', 'time', 'tick', 'round')
        round_time = config.get(*key_round_time)
        if not round_time or not isinstance(round_time, numbers.DecimalTypes):
            msg = ("Could not get Round Time from config data: "
                   f"config data: {label.join(key_round_time)} "
                   f"{round_time}")
            raise background.config.exception(context, msg)
        self._seconds_per_round = game_data.get('time', 'round')

        # ---
        # Current Seconds
        # ---
        # Current Time will be stored in game save.

        game_data = background.data.game
        if not game_data:
            msg = ("Could not get game's saved current time. "
                   "Game's saved data does not exist?")
            raise background.config.exception(context, msg,
                                              error_data={
                                                  'game_data': game_data,
                                              })
        self._current_seconds = game_data.get('time', 'round')

    # -------------------------------------------------------------------------
    # Getters / Setters
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
                    and curr_ent not in turn_order):
                # Save their spot in the new list.
                new_index = turn_order.index(curr_ent)

        self._turn_order = entities or Null()
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

        # Index being zero based helps us out here. We need zero based anyways
        # because we want what the exact time is at the start of this entity's
        # turn. So that the 5th of 5 entities has an 'exact_seconds' in this
        # round instead of at the start of next round.
        num_actors = len(self._turn_order)
        curr_actor = self._turn_index

        return curr_time + (curr_actor / num_actors * self.)

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

    def delta(self) -> Decimal:
        '''
        Increment delta tick by one, actual round time by none, and get ready
        for this tick.
        '''
        self._ticks += 1
        return self._ticks

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
