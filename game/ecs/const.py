# coding: utf-8

'''
Consts that are needed by some modules that don't want to/can't cross reference
each other.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import enum


# -----------------------------------------------------------------------------
# Debugging
# -----------------------------------------------------------------------------

@enum.unique
class DebugFlag(enum.Flag):
    LOG_TICK     = enum.auto()
    '''Output a log message each tick at debug level.'''

    RAISE_ERRORS = enum.auto()
    '''Re-raises any errors/exceptions caught in Engine object itself.'''

    UNIT_TESTS = LOG_TICK | RAISE_ERRORS

    def has(self, flag):
        return ((self & flag) == flag)


# -----------------------------------------------------------------------------
# Systems
# -----------------------------------------------------------------------------

@enum.unique
class SystemTick(enum.Flag):
    '''
    Enum for the defininiton of the steps in a full tick.

    These are (or should be) defined in the order they occur in Engine.
    '''

    # ---
    # Pre-Game-Loop Ticks
    # ---

    SET_UP      = enum.auto()
    '''Tick where systems load stuff they care about from data and get all set
    up and stuff.'''

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

    ALL = TIME | CREATION | PRE | STANDARD | POST | DESTRUCTION

    def has(self, flag):
        return ((self & flag) == flag)


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
    DATA_CODEC = HIGH - 6
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
