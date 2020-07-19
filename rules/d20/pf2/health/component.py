# coding: utf-8

'''
Health component - a component that has persistent data on it and deals with
health, hit points, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import enum

from veredi.base.enum            import FlagCheckMixin, FlagSetMixin

from veredi.data.config.registry import register
from veredi.game.data.component  import DataComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@enum.unique
class HealthState(FlagCheckMixin, FlagSetMixin, enum.Flag):
    '''
    has() and any() provided by FlagCheckMixin.
    set() and unset() provided by FlagSetMixin.
    '''

    INVALID = enum.auto()
    ALIVE = enum.auto()
    HALF = enum.auto()
    UNCONSCIOUS = enum.auto()
    DEAD = enum.auto()


@register('veredi', 'rules', 'd20', 'pf2', 'health', 'component')
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
