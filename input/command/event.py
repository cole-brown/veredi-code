# coding: utf-8

'''
Events related to input from user. All input from user should be either
packaged up into an event or perhaps fed directly/firstly into InputSystem.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, Optional, Type

from veredi.logger                  import log
from veredi.game.ecs.event          import Event
from veredi.game.ecs.base.component import Component

from .                              import const
from .exceptions                    import CommandRegisterError
from .args                          import (CommandArgType,
                                            CommandArg,
                                            CommandKwarg,
                                            CommandInvoke)


# -----------------------------------------------------------------------------
# Base Command Event
# -----------------------------------------------------------------------------

class CommandEvent(Event):
    '''Base Class: (Probably) Do Not Use.'''

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "CmdEvent"


class CommandRegistrationBroadcast(CommandEvent):
    '''
    No special members or properties... Just a broadcast event to anyone that
    we can now receive CommandRegisterReplies.

    CommandRegistrationBroadcast.id will be InputSystem's SystemId, in case
    more input tie-in is needed/wanted at time of event reception.
    '''

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "CmdRegBcast"


class CommandRegisterReply(CommandEvent):
    '''
    Everything Commander needs to create a command for this should be in here.
    '''

    def __init__(self,
                 registration:  CommandRegistrationBroadcast,
                 command_name:  str,
                 permissions:   const.CommandPermission,
                 event_trigger: CommandInvoke,
                 # ---
                 # Optional info about command
                 usage:         Optional[str] = None,
                 example:       Optional[str] = None,
                 description:   Optional[str] = None) -> None:
        '''
        Initialize Register reply event from Registration broadcast event.

        The command function `event_trigger` should be something light-weight.
        Any heavy lifting should be either queued up in your system for later
        (e.g. attached to a component), or sent out as an event to be processed
        when you receive it back.
        '''
        super().__init__(registration.id,
                         registration.type,
                         registration.context)

        self._set_name(command_name)
        self._set_perms(permissions)
        self._set_func(event_trigger, registration)

        self.usage:       str  = usage
        self.example:     str  = example
        self.description: str  = description

        self.args:       list = []
        self.kwargs:     dict = {}

    def _set_name(self, name: str) -> None:
        '''Raises a CommandError if name is invalid (e.g. starts with the
        command prefix).'''
        self.name = name.strip().lower()
        # TODO [2020-06-14]: Regex check... also must start with letter.
        if self.name.startswith(const._TEXT_CMD_PREFIX):
            self.name = None
            raise log.exception(None,
                                CommandRegisterError,
                                "Command name '{}' cannot start with '{}'. "
                                "That is the command input prefix for "
                                "text-based commands.",
                                name,
                                const._TEXT_CMD_PREFIX,
                                context=self.context)

    def _set_perms(self, permissions: const.CommandPermission) -> None:
        '''Permissions required for the command to execute.'''
        self.permissions = permissions

        self.permission_components = None
        if self.permissions.has(const.CommandPermission.COMPONENT):
            self.permission_components = set()

    def permission_components(self, *components: Component) -> None:
        '''
        Set component types required by permissions. Raises a
        CommandRegisterError if permissions bit CommandPermission.COMPONENT is
        not set.
        '''
        if (not self.permissions.has(const.CommandPermission.COMPONENT)
                or self.permission_components is None):
            raise log.exception(
                None,
                CommandRegisterError,
                "CommandRegisterReply '{}' is not set to require components. "
                "Set CommandPermission.COMPONENT flag in your permissions in "
                "the constructor if this command has required components. "
                "perms: {}, desired req comps: {}. event: {}",
                self.name,
                self.permissions,
                components,
                context=self.context)

        # Load the supplied components into our set.
        for comp in components:
            self.permission_components.add(comp)

    def _set_func(self,
                  event_constructor: CommandInvoke,
                  registration:      CommandRegistrationBroadcast) -> None:
        '''
        Sets the thing we call with the stuff once we're ready to execute the
        command.
        '''
        if not callable(event_constructor):
            raise log.exception(
                None,
                CommandRegisterError,
                "CommandRegisterReply '{}' needs a callable() for "
                "constructing a command event to be published. "
                "got: {}. event: {}",
                self.name,
                event_constructor,
                registration,
                context=self.context)
        self.function = event_constructor

    def add_arg(self,
                name: str,
                type: Union[Type, CommandArgType],
                optional: Optional[bool] = False,
                help: Optional[str] = None) -> None:
        '''
        Add a command argument into our data for registering this command.
        '''
        self.args.append(CommandArg(name, type, optional, help))

    def add_kwarg(self,
                  kwarg_name,
                  cmd_arg_name: str,
                  type: Union[Type, CommandArgType],
                  optional: Optional[bool] = False,
                  help: Optional[str] = None) -> None:
        '''
        Add a command argument into our data for registering this command.

        This is a kwarg for the receiving system in game, not for the command
        interface for the player.
        That is, if you want to receive:
            do_a_command(name='jeff')
        Instead of:
            do_a_command('jeff')
        '''
        self.kwargs[kwarg_name] = CommandKwarg(kwarg_name,
                                               cmd_arg_name,
                                               type,
                                               optional,
                                               help)

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "CmdRegReply"
