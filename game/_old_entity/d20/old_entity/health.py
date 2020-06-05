# coding: utf-8

'''
Health component.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, Union, Iterable
import enum
import re
import decimal

from veredi.data.exceptions import (DataNotPresentError,
                                    DataRestrictedError)
from ..component import (Component,
                         ComponentError)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


class AttrDict(dict):
    _SEPARATORS = r'[_ -]'
    _REPLACEMENT = '_'
    # Valid in game code are:
    #   0 through 9
    #   a through z
    #   A through Z
    #   underscore
    _VALID_REGEX = re.compile(r'^[a-zA-Z0-9_]$')

    def __init__(self, *args: Any, **kwargs: str) -> None:
        data = {}
        for key in kwargs:
            # Copy over to our dict, making keys usable as attributes.
            data[AttrDict.make_safe(key)] = kwargs[key]
        # Don't accidentally use this now.
        kwargs = None

        super().__init__(*args, **data)
        self.__dict__ = self

    @staticmethod
    def make_safe(value: str) -> str:
        return AttrDict._VALID_REGEX.sub(AttrDict._REPLACEMENT, key)


class DataClass(AttrDict):
    _RESTRICTED_KEYS = {
        DataClass.make_regex(r'raw', DataClass._SEPARATORS, r'data'),
    }

    @staticmethod
    def make_regex(*args: str) -> str:
        return re.compile(''.join(args))

    def has_regex(regex: re.Pattern, string: str) -> bool:
        return bool(regex.search(string))

    def __init__(self,
                 raw_data_key: str,
                 required_keys: Iterable[str],
                 **kwargs: str) -> None:
        if raw_data_key not in kwargs:
            raise DataNotPresentError(
                "Base key '{}' not present in data provided: {}",
                raw_data_key, kwargs)

        for r_key in _RESTRICTED_KEYS:
            for d_key_regex in **kwargs:
                if d_key_regex.search(r_key):
                    raise DataRestrictedError(
                        "Found restricted key '{}' present in data provided: {}",
                        d_key, kwargs)

        # Save our raw data, then init our AttrDict parent with it.
        self.raw_data = kwargs[raw_data_key]
        kwargs = None  # Don't accidentally use this now.

        # Make sure our required keys are in the raw data.
        # Do it on the unsafe'd keys (self.raw_data)?
        # Alternatively, could do it on the attribute-safe'd keys after
        # super-init call...
        for requirement in required_keys:
            if requirement not in self.raw_data:
                raise DataNotPresentError(
                    "Required key '{}' not present in data provided: {}",
                    requirement, self.raw_data)

        super().__init__(*args, **self.raw_data)


class DataContext:
    def __init__(self, keys: Iterable[str], value: str) -> None:
        self._keys = keys
        self._value = value

    @property
    def keys(self) -> Iterable[str]:
        return self._keys

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, value: Union[str, int, decimal.Decimal]) -> None:
        self._value = value


@enum.unique
class HealthState(enum.Flag):
    INVALID = enum.auto()
    ALIVE = enum.auto()
    HALF = enum.auto()
    UNCONSCIOUS = enum.auto()
    DEAD = enum.auto()

    def has(self, flag: 'HealthState') -> bool:
        return ((self & flag) == flag)

    def set(self, flag):
        return self | flag

    def unset(self, flag):
        return self & ~flag


class HitPoints(DataClass):
    _KEY_BASE = 'hit-points'

    _REQUIRED_KEYS = {
        'current',
        'maximum',
        'unconscious',
        'death',
    }

    def __init__(self, *args: str, **kwargs: str) -> None:
        super().__init__(self._KEY_BASE, self._REQUIRED_KEYS, **self.raw_data)

    def adjust(self, amount: Union[int, decimal.Decimal], *tags: str) -> decimal.Decimal:
        self.current += amount
        return self.current

    def reset(self, *tags: str) -> decimal.Decimal:
        self.current = self.maximum
        return self.current

    @property
    def state(self) -> HealthState:
        state = HealthState.INVALID

        # General States: ALIVE, DEAD, UNCONSCIOUS (mostly dead)
        if self.current > self.unconscious:
            state = state.set(HealthState.ALIVE)
        elif self.current < self.death:
            state = state.set(HealthState.DEAD)
        else:
            state = state.set(HealthState.UNCONSCIOUS)

        # Bonus States: Alive, but half health or less.
        if state.has(HealthState.ALIVE) and self.current < (self.maximum // 2):
            state = state.set(HealthState.HALF)

        if state != HealthState.INVALID:
            state = state.unset(HealthState.INVALID)

        return state


class Health(Component):
    '''
    Hit points, etc.
    '''

    def __init__(self, data) -> None:
        super().__init__()

        self._hp = HitPoints(data)
        # TODO: other stuff... DR?

    @property
    def health(self):
        return self._hp
