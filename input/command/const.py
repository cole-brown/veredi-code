# coding: utf-8

'''
Constants for Commands, Command sub-system, Command events, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import enum


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_TEXT_CMD_PREFIX = '/'
'''
Things outside the Command sub-system internals should not need to reference
this.
'''


# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------
# §-TODO-§ [2020-06-15]: Move to wherever permissions/authz lives once it lives

@enum.unique
class CommandPermission(enum.Flag):
    '''
    Role/Attribute-based Access Control via these Permission Flags.

    Users are authenticated and receive a number of Authorization flags for
    what kind of actions they can preform in what context.

    When the user attempts to execute a command, their authorization is checked
    against the command's permissions before allowing.
    '''

    INVALID = 0
    '''No one is allowed to use this? Probably an error...'''

    UNRESTRICTED = enum.auto()
    '''Command has no restrictions or permission requirements. Any user
    authenticated into a game can use it.'''

    # ---
    # Attributes
    # ---

    ENTITY_TYPE = enum.auto()
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

    # ---
    # Roles
    # ---

    NPC = enum.auto()
    '''Only allowed by NPC entities (presumably acting under GM direction).'''

    PLAYER = enum.auto()
    '''Only allowed by player entities (presumably acting under human user
    direction).'''

    GM = enum.auto()
    '''Only allowed by the GM entity/entities (presumably acting under the
    blessing of the game owner).'''

    OWNER = enum.auto()
    '''Only allowed by the owner entity of the game.'''

    # ---
    # Non-Standard Permissions Below Here!
    #   - These won't show up in real games or be available to
    #     real/normal users.
    #   - THESE HAVE THE POSSIBILITY OF RUINING EVERYTHING IN YOUR GAME!
    # ---

    DEBUG = enum.auto()
    '''Only allowed when game is in a debugging state/context and user is
    allowed to debug. Minor havoc could be caused if done wrong.'''

    TEST = enum.auto()
    '''Only allowed when game is in a testing state/context and user is allowed
    to test. Some amount of havoc will probably happen.'''

    # ---
    # Masks / Combinations
    # ---

    GHOST_IN_THE_MACHINE = GM | OWNER | DEBUG | TEST
    '''
    This probably means you're either a hacker or the other kind of hacker.
    Good luck and god speed; sorry about the mess- I mean source code.
    '''

    def has(self, flag):
        '''
        True if `flag` bit is set in this enum value.
        '''
        return ((self & flag) == flag)


# -----------------------------------------------------------------------------
# Failure Info
# -----------------------------------------------------------------------------

@enum.unique
class CommandFailure(enum.Flag):
    '''
    Flags for helping code understand what all went wrong in a command, so that
    it can hopefully tell the user more helpfully.
    '''

    NO_FAILURE = 0
    '''This means you f'd up. I'm talking to you, Mr. Programmer. You've got a
    failure of NO_FAILURE; please make sure the universe is right-side up.'''

    GENERIC = enum.auto()
    '''This means you're lazy or forgot to make a better one... Or maybe you're
    just trying to make some code on top and not mess with Veredi itself.
    Apologies for not making a better option.'''

    # ---
    # Actual Failures
    # ---

    UNKNOWN_CMD = enum.auto()
    '''
    For this specific user and their specific authz, Command does not exist /
    is not known. Maybe we actually don't have anything registered for it.
    Maybe we do but it's permissions don't allow user to call it.
    '''

    INPUT_PARSE = enum.auto()
    '''
    Could not parse input into parameters.
    '''

    def has(self, flag):
        '''
        True if `flag` bit is set in this enum value.
        '''
        return ((self & flag) == flag)
