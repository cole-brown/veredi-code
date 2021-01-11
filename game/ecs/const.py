# coding: utf-8

'''
Consts that are needed by some modules that don't want to/can't cross reference
each other.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import enum

from veredi.base.enum import FlagCheckMixin

from veredi.base.const import VerediHealth


# -----------------------------------------------------------------------------
# Ticking
# -----------------------------------------------------------------------------

@enum.unique
class SystemTick(FlagCheckMixin, enum.Flag):
    '''
    Enum for the defininiton of the steps in a full tick.

    These are (or should be) defined in the order they occur in Engine.

    has() and any() provided by FlagCheckMixin.
    '''

    # ------------------------------
    # Tick Meta-Values
    # ------------------------------

    INVALID     = 0
    '''Generic invalid/uninitialized value.'''

    ERROR       = enum.auto()
    '''Engine is in an invalid tick/life-cycle state.'''

    # ------------------------------
    # Actual Tick Values
    # ------------------------------

    # ---
    # Pre-Game-Loop Ticks
    # ---

    GENESIS      = enum.auto()
    '''Tick where systems load stuff they care about from data and get all set
    up and stuff.'''

    INTRA_SYSTEM = enum.auto()
    '''
    Tick where systems talk to each other about finishing set up. E.g. Command
    registration happens here.

    NOTE: Systems may not need to subscribe to this to take advantage - events
    may happen for them. E.g. Command registration happens as events and only
    InputSystem needs to run on this tick for registration to succeed.
    '''

    # ---
    # Game-Loop Ticks
    # ---

    TIME        = enum.auto()
    '''Tick where game time is updated.'''

    CREATION    = enum.auto()
    '''Tick where ECS creation happens.'''

    PRE         = enum.auto()
    '''Tick where ECS creation events are published, and any other
    pre-standard-tick stuff should happen.'''

    STANDARD    = enum.auto()
    '''Tick where basically everything should happen.

    USE THIS ONE!
    '''

    POST        = enum.auto()
    '''Tick where STANDARD events are published, and any other
    post-standard-tick stuff should happen.'''

    DESTRUCTION = enum.auto()
    '''Tick where ECS destruction happens.'''

    # ---
    # Post-Game Ticks
    # ---

    APOPTOSIS = enum.auto()
    '''
    Structured death of the game. Systems should save off data, tell their
    loved ones goodbye, and try to die in an orderly fashion.
    '''

    APOCALYPSE = enum.auto()
    '''
    "Terminate with extreme prejudice" death of the game. Systems should expect
    to just be murdered at any time if the aren't dead yet.
    '''

    THE_END = enum.auto()
    '''
    Goodbye.
    '''

    FUNERAL     = enum.auto()
    '''Engine has finished running; goodbye.'''

    # ------------------------------
    # Tick Collections & Masks
    # ------------------------------

    # ---
    # Ticks Collected into start/run/end.
    # ---

    # TICKS_BIRTH?
    TICKS_START = GENESIS | INTRA_SYSTEM
    '''All ticks considered part of start-up.'''

    # TICKS_LIFE?
    TICKS_RUN = TIME | CREATION | PRE | STANDARD | POST | DESTRUCTION
    '''All ticks considered part of the standard game loop.'''

    # TICKS_DEATH?
    TICKS_END = APOPTOSIS | APOCALYPSE | THE_END | FUNERAL
    '''The game will die now.'''

    # TODO: TICKS_AFTERLIFE
    AFTER_THE_END = FUNERAL | THE_END
    '''The game has finished running TICKS_END.'''

    # ---
    # Masks
    # ---

    RESCHEDULE_SYSTEMS = GENESIS | TIME
    '''
    Reschedule during GENESIS as systems come on line. Check during TIME phase
    to see if anything changed to require a reschedule.
    '''

    # Use: TICKS_RUN
    # ALL = TIME | CREATION | PRE | STANDARD | POST | DESTRUCTION
    # '''
    # ALL of the (standard) ticks.
    # '''


_GAME_LOOP_SEQUENCE = [
    (SystemTick.TIME,        SystemTick.CREATION),
    (SystemTick.CREATION,    SystemTick.PRE),
    (SystemTick.PRE,         SystemTick.STANDARD),
    (SystemTick.STANDARD,    SystemTick.POST),
    (SystemTick.POST,        SystemTick.DESTRUCTION),
    (SystemTick.DESTRUCTION, SystemTick.TIME),
]
'''The game-loop ticks in proper order, as (current, next) tuples.'''


def game_loop_next():
    '''
    Generator loops over the _GAME_LOOP_SEQUENCE ticks once.
    '''
    for tick in _GAME_LOOP_SEQUENCE:
        yield tick


def game_loop_start() -> bool:
    '''
    Returns the first element in the game loop sequence.
    '''
    return _GAME_LOOP_SEQUENCE[0][0]


def game_loop_end() -> bool:
    '''
    Returns the last element in the game loop sequence.
    '''
    return _GAME_LOOP_SEQUENCE[-1][0]


# -----------------------------------------------------------------------------
# Tick Ordering
# -----------------------------------------------------------------------------

class SystemPriority(enum.IntEnum):
    '''
    Low priority systems go last, so that a standard (non-reversed) sort will
    sort them in high-to-low priority.
    '''
    # ---
    # GENERAL
    # ---
    LOW    = 10000
    MEDIUM = 1000
    HIGH   = 100

    # ---
    # Specific Systems
    # ---
    DATA   = HIGH - 10

    # @staticmethod
    # def sort_key(key: 'SystemPriority') -> Union[SystemPriority, int]:
    #     '''
    #     This could be used, but we are using System.sort_key().
    #     '''
    #     return key


# -----------------------------------------------------------------------------
# Tick -> Health
# -----------------------------------------------------------------------------

def tick_health_init(tick:       'SystemTick',
                     invalid_ok: bool = False) -> VerediHealth:
    '''
    Returns a starting, good health for a tick type.

    If `invalid_ok` is True, SystemTick.INVALID will return
    VerediHealth.HEALTHY. Otherwise it will return the error/default health.

    Good Starting Healths are, for ticks in:
      - INVALID     - HEALTHY
      - TICKS_START - HEALTHY
      - TICKS_RUN   - HEALTHY
      - TICKS_END
        - APOPTOSIS  - APOPTOSIS (in progress)
        - APOCALYPSE - APOCALYPSE (in progress)
        - THE_END    - THE_END (good kind of dead)
    '''
    # ---
    # Start
    # ---
    if tick is SystemTick.INVALID:
        # HEALTHY will be downgraded by PENDING, etc.
        return VerediHealth.HEALTHY

    if tick in SystemTick.TICKS_START:
        # HEALTHY will be downgraded by PENDING, etc.
        return VerediHealth.HEALTHY

    # ---
    # RUN!
    # ---
    elif tick in SystemTick.TICKS_RUN:
        return VerediHealth.HEALTHY

    # ---
    # Done.
    # ---
    elif tick in SystemTick.TICKS_END:
        if tick is SystemTick.APOPTOSIS:
            # Success will be downgraded by in-progress or failure.
            return VerediHealth.APOPTOSIS_SUCCESSFUL

        if tick is SystemTick.APOCALYPSE:
            # Done will be downgraded by in-progress.
            return VerediHealth.APOCALYPSE_DONE

        if tick is SystemTick.THE_END:
            # This is the only THE_END-specific value right now...
            return VerediHealth.THE_END

        if tick is SystemTick.FUNERAL:
            return VerediHealth.THE_END

    # ---
    # Errors
    # ---
    # We don't know what to do for this tick, right now...
    return VerediHealth.FATAL


def tick_healthy(tick: 'SystemTick', health: VerediHealth) -> bool:
    '''
    Checks that `health` is a "good enough" value for the tick.

    Examples:
      - "PENDING" is good enough for GENESIS, but bad in the TICKS_RUN.
      - "HEALTHY" is good for TICKS_RUN, but /bad/ in TICKS_END.
        - Means some TICKS_RUN logic got mixed in, usually.
    '''
    # ---
    # Start
    # ---
    if tick in SystemTick.TICKS_START:
        # Limbo is also ok for START.
        return health.in_best_health or health.limbo

    # ---
    # RUN!
    # ---
    elif tick in SystemTick.TICKS_RUN:
        # Only best health is ok.
        return health.in_best_health

    # ---
    # Done.
    # ---
    elif tick in SystemTick.TICKS_END:
        # For the funeral, we expect specifically THE_END.
        if tick is SystemTick.FUNERAL:
            return health == VerediHealth.THE_END

        # Anything above 'real bad' is good.
        return health.in_runnable_health

    # ---
    # Errors or Funerals
    # ---
    # We don't know what to do for this tick, right now...
    return VerediHealth.FATAL
