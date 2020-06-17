# coding: utf-8

'''
User Input validation and sanitization.

In general, preferrs to drop anything it suspects of invalidity or insanity
rather than trying to "fix".
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Typing
# ---
from typing import Optional, Union, Type, Set, Tuple
from decimal import Decimal

# ---
# Code
# ---
import enum
import re

from veredi.logger                  import log
from veredi.base.const              import VerediHealth
from veredi.base.context            import VerediContext
from veredi.data.config.context     import ConfigContext
from veredi.data.config.registry    import register

# Game / ECS Stuff
from veredi.game.ecs.event          import EventManager
from veredi.game.ecs.time           import TimeManager
from veredi.game.ecs.component      import ComponentManager
from veredi.game.ecs.entity         import EntityManager

from veredi.game.ecs.const          import (SystemTick,
                                            SystemPriority)

from veredi.game.ecs.base.identity  import ComponentId
from veredi.game.ecs.base.system    import System
from veredi.game.ecs.base.component import Component


# Input-Related Events & Components
from .event                         import CommandInputEvent
# from .component                     import InputComponent


# -----------------------------------------------------------------------------
# General Constants
# -----------------------------------------------------------------------------

STRING_MAX_LENGTH = 500


RE_FLAGS = re.IGNORECASE
'''
Don't care about case in our input.
'''

RE_CMD_NAME_STR = (
    r'^\s*'
    r'(?P<cmd_name>\w[\w\d_-]{1,13}[\w\d])'
    r'\s?'
    r'(?P<cmd_input>.*)?'
    r'\s*$'
)
'''
Attempting to make regex that works for both checking just name and for
splitting name from rest of command. If it gets too annoying or ascii-soupy,
split those intentions apart.

Also using regex to strip whitespace.

Allowed in command name:
  - letters
  - digits
  - hyphen: '-'
  - underscore: '_'

Command name must start with a letter and end with a letter or digit.

Command name must be 3 to 15 characters long.
'''


RE_CMD_NAME = re.compile(RE_CMD_NAME_STR, RE_FLAGS)
'''re.Pattern of RE_CMD_NAME_STR & RE_FLAGS'''


@enum.unique
class InputValid(enum.Flag):
    UNKNOWN = enum.auto()
    '''
    A butterfly flapped its wings, probably. Who knows?
    '''

    STR_TOO_LONG = enum.auto()
    STR_UNPRINTABLE = enum.auto()
    '''
    String had unprintable characters in it; no-go.
    '''

    # ---
    # The only "ok; go" response.
    # ---
    VALID = enum.auto()
    '''
    This is the good one; if yours is not this, then the input you validated is
    bad juju.
    '''

    def set_flag(current, setting):
        '''
        Or's `setting` into `current` in such a way as to lose UNKNOWN if it is
        amongst them. Unless they are both just UNKNOWN. Then you get UNKNOWN
        back.
        '''
        result = current | setting
        result &= ~InputValid.UNKNOWN
        return result or InputValid.UNKNOWN


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def validate(string_unsafe: Optional[str],
             string_source0: Optional[str],
             string_source1: Optional[str],
             context_log: Optional[VerediContext] = None,
             ) -> Tuple[Optional[str], InputValid]:
    '''
    Checks `string_unsafe` for invalid conditions.

    `source0` and `source1` are for logging only.
    For PCs:
      - `source0`: Should be username.
      - `source1`: Should be player name.
    For other entities:
      - `source0`: Should be name.
      - `source1`: Don't care.

    Returns a Tuple of:
      - string_safe or None (if failed validation).
      - InputValid flags describing success/failure reasons.
    '''
    valid = InputValid.UNKNOWN

    strlen = len(string_unsafe)
    if strlen > STRING_MAX_LENGTH:
        valid = InputValid.set_flag(InputValid.STR_TOO_LONG)
        log.warning("Source '{}' ('{}') provided input string which was "
                    "very long. str-len: {}",
                    string_source0, string_source1,
                    strlen)

    if not string_unsafe.isprintable():
        valid = InputValid.set_flag(InputValid.STR_UNPRINTABLE)
        # What in heck are they sending us then?
        log.warning("Source '{}' ('{}') provided input string with "
                    "unprintable characters in it. str-len: {}",
                    string_source0, string_source1,
                    strlen)

    # If I still don't know, I guess it passes the tests...
    if valid == InputValid.UNKNOWN:
        return string_unsafe, InputValid.VALID

    return None, valid


def command_split(string_safe: str) -> Tuple[str, Optional[str]]:
    '''
    Checks `string_safe` against regex to ensure it starts with a valid Veredi
    command name. For what 'valid' is, exactly, see docstr for
    `RE_CMD_NAME_STR`.

    Splits `string_safe` into the "Command Name" portion, and the
    "And The Rest" portion. "And The Rest" can be None.

    Returns tuple of (cmd_name, the_rest):
      - if valid: cmd_name: Stripped of surrounding whitespace and lowercased.
                  the_rest: Stripped of surrounding whitespace.
      - else:     (None, None)
    '''
    match = RE_CMD_NAME.match(string_safe)
    cmd = match.group('cmd_name')
    if not match or not cmd:
        return (None, None)

    return cmd, match.group('cmd_input')
