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


# -----------------------------------------------------------------------------
# Systems
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

    TICKS_START = GENESIS | INTRA_SYSTEM
    '''All ticks considered part of start-up.'''

    TICKS_RUN = TIME | CREATION | PRE | STANDARD | POST | DESTRUCTION
    '''All ticks considered part of the standard game loop.'''

    TICKS_END = APOPTOSIS | APOCALYPSE | THE_END | FUNERAL
    '''The game will die now.'''

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
    DATA_SERDES = HIGH - 6
    DATA_REPO  = HIGH - 8
    DATA_REQ   = HIGH - 10

    # @staticmethod
    # def sort_key(key: 'SystemPriority') -> Union[SystemPriority, int]:
    #     '''
    #     This could be used, but we are using System.sort_key().
    #     '''
    #     return key


# -----------------------------------------------------------------------------
# Other?
# -----------------------------------------------------------------------------
