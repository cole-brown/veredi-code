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

    INVALID     = 0

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
    # Masks
    # ---

    RESCHEDULE_SYSTEMS = GENESIS | TIME
    '''
    Reschedule during GENESIS as systems come on line. Check during TIME phase
    to see if anything changed to require a reschedule.
    '''

    ALL = TIME | CREATION | PRE | STANDARD | POST | DESTRUCTION
    '''
    ALL of the (standard) ticks.
    '''


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
