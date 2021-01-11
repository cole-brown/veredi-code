# coding: utf-8

'''
Helpers for getting a game of Veredi running.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ------------------------------
# Sub-Modules
# ------------------------------

from . import base


# ------------------------------
# Types
# ------------------------------
from .component          import ComponentManager
from .entity             import EntityManager
from .event              import EventManager, Event
from .system             import SystemManager
from .time               import TimeManager

from .meeting            import Meeting


# ------------------------------
# Enums
# ------------------------------
from veredi.base.const   import VerediHealth

from veredi.game.ecs.const              import (SystemTick,
                                                SystemPriority,
                                                # and functions too...
                                                tick_health_init,
                                                tick_healthy)


# ------------------------------
# Functions
# ------------------------------


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # ------------------------------
    # Sub-Modules
    # ------------------------------
    'base'

    # ------------------------------
    # Enums
    # ------------------------------
    'VerediHealth',
    'SystemTick',
    'SystemPriority',

    # ------------------------------
    # Types
    # ------------------------------
    'ComponentManager',
    'EntityManager',
    'EventManager',
    'Event',
    'SystemManager',
    'TimeManager',

    'Meeting',

    # ------------------------------
    # Functions
    # ------------------------------
    'tick_health_init',
    'tick_healthy',
]
