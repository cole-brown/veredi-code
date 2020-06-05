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
class VerediHealth(enum.IntEnum):
    '''
    Return value for game engine tick functions, game system tick functions,
    some ECS manager functions, and other not-exactly-game systems.
    '''

    # --------------------------------------------------------------------------
    # Manually setting values so that VerediHealth.worst() is easier.
    # --------------------------------------------------------------------------

    # Leave invalid at zero since that's default int.
    INVALID   = 0
    '''A state to indicate a state hasn't been set but should/should have.'''

    # Apoptosis is the good kind of dying, but it still means we're killing
    # this thing.
    APOPTOSIS = -10
    '''System is dying in a healthy manner.'''

    # Unhealthy is bad.
    UNHEALTHY = -20
    '''Mr. Stark, I don't feel so good...'''

    # Fatal is the bad kind of dying.
    FATAL     = -30
    '''System is encountering bad things and should be killed.'''

    # Pending is more certain than INVALID, but still some quantum state.
    PENDING   = 10
    '''System is uncertain... Probably waiting on something (e.g. subscribe() so
    it can know if vital-to-it EventManager exists).'''

    _GOOD_HEALTH_THRESHOLD = 19
    '''External Folks should not use this - this is just for
    VerediHealth bookkeeping.'''

    # The Good One.
    HEALTHY   = 111
    '''Valid, healthly system.'''

    @property
    def should_die(self):
        '''
        Is this a state that should trigger system death?
        '''
        return (self == VerediHealth.FATAL
                or self == VerediHealth.APOPTOSIS)
        # TODO: Should INVALID be a trigger as well?
        # TODO: Should FATAL require a count of N > 1 FATALS?

    @property
    def good(self):
        '''
        Is this a state that is "'good'"?
        ...whatever that means.
        '''
        return self.value > VerediHealth._GOOD_HEALTH_THRESHOLD.value

    def worse(a: 'VerediHealth',
              b: 'VerediHealth') -> 'VerediHealth':
        '''
        Given `a` and `b`, returns the worse health of the two.
        '''
        # We've set up the enum values so that the worse off your health is, the
        # lower the number it's assigned.
        return (a if a.value < b.value else b)

    def set(a: 'VerediHealth',
            b: 'VerediHealth') -> 'VerediHealth':
        '''
        Given `a` and `b`, returns the worse health of the two. This will (try
        to) ignore INVALID. If both are invalid, though, it will be forced to
        still return INVALID.
        '''
        if a is VerediHealth.INVALID:
            return b
        if b is VerediHealth.INVALID:
            return a

        # We've set up the enum values so that the worse off your health is, the
        # lower the number it's assigned.
        return (a if a.value < b.value else b)



# -----------------------------------------------------------------------------
# Other?
# -----------------------------------------------------------------------------
