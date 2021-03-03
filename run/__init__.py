# coding: utf-8

'''
Helpers for getting a game of Veredi running.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from veredi.game.engine import Engine
    from veredi.data.config.config import Configuration

# Functions
from .options  import configuration
from .engine   import managers, engine
from .registry import registries

# Namespaced
from .         import system

from .server   import server


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def init(config: 'Configuration') -> None:
    '''
    Do some importing and set-up.
    '''
    registries(config)


def start(engine: 'Engine') -> None:
    '''
    Starts engine, runs until game is completed or stopped.
    '''
    return engine.run()


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # ------------------------------
    # File-Local
    # ------------------------------
    'init',
    'start',

    # ------------------------------
    # Functions
    # ------------------------------
    'configuration',
    'managers',
    'engine',
    'registries',

    # ------------------------------
    # Functions
    # ------------------------------
    'system',

    # ------------------------------
    # Overall Setup?
    # ------------------------------
    'server',
]
