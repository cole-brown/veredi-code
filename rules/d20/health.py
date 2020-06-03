# coding: utf-8

'''
Health component - a component that has persistent data on it and deals with
health, hit points, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, Union, Iterable, Collection, MutableMapping, Container
import enum
# import re
# import decimal

from veredi.data.config.registry import register

from veredi.data.exceptions         import (DataNotPresentError,
                                            DataRestrictedError)
from veredi.game.ecs.base.component import ComponentError
from veredi.game.data.component     import DataComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

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


@register('veredi', 'rules', 'd20', 'health')
class HealthComponent(DataComponent):
    '''
    Component with persistent data for health, hit points, etc.
    '''

    # TEMP: a way to verify we got something, and to verify we're using the
    # verify() function...
    _REQ_KEYS = {
        'health': {
            'current': ['hit-points', 'permanent'],
            'maximum': ['hit-points'],
            'unconscious': ['hit-points'],
            'death': ['hit-points'],
            'resistance': [],
        },
    }

    def _verify(self) -> None:  # TODO: pass in `requirements`.
        '''
        Verifies our data against a template/requirements data set.
        '''
        # §-TODO-§ [2020-05-26]: verify against template/reqs.
        # For now, simpler verify...

        if not self._persistent:
            raise DataNotPresentError(
                "No data supplied.",
                None, None)

        for key in self._REQ_KEYS:
            self._verify_key(key, self._persistent, self._REQ_KEYS[key])

    def _verify_key(self,
                    key: str,
                    data: Collection[str],
                    sub_keys: Union[Collection[str], MutableMapping[str, str]]) -> None:
        # Get this one...
        self._verify_exists(key, data)

        # ...then go one deeper.
        sub_data = data[key]
        for each in sub_keys:
            if isinstance(sub_keys, list):
                self._verify_exists(each, sub_data)
            else:
                self._verify_key(each, sub_data, sub_keys.get(each, ()))

    def _verify_exists(self,
                       key: str,
                       container: Container[str]) -> None:
        if key not in container:
            raise DataNotPresentError(
                f"Key '{key}' not found in our data (in {container}).",
                None, None)
