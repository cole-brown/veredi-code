# coding: utf-8

'''
Debugging related consts.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import enum

from veredi.base.enum import FlagCheckMixin


# -----------------------------------------------------------------------------
# Flags for e.g. Extra Logging
# -----------------------------------------------------------------------------

@enum.unique
class DebugFlag(FlagCheckMixin, enum.Flag):
    '''
    has() and any() provided by FlagCheckMixin.
    '''

    # ------------------------------
    # veredi.game
    # ------------------------------

    LOG_TICK     = enum.auto()
    '''Output a log message each tick at debug level.'''

    RAISE_ERRORS = enum.auto()
    '''Re-raises any errors/exceptions caught in Engine object itself.'''

    SYSTEM_DEBUG = enum.auto()
    '''Output extra SystemManager/System logs at debug level.'''

    GAME_ALL = LOG_TICK | RAISE_ERRORS | SYSTEM_DEBUG
    '''All the game debugging flags.'''

    # ------------------------------
    # veredi.interface
    # ------------------------------

    MEDIATOR_BASE = enum.auto()
    '''Extra debugging output on base mediator code.'''

    MEDIATOR_SERVER = enum.auto()
    '''Extra debugging output on mediator server-side.'''

    MEDIATOR_CLIENT = enum.auto()
    '''Extra debugging output on mediator client-side.'''

    MEDIATOR_ALL = MEDIATOR_BASE | MEDIATOR_SERVER | MEDIATOR_CLIENT
    '''Extra debugging output on all mediator code.'''

    # ------------------------------
    # veredi.zest
    # ------------------------------

    SPAM = GAME_ALL | MEDIATOR_ALL
    '''Go loud. Turn it all up.'''
