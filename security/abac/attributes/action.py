# coding: utf-8

'''
Access-Based Access Control - Attributes for Actions.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import enum
from veredi.base.strings import labeler
from veredi.base.enum    import FlagCheckMixin, FlagSetMixin
from veredi.data         import codec


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Attributes
# -----------------------------------------------------------------------------

# TODO: make sure we're actually doing Attribute-based Access Control
# https://en.wikipedia.org/wiki/Attribute-based_access_control

@codec.enum.encodable(name_dotted='veredi.security.abac.attributes.action',
                      name_string='attributes.action',
                      enum_encode_type=codec.enum.FlagEncodeName)
@enum.unique
class Action(FlagCheckMixin, FlagSetMixin, enum.Flag):
    '''
    Attribute-based Access Control via these Action Permission Flags.
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
    # Action Attributes:
    # ------------------------------
    # Attributes that describe the action being attempted e.g. read, delete,
    # view, approve...
    # ---
    # Prefix: "A_": "Action!"

    # No actions atm...

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
