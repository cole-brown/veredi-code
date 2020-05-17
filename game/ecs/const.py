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
# Systems
# -----------------------------------------------------------------------------

@enum.unique
class SystemTick(enum.Flag):
    '''
    Enum for the defininiton of the steps in a full tick.

    These are (or should be) defined in the order they occur in Engine.
    '''

    TIME     = enum.auto()
    '''Tick where game time is updated.'''

    LIFE     = enum.auto()
    '''Tick where ECS creation happens.'''

    PRE      = enum.auto()
    '''Tick where ECS creation events are published, and any other
    pre-standard-tick stuff should happen.'''

    STANDARD = enum.auto()
    '''Tick where basically everything should happen.

    USE THIS ONE!
    '''

    POST     = enum.auto()
    '''Tick where STANDARD events are published, and any other
    post-standard-tick stuff should happen.'''

    DEATH    = enum.auto()
    '''Tick where ECS destruction happens.'''

    def has(self, flag):
        return ((self & flag) == flag)


class SystemPriority(enum.IntEnum):
    '''
    Low priority systems go last, so that a standard (non-reversed) sort will
    sort them in high-to-low priority.
    '''
    LOW    = 10000
    MEDIUM = 1000
    HIGH   = 100

    # @staticmethod
    # def sort_key(key: 'SystemPriority') -> Union[SystemPriority, int]:
    #     '''
    #     This could be used, but we are using System.sort_key().
    #     '''
    #     return key



@enum.unique
class SystemHealth(enum.Enum):
    '''
    Return value for system tick functions, and some ECS manager functions.
    '''

    INVALID   = 0
    '''A state to indicate a state hasn't been set but should/should have.'''

    HEALTHY   = enum.auto()
    '''Valid, healthly system.'''

    UNHEALTHY = enum.auto()
    '''Mr. Stark, I don't feel so good...'''

    FATAL     = enum.auto()
    '''System is encountering bad things and should be killed.'''

    APOPTOSIS = enum.auto()
    '''System just wants to die.'''

    def should_die(self):
        '''
        Is this a state that should trigger system death?
        '''
        return (self == SystemHealth.FATAL
                or self == SystemHealth.APOPTOSIS)
        # TODO: Should INVALID be a trigger as well?
        # TODO: Should FATAL require a count of N > 1 FATALS?



# -----------------------------------------------------------------------------
# Other?
# -----------------------------------------------------------------------------
