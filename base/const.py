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
# Health
# -----------------------------------------------------------------------------

@enum.unique
class VerediHealth(enum.IntEnum):
    '''
    Return value for game engine tick functions, game system tick functions,
    some ECS manager functions, and other not-exactly-game systems.
    '''

    # -------------------------------------------------------------------------
    # Manually setting values so that VerediHealth.worst() is easier.
    # -------------------------------------------------------------------------

    # ------------------------------
    # Limbo: == 0
    # ------------------------------
    INVALID   = 0
    '''A state to indicate a state hasn't been set but should/should have.'''

    # ------------------------------
    # The Good Death: [-10, -20)
    # ------------------------------
    # Apoptosis is the good kind of dying, but it still means we're killing
    # this thing.
    APOPTOSIS = -10
    '''In Progress: System is dying in a healthy manner.'''

    APOPTOSIS_SUCCESSFUL = -11
    '''Done: Successfully died in a healthy manner.'''

    APOPTOSIS_FAILURE = -12
    '''
    Done: Failed to die in a healthy manner, but probably can't do much about
    it...
    '''

    APOCALYPSE = -15
    '''System's/Engine's Apocalypse is in progress.'''

    APOCALYPSE_DONE = -16
    '''System/Engine is done with the apocalypse.'''

    THE_END = -18
    '''System/Engine is done with everything and is the good kind of dead.'''

    _RUN_OK_HEALTH_MIN = -19
    '''
    Engine is in acceptable health for running if above this value.
    NOTE! Probably don't use this - use 'in_runnable_health' property.
    '''

    # ------------------------------
    # Bad Things: (-∞, -20]
    # ------------------------------

    # Unhealthy is bad.
    UNHEALTHY = -20
    '''Mr. Stark, I don't feel so good...'''

    DYING = -30
    '''
    System is in the process of dying unhealthily, but don't kill it just yet?
    '''

    # Fatal is the bad kind of dying.
    FATAL  = -100
    '''System is encountering bad things and should be killed.'''

    # ------------------------------
    # Good, Running Things: [10, ∞)
    # ------------------------------

    # Pending is more certain than INVALID, but still some quantum state.
    PENDING = 10
    '''System is uncertain... Probably waiting on something (e.g. subscribe()
    so it can know if vital-to-it EventManager exists).'''

    _GOOD_HEALTH_MIN = 19
    '''
    Minimum health that is acceptable as 'good'.
    NOTE! Probably don't use this - use 'in_best_health' or 'limbo' property.
    '''

    # The Slightly Less Good One.
    HEALTHY_BUT_WARNING = 100
    '''Valid, healthly system.'''

    # The Good One.
    HEALTHY = 111
    '''Valid, healthly system.'''

    @property
    def should_die(self) -> bool:
        '''
        Is this a state that should trigger system death?
        '''
        return self < VerediHealth._RUN_OK_HEALTH_MIN
        # or self == VerediHealth.APOPTOSIS_SUCCESSFUL
        # or self == VerediHealth.APOPTOSIS_FAILURE)
        # TODO: Should INVALID be a trigger as well?
        # TODO: Should FATAL require a count of N > 1 FATALS?

    @property
    def limbo(self) -> bool:
        '''
        Is this a state that is "'good' for set-up"? But neither good nor bad?
        ...whatever that means.
        '''
        return (self.value >= VerediHealth.INVALID.value
                and self.value < VerediHealth._GOOD_HEALTH_MIN.value)

    @property
    def in_best_health(self) -> bool:
        '''
        Is this a health value that is at or above the minimum defined by
        VerediHealth._GOOD_HEALTH_MIN?

        This is generally for the TICKS_RUN (game loop) phase of living.
        '''
        return self.value > VerediHealth._GOOD_HEALTH_MIN.value

    @property
    def in_runnable_health(self) -> bool:
        '''
        Is this a health value that is at or above the minimum defined by
        VerediHealth._RUN_OK_HEALTH_MIN?

        This is generally for the TICKS_END (structured shutdown) phase of
        the engine.
        '''
        return self.value > VerediHealth._RUN_OK_HEALTH_MIN.value

    @staticmethod
    def worse(a: 'VerediHealth',
              b: 'VerediHealth') -> 'VerediHealth':
        '''
        Given `a` and `b`, returns the worse health of the two.
        '''
        # We've set up the enum values so that the worse off your health is,
        # the lower the number it's assigned.
        return (a if a.value < b.value else b)

    @staticmethod
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

        # We've set up the enum values so that the worse off your health is,
        # the lower the number it's assigned.
        return (a if a.value < b.value else b)

    def update(self, *health_update: 'VerediHealth') -> 'VerediHealth':
        '''
        Given `self` and `health`, returns the worse health of the two. This is
        a helpful shortcut to VerediHealth.set().
        '''
        # We have ourself, a health value, and any health args passed in. Set
        # ourself as the starting health, and then update that with each health
        # passed in and return the result (the worst of ourself and the
        # healths).
        health = self
        for value in health_update:
            health = VerediHealth.set(self, value)

        return VerediHealth.set(self, health)

    def __str__(self) -> str:
        '''
        Python 'to string' function.
        '''
        return self.__class__.__name__ + '.' + self.name

    def __repr__(self) -> str:
        '''
        Python 'to repr' function.
        '''
        return self.__class__.__name__ + '.' + self.name


# -----------------------------------------------------------------------------
# Other?
# -----------------------------------------------------------------------------


# TODO [2020-10-03]: unit test for health helpers

# TODO [2020-10-03]: Rename this to 'health.py'?
