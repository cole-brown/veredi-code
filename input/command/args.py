# coding: utf-8

'''
Constants for Commands, Command sub-system, Command events, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Union, Optional, Any, Protocol, Type, Mapping)
if TYPE_CHECKING:
    from veredi.base.const import VerediHealth
    from veredi.game.ecs.base.component import Component
    from veredi.game.ecs.base.entity import Entity


import enum
import re


from veredi.logger import log
from veredi.base.context import VerediContext

from veredi.game.ecs.base.identity import EntityId

from .const import CommandFailure
from ..context import InputContext


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


class CommandArgType(enum.Enum):
    '''
    For arg types that systems don't actually care about.

    "Yeah, it's a math parser thing; whatever."
    '''
    INVALID = 0

    # ---
    # Maths
    # ---
    VARIABLE = enum.auto()
    MATH = enum.auto()

    # ---
    # Texts
    # ---
    WORD = enum.auto()
    STRING = enum.auto()


# -----------------------------------------------------------------------------
# Args & Kwargs
# -----------------------------------------------------------------------------

class CommandArg:
    '''
    Class to encapsulate what an arg is called and what it expects to receive.
    '''

    RE_FLAGS = re.IGNORECASE

    RE_WORD_STR = r'^(?P<arg>\w+)\s*?(?P<remainder>.*)?$'
    RE_WORD = re.compile(RE_WORD_STR, RE_FLAGS)

    RE_STRING_STR = r'^(?P<arg>\w+\s*?[\w\s]*)$'
    RE_STRING = re.compile(RE_STRING_STR, RE_FLAGS)

    def __init__(self,
                 name:     str,
                 type:     Union[Type, 'CommandArgType'],
                 optional: Optional[bool] = False,
                 help:     Optional[str]  = None) -> None:
        '''
        `name`: Name of argument (for e.g. help/usage text).

        `type`: Type of argument (must be converted to this successfully
                before the command can execute).

        `optional`: Whether argument is required or is optional.

        `help`: Help text.
        '''
        self._name = name
        self._text_help = help

        self._type = type

        self._optional = optional

    @property
    def name(self):
        '''
        Text name of argument (for e.g. help/usage text).
        '''
        return self._name

    @property
    def type(self):
        '''
        Type of argument (must be converted to this successfully
        before the command can execute).
        '''
        return self._type

    @property
    def optional(self):
        '''
        Optional: Whether argument is required or is optional.
        '''
        return self._optional

    @property
    def help(self):
        '''
        Help: Help text.
        '''
        return self._help

    def parse(self, input_str: str) -> Optional[str]:
        '''
        Parse input string with the assumption that this arg should get the
        some or all of it, anchored at the start of the string.

        Returns any remainder of `input_str` that it doesn't claim.
        '''
        # Ignore ones we don't control (e.g. math).

        if self.type == CommandArgType.WORD:
            if not input_str:
                return ('', input_str)

            match = self.RE_WORD.match(input_str)
            arg = match.group('arg') if match else ''
            remainder = match.group('remainder') if match else ''
            if not match:
                msg = "Can't parse arg type '{}'.".format(self.type)
                error = NotImplementedError(
                    msg,
                    input_str)
                raise log.exception(error, None, msg)
                # If not raising anymore, return full input_str as remainder.
                # return (None, input_str)
            return (arg, remainder)

        elif self.type == CommandArgType.STRING:
            if not input_str:
                return ('', input_str)

            match = self.RE_WORD.match(input_str)
            arg = match.group('arg') if match else None
            # No remainder for string - eats whole input or none.
            if not match or not arg:
                return (None, None)
            return (arg, None)

        msg = "Can't parse arg type '{}'.".format(self.type)
        error = NotImplementedError(
            msg,
            input_str)
        raise log.exception(error, None, msg)


class CommandKwarg(CommandArg):
    '''
    Class to return a CommandArg during command execution as a keyword arg
    rather than a positional arg.
    '''

    def __init__(self,
                 kwarg_name:   str,
                 cmd_arg_name: str,
                 type:         Union[Type, 'CommandArgType'],
                 optional:     Optional[bool] = False,
                 help:         Optional[str]  = None) -> None:
        '''
        `kwarg_name`: Name of parameter command should use during execution
                      when invoking command on receiver.

        `cmd_arg_name`: Name of command argument (for e.g. help/usage text).

        `type`: Type of argument (must be converted to this successfully
                before the command can execute).

        `optional`: Whether argument is required or is optional.

        `help`: Help text.
        '''
        super().__init__(cmd_arg_name, type, optional, help)
        self._kwarg_name = kwarg_name

    @property
    def kwarg(self):
        '''
        Name of parameter command should use during execution when invoking
        command on receiver.
        '''
        return self._kwarg_name


# -----------------------------------------------------------------------------
# Return Value is an Argument, Sorta... I Guess.
# -----------------------------------------------------------------------------

class CommandStatus:
    '''
    Class to indicate success/failure status of command execution/invocation.

    If failure, you should provide info on what failed, if possible, so that
    output can be human-helpful.
    '''
    # Â§-TODO-Â§ [2020-06-14]: The 'be helpful' side should be done better than
    # just a string...

    # -------------------------------------------------------------------------
    # Easy/Lazy Return Status Helpers
    # -------------------------------------------------------------------------

    # ---
    # FAILURES - For Systems Executing Commands
    # ---

    @staticmethod
    def system_health(sys_name: str,
                      health:   'VerediHealth',
                      context:  InputContext) -> 'CommandStatus':
        '''
        Create a CommandStatus object for an unhealthy system.
        '''
        flags = CommandFailure.SYSTEM_HEALTH

        # TODO: should these be user-display strings?
        internal = ("'{}' is reporting poor health: {}. "
                    "It dropped command.").format(sys_name,
                                                  health)
        reason = "Game system for is sick right now... Try again?"

        return CommandStatus(False,
                             InputContext.input(context),
                             user_reason=reason,
                             internal_reason=internal,
                             flags=flags)

    @staticmethod
    def does_not_exist(entity_id:      EntityId,
                       entity:         'Entity',
                       component:      Type['Component'],
                       component_type: Type['Component'],
                       context:        InputContext) -> 'CommandStatus':
        '''
        Create a CommandStatus object for a non-existant entity or component.
        '''
        flags = CommandFailure.NO_FAILURE
        if not entity:
            flags = CommandFailure.ENTITY_DNE
        if entity and not component:
            flags |= CommandFailure.COMPONENT_DNE

        # TODO: should these be user-display strings?
        entity_name = InputContext.display.entity
        if not entity_name:
            reason = "Couldn't find the entity for the command."
        else:
            entity_data = InputContext.display.component
            if entity_data:
                entity_data += ' '
            reason = "Couldn't find either '{}' or their {}data.".format(
                entity_name,
                entity_data)

        internal = ('Entity or Component does not exist: '
                    'id: {}, entity: {}, component: {}').format(entity_id,
                                                                entity,
                                                                component)
        return CommandStatus(False,
                             InputContext.input(context),
                             user_reason=reason,
                             internal_reason=internal,
                             flags=flags)

    # ---
    # FAILURES - Parsing, Input, Permissions
    # ---

    @staticmethod
    def failure(command_safe:    str,
                user_reason:     str,
                internal_reason: str,
                flags:           CommandFailure = CommandFailure.GENERIC
                ) -> 'CommandStatus':
        '''
        Create a CommandStatus object for a failed command.
        '''
        return CommandStatus(False, command_safe,
                             user_reason,
                             internal_reason,
                             flags=flags)

    @staticmethod
    def unknown_for_user(command_safe: str,
                         reason: str,
                         internal: str) -> 'CommandStatus':
        '''
        Create a CommandStatus object for an unknown command.

        "For user" as this 'unknown' command could very well exist but maybe we
        want to not acknowledge its existance due to the user not having
        required permissions.
        '''
        return CommandStatus(False, command_safe,
                             user_reason=reason,
                             internal_reason=internal,
                             flags=CommandFailure.UNKNOWN_CMD)

    @staticmethod
    def permissions(command_safe: str,
                    reason: str,
                    internal: str) -> 'CommandStatus':
        '''
        Create a CommandStatus object for a command that a user failed
        permission checks for.

        This should probably be/be-very-close-to unknown_for_user().
        '''
        return CommandStatus.unknown_for_user(command_safe, reason, internal)

    @staticmethod
    def parsing(command_safe: str,
                reason: str,
                internal: str) -> 'CommandStatus':
        '''
        Create a CommandStatus object for a command that failed to properly
        parse its input string into arguments.
        '''
        return CommandStatus(False, command_safe,
                             reason, internal,
                             flags=CommandFailure.INPUT_PARSE)

    # ---
    # Successes.
    # ---

    @staticmethod
    def successful(context: VerediContext) -> 'CommandStatus':
        '''
        Create a CommandStatus object for a successful command.
        '''
        cmd = InputContext.input(context)
        return CommandStatus(True, cmd, None, None)

    # ---
    # Init
    # ---

    def __init__(self,
                 success: bool,
                 command_safe: str,
                 user_reason: str,
                 internal_reason: str,
                 flags: CommandFailure = CommandFailure.NO_FAILURE,
                 **kwargs: str) -> None:
        self.success         = success
        self.command_safe    = command_safe
        self.user_reason     = user_reason
        self.internal_reason = internal_reason

        self.specifics       = kwargs
        self._flags          = flags

    @property
    def flags(self) -> CommandFailure:
        '''
        Returns our failure flag member value.
        '''
        return self._flags

    @flags.setter
    def flags(self, value: CommandFailure) -> None:
        '''
        Setter for our failure flag member value.
        Overwrites, so do any flag or'ing, masking, etc. before-hand.
        '''
        self._flags = value


# -----------------------------------------------------------------------------
# Command Invocation Signature
# -----------------------------------------------------------------------------

class CommandInvoke(Protocol):
    '''
    Protocol class for defining what the Command Invokee should use for their
    function signature.
    '''

    def __call__(self,
                 *args: Any,
                 context: Optional[InputContext] = None,
                 **kwargs: Mapping[str, Any]) -> CommandStatus:
        ...
