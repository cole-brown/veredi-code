# coding: utf-8

'''
Access-Based Access Control - Attributes for Objects.
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
class Object(FlagCheckMixin, FlagSetMixin, enum.Flag):
    '''
    Attribute-based Access Control via these Object Permission Flags.
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
    # Object Attributes:
    # ------------------------------
    # Attributes that describe the object (or resource) being accessed e.g. the
    # object type (medical record, bank account...), the department, the
    # classification or sensitivity, the location...
    # ---

    ENTITY = enum.auto()
    '''
    Check command's data for what EntityTypeIds are allowed to execute this
    command.
    '''

    COMPONENT = enum.auto()
    '''
    Check command's data for what components are required in order for entity
    to be allowed to do this.

    NOTE: This is not a "components needed for command to function properly".
    It is, for example, only allowing attack commands from things with
    HealthComponents. They don't need health to attack, probably, but maybe you
    want to restrict attacking to entities who can receive damage in return.
    '''

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

    _GHOST_IN_THE_MACHINE = ENTITY | COMPONENT | _DEBUG | _TEST
    '''
    This probably means you're either a hacker or the other kind of hacker.
    Good luck and god speed; sorry about the mess- I mean source code.
    '''
