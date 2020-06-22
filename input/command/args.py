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
    from veredi.game.ecs.base.component import Component
    from veredi.game.ecs.base.entity import Entity


import enum


from veredi.base.context import VerediContext

from veredi.game.ecs.base.identity import EntityId

from . import const
from ..context import InputSystemContext, InputUserContext


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


# -----------------------------------------------------------------------------
# Args & Kwargs
# -----------------------------------------------------------------------------

class CommandArg:
    '''
    Class to encapsulate what an arg is called and what it expects to receive.
    '''

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
    def does_not_exist(entity_id: EntityId,
                       entity: 'Entity',
                       component: Type['Component'],
                       component_type: Type['Component'],
                       context: InputUserContext) -> 'CommandStatus':
        '''
        Create a CommandStatus object for an unknown command.

        "For user" as this 'unknown' command could very well exist but maybe we
        want to not acknowledge its existance due to the user not having
        required permissions.
        '''
        flags = const.CommandFailure.NO_FAILURE
        if not entity:
            flags = const.CommandFailure.ENTITY_DNE
        if entity and not component:
            flags |= const.CommandFailure.COMPONENT_DNE

        # TODO: should these be user-display strings?
        reason = ('Entity or Component does not exist: '
                  'id: {}, entity: {}, component: {}').format(entity_id,
                                                              entity,
                                                              component)
        return CommandStatus(False,
                             InputSystemContext.input(context),
                             reason,
                             flags=flags)

    # ---
    # FAILURES - Parsing, Input, Permissions
    # ---

    @staticmethod
    def failure(command_safe: str,
                reason: str,
                flags:  const.CommandFailure = const.CommandFailure.GENERIC
                ) -> 'CommandStatus':
        '''
        Create a CommandStatus object for a failed command.
        '''
        return CommandStatus(False, command_safe, reason,
                             flags=flags)

    @staticmethod
    def unknown_for_user(command_safe: str,
                         reason: str) -> 'CommandStatus':
        '''
        Create a CommandStatus object for an unknown command.

        "For user" as this 'unknown' command could very well exist but maybe we
        want to not acknowledge its existance due to the user not having
        required permissions.
        '''
        return CommandStatus(False, command_safe, reason,
                             flags=const.CommandFailure.UNKNOWN_CMD)

    @staticmethod
    def permissions(command_safe: str,
                    reason: str) -> 'CommandStatus':
        '''
        Create a CommandStatus object for a command that a user failed
        permission checks for.

        This should probably be/be-very-close-to unknown_for_user().
        '''
        return CommandStatus.unknown_for_user(command_safe, reason)

    @staticmethod
    def parsing(command_safe: str,
                reason: str) -> 'CommandStatus':
        '''
        Create a CommandStatus object for a command that failed to properly
        parse its input string into arguments.
        '''
        return CommandStatus(False, command_safe, reason,
                             flags=const.CommandFailure.INPUT_PARSE)

    # ---
    # Successes.
    # ---

    @staticmethod
    def successful(context: VerediContext) -> 'CommandStatus':
        '''
        Create a CommandStatus object for a successful command.
        '''
        cmd = InputSystemContext.input(context)
        return CommandStatus(True, cmd, None)

    # ---
    # Init
    # ---

    def __init__(self,
                 success: bool,
                 command_safe: str,
                 reason: str,
                 flags: const.CommandFailure = const.CommandFailure.NO_FAILURE,
                 **kwargs: str) -> None:
        self.success      = success
        self.command_safe = command_safe
        self.reason       = reason

        self.specifics    = kwargs
        self._flags       = flags

    @property
    def flags(self) -> const.CommandFailure:
        '''
        Returns our failure flag member value.
        '''
        return self._flags

    @flags.setter
    def flags(self, value: const.CommandFailure) -> None:
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
                 context: Optional[InputUserContext] = None,
                 **kwargs: Mapping[str, Any]) -> CommandStatus:
        ...
