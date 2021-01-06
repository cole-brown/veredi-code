# coding: utf-8

'''
Debugging related consts.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import enum

from veredi.base.enum import FlagCheckMixin, FlagSetMixin


# -----------------------------------------------------------------------------
# Flags for e.g. Extra Logging
# -----------------------------------------------------------------------------

@enum.unique
class DebugFlag(FlagCheckMixin, FlagSetMixin, enum.Flag):
    '''
    has() and any() provided by FlagCheckMixin.
    '''

    # ------------------------------
    # General Flags
    # ------------------------------

    LOG_SKIP = enum.auto()
    '''Enabled when certain logs should be skipped if unit testing.'''

    # ------------------------------
    # veredi.game
    # ------------------------------

    LOG_TICK = enum.auto()
    '''Output a log message each tick at debug level.'''

    RAISE_ERRORS = enum.auto()
    '''Re-raises any errors/exceptions caught in Engine object itself.'''

    RAISE_HEALTH = enum.auto()
    '''
    Raise an error if health becomes unrunnable. For help debugging when a
    health goes bad...
    '''

    RAISE_LOGS = enum.auto()
    '''
    Raise an error if a log is above a certain level.
    '''

    SYSTEM_DEBUG = enum.auto()
    '''Output extra SystemManager/System logs at debug level.'''

    MANUAL_ENGINE_TICK = enum.auto()
    '''
    Makes the engine only do one tick at a time, instead of infinitely looping.
    '''

    EVENTS = enum.auto()
    '''
    Debug stuff about events.
    '''

    NO_SAVE_FILES = enum.auto()
    '''
    Skip/mute check for saved game file.
    '''

    # ------------------------------
    # veredi.interface
    # ------------------------------

    MEDIATOR_BASE = enum.auto()
    '''Extra debugging output on base mediator code.'''

    MEDIATOR_SERVER = enum.auto()
    '''Extra debugging output on mediator server-side.'''

    MEDIATOR_CLIENT = enum.auto()
    '''Extra debugging output on mediator client-side.'''

    # ------------------------------
    # veredi.zest
    # ------------------------------

    # TODO: Change what gets set as default debug flags? To make them more
    # useful so they can spam when turned on?
    GAME_ALL = (LOG_TICK | RAISE_ERRORS | RAISE_HEALTH | RAISE_LOGS
                | SYSTEM_DEBUG | MANUAL_ENGINE_TICK)
    # | EVENTS)
    '''All the game debugging flags.'''

    MEDIATOR_ALL = MEDIATOR_BASE | MEDIATOR_SERVER | MEDIATOR_CLIENT
    '''Extra debugging output on all mediator code.'''

    SPAM = GAME_ALL | MEDIATOR_ALL
    '''Go loud. Turn it all up.'''
