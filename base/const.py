# coding: utf-8

'''
Consts that are needed by some modules that don't want to/can't cross reference
each other.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import enum


# ------------------------------------------------------------------------------
# Health
# ------------------------------------------------------------------------------

@enum.unique
class VerediHealth(enum.Enum):
    '''
    Return value for game engine tick functions, game system tick functions,
    some ECS manager functions, and other not-exactly-game systems.
    '''

    INVALID   = 0
    '''A state to indicate a state hasn't been set but should/should have.'''

    PENDING   = enum.auto()
    '''System is uncertain... Probably waiting on something (e.g. subscribe() so
    it can know if vital-to-it EventManager exists).'''

    HEALTHY   = enum.auto()
    '''Valid, healthly system.'''

    UNHEALTHY = enum.auto()
    '''Mr. Stark, I don't feel so good...'''

    FATAL     = enum.auto()
    '''System is encountering bad things and should be killed.'''

    APOPTOSIS = enum.auto()
    '''System is dying in a healthy manner.'''

    @property
    def should_die(self):
        '''
        Is this a state that should trigger system death?
        '''
        return (self == VerediHealth.FATAL
                or self == VerediHealth.APOPTOSIS)
        # TODO: Should INVALID be a trigger as well?
        # TODO: Should FATAL require a count of N > 1 FATALS?


# -----------------------------------------------------------------------------
# Other?
# -----------------------------------------------------------------------------
