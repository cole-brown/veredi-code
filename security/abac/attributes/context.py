# coding: utf-8

'''
Access-Based Access Control - Attributes for Contextual aspects.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import enum
from veredi.base.enum    import FlagCheckMixin, FlagSetMixin


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Attributes
# -----------------------------------------------------------------------------

# TODO: make sure we're actually doing Attribute-based Access Control
# https://en.wikipedia.org/wiki/Attribute-based_access_control

@enum.unique
class Context(FlagCheckMixin, FlagSetMixin, enum.Flag):
    '''
    Attribute-based Access Control via these Context Permission Flags.
    '''

    # ------------------------------
    # Blanket Attributes:
    # ------------------------------

    INVALID = 0
    '''No one is allowed to use this? Probably an error...'''

    UNRESTRICTED = enum.auto()
    '''
    Command has no restrictions or permission requirements. Any user
    authenticated into a game can use it.
    '''

    # ------------------------------
    # Contextual (Environment) Attributes:
    # ------------------------------
    # Attributes that deal with time, location or dynamic aspects of the access
    # control scenario.
    # ---

    # No contextual attributes atm...

    # ------------------------------
    # !!! Non-Standard Attributes !!!
    # ------------------------------
    #   - These won't show up in real games or be available to
    #     real/normal users.
    #   - THESE HAVE THE POSSIBILITY OF RUINING EVERYTHING IN YOUR GAME!
    # ---

    _DEBUG = enum.auto()
    '''
    Only allowed when game is in a debugging state/context and user is
    allowed to debug. Minor havoc could be caused if done wrong.
    '''

    _TEST = enum.auto()
    '''
    Only allowed when game is in a testing state/context and user is allowed
    to test. Some amount of havoc will probably happen.
    '''

    _GHOST_IN_THE_MACHINE = _DEBUG | _TEST
    '''
    This probably means you're either a hacker or the other kind of hacker.
    Good luck and god speed; sorry about the mess- I mean source code.
    '''
