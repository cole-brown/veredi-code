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


from veredi.base.strings import label
from veredi.logs         import log

# Functions
from .options            import configuration
from .engine             import managers, engine
from .registry           import registration

# Namespaced
from .                   import system

from .server             import server


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_DOTTED: str = 'veredi.run'


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def init(config: 'Configuration') -> None:
    '''
    Do some importing and set-up.
    '''
    log_dotted = label.normalize(_DOTTED, 'init')
    log.start_up(log_dotted,
                 "Initializing Veredi...")

    registration(config)

    log.start_up(log_dotted,
                 "Initialization done.")


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
    'registration',

    # ------------------------------
    # Functions
    # ------------------------------
    'system',

    # ------------------------------
    # Overall Setup?
    # ------------------------------
    'server',
]
