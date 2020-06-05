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
