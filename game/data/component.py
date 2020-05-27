# coding: utf-8

'''
Data component - a component that has persistent data on it.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, Union, Iterable
# import enum
# import re
# import decimal

from veredi.data.exceptions import (DataNotPresentError,
                                    DataRestrictedError)
from ..ecs.base import (Component,
                        ComponentError)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# @enum.unique
# class HealthState(enum.Flag):
#     INVALID = enum.auto()
#     ALIVE = enum.auto()
#     HALF = enum.auto()
#     UNCONSCIOUS = enum.auto()
#     DEAD = enum.auto()
#
#     def has(self, flag: 'HealthState') -> bool:
#         return ((self & flag) == flag)
#
#     def set(self, flag):
#         return self | flag
#
#     def unset(self, flag):
#         return self & ~flag


# class HitPoints(DataClass):
#     _KEY_BASE = 'hit-points'
#
#     _REQUIRED_KEYS = {
#         'current',
#         'maximum',
#         'unconscious',
#         'death',
#     }
#
#     def __init__(self, *args: str, **kwargs: str) -> None:
#         super().__init__(self._KEY_BASE, self._REQUIRED_KEYS, **self.raw_data)
#
#     def adjust(self, amount: Union[int, decimal.Decimal], *tags: str) -> decimal.Decimal:
#         self.current += amount
#         return self.current
#
#     def reset(self, *tags: str) -> decimal.Decimal:
#         self.current = self.maximum
#         return self.current
#
#     @property
#     def state(self) -> HealthState:
#         state = HealthState.INVALID
#
#         # General States: ALIVE, DEAD, UNCONSCIOUS (mostly dead)
#         if self.current > self.unconscious:
#             state = state.set(HealthState.ALIVE)
#         elif self.current < self.death:
#             state = state.set(HealthState.DEAD)
#         else:
#             state = state.set(HealthState.UNCONSCIOUS)
#
#         # Bonus States: Alive, but half health or less.
#         if state.has(HealthState.ALIVE) and self.current < (self.maximum // 2):
#             state = state.set(HealthState.HALF)
#
#         if state != HealthState.INVALID:
#             state = state.unset(HealthState.INVALID)
#
#         return state


class DataComponent(Component):
    '''
    Component with persistent data.
    '''

    def __init__(self,
                 cid: ComponentId,
                 data: Dict[str, Any],
                 *args: Any,
                 **kwargs: Any) -> None:
        '''DO NOT CALL THIS UNLESS YOUR NAME IS ComponentManager!'''
        # §-TODO-§ [2020-05-26]: stuff here.

        # All persistent data should go here, or be gathered up in return value
        # of persistent property.
        self._persistent: Dict[str, Any] = data or {}
        # Flag for indicating that this component wants its
        # persistent data saved.
        self._dirty:      bool           = False

        super().__init__(cid, *args, **kwargs)
        self._verify()
        self._from_data()

    @property
    def persistent(self):
        return self._persistent

    def _verify(self, requirements) -> None:  # TODO: type of `requirements`.
        '''
        Verifies our data against a template/requirements data set.

        Raises:
          - DataNotPresentError (VerediError)
          - DataRestrictedError (VerediError)
          - NotImplementedError - temporarily
        '''
        # §-TODO-§ [2020-05-26]: Use component-template, component-requirements
        # here to do the verification?
        raise NotImplementedError

    def _from_data(self):
        '''
        Do any data processing needed for readying this component for use based
        on new data.
        '''
        raise NotImplementedError

    def _to_data(self):
        '''
        Do any data processing needed for readying this component for
        serialization on new data.
        '''
        raise NotImplementedError
