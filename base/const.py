# coding: utf-8

'''
Consts that are needed by some modules that don't want to/can't cross reference
each other.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, NewType

import enum
import pathlib


from .numbers import NumberTypes, NumberTypesTuple


# -----------------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------------

SimpleTypes = NewType('SimpleTypes', Union[str, NumberTypes])
SimpleTypesTuple = (str, *NumberTypesTuple)


# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------

# We are in veredi/base/const.py, so this file's grandparent is the veredi root
# directory.
LIB_VEREDI_ROOT = pathlib.Path(__file__).parent.parent
'''The current root directory of the Veredi library.'''

VEREDI_NAME_CODE = 'veredi'
'''A constant to use for our name.'''

VEREDI_NAME_DISPLAY = 'Veredi'
'''Our properly cased name.'''


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
    # Special/Neutral: [0, 10)*
    # ------------------------------
    # *NOTE:
    #   - limbo() is [0, 20)
    #   - But [10, 20] are in the 'Good' range and used for things like
    #     PENDING.
    #   - So Special/Neutral is [0, 10) or [0, 20), depending.

    INVALID   = 0
    '''A state to indicate a state hasn't been set but should/should have.'''

    IGNORE    = 1
    '''
    A state to indicate that this health value should just be ignored.

    E.g.: A manager that gets called for all tick types but doesn't care about
    one can return VerediHealth.IGNORE to indicate it should be ignored.
    '''

    # ------------------------------
    # The Good Death: [-10, -20)
    # ------------------------------
    # Must have the "good/done" values above the "ok/in-progress" for
    # `update()` et al to function correctly.

    # Autophagy is the good kind of dying, but it still means we're killing
    # this thing.
    AUTOPHAGY_SUCCESSFUL = -10
    '''Done: Successfully died in a healthy manner.'''

    AUTOPHAGY = -11
    '''In Progress: System is dying in a healthy manner.'''

    AUTOPHAGY_FAILURE = -12
    '''
    Done: Failed to die in a healthy manner, but probably can't do much about
    it...
    '''

    APOPTOSIS_DONE = -16
    '''System/Engine is done with the apoptosis.'''

    APOPTOSIS = -15
    '''System's/Engine's Apoptosis is in progress.'''

    NECROSIS = -18
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

    # -------------------------------------------------------------------------
    # Helper Functions
    # -------------------------------------------------------------------------

    @property
    def should_die(self) -> bool:
        '''
        Is this a state that should trigger system death?
        '''
        return self < VerediHealth._RUN_OK_HEALTH_MIN
        # or self == VerediHealth.AUTOPHAGY_SUCCESSFUL
        # or self == VerediHealth.AUTOPHAGY_FAILURE)
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

        This is generally for the TICKS_LIFE (game loop) phase of living.
        '''
        return (self.value > VerediHealth._GOOD_HEALTH_MIN.value
                or self is VerediHealth.IGNORE)

    @property
    def in_runnable_health(self) -> bool:
        '''
        Is this a health value that is at or above the minimum defined by
        VerediHealth._RUN_OK_HEALTH_MIN?

        This is generally for the TICKS_DEATH (structured shutdown) phase of
        the engine.
        '''
        return (self.value > VerediHealth._RUN_OK_HEALTH_MIN.value
                or self is VerediHealth.IGNORE)

    # -------------------------------------------------------------------------
    # Set Value Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def worse(a: 'VerediHealth',
              b: 'VerediHealth') -> 'VerediHealth':
        '''
        Given `a` and `b`, returns the worse health of the two.

        Ignores IGNORE if possible.
        '''
        # (Try to) ignore the IGNORE value (but if both are IGNORE... *shrug*).
        if a is VerediHealth.IGNORE:
            return b
        if b is VerediHealth.IGNORE:
            return a

        # We've set up the enum values so that the worse off your health is,
        # the lower the number it's assigned.
        return (a if a.value < b.value else b)

    @staticmethod
    def set(a: 'VerediHealth',
            b: 'VerediHealth') -> 'VerediHealth':
        '''
        Given `a` and `b`, returns the worse health of the two. This will (try
        to) ignore INVALID/IGNORE. If both are invalid/ignore, though, it will
        be forced to still return INVALID/IGNORE. Attempts to prefer INVALID
        over IGNORE.

        Ignores IGNORE if possible.
        '''
        # ---
        # Try for (optimal) invalidity check.
        # ---
        # Split invalid/ignore checks so we can try to prefer returning INVALID
        # over IGNORE.

        # One INVALID but no IGNORE?
        if a is VerediHealth.INVALID and b is not VerediHealth.IGNORE:
            return b
        if b is VerediHealth.INVALID and a is not VerediHealth.IGNORE:
            return a

        # One IGNORE but no INVALID?
        if a is VerediHealth.IGNORE and b is not VerediHealth.INVALID:
            return b
        if b is VerediHealth.IGNORE and a is not VerediHealth.INVALID:
            return a

        # INVALID/IGNORE fallback is same as the normal case. Prefer INVALID
        # over IGNORE (and we've set up the values of those two the correct way
        # for this check).

        # ---
        # Normal check.
        # ---
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

        return health

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

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
