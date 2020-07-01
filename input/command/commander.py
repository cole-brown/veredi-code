# coding: utf-8

'''
Commands for Veredi.

Handles:
  - Input Commands like
    - /roll
    - /whisper
    - /whatever
  - Other things probably.

o7
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Typing
# ---
from typing import Any, Dict


# ---
# Code
# ---
from veredi.logger                       import log
from veredi.logger                       import pretty
from veredi.base.const                   import VerediHealth
from veredi.base.context                 import VerediContext
from veredi.data.config.registry         import register
from veredi.data                         import background

# Game / ECS Stuff
from veredi.game.ecs.event               import EventManager
# from veredi.game.ecs.time              import TimeManager
# from veredi.game.ecs.component         import ComponentManager
# from veredi.game.ecs.entity            import EntityManager

from veredi.game.ecs.base.identity       import SystemId
from veredi.game.ecs.base.entity         import Entity
# from veredi.game.ecs.base.system       import System
# from veredi.game.ecs.base.component    import Component
from veredi.game.data.identity.component import IdentityComponent

from ..                                  import sanitize
from .                                   import const
from .const                              import CommandPermission
from ..context                           import InputContext
from .exceptions                         import (CommandRegisterError,
                                                 CommandExecutionError)
from .command                            import Command
from .args                               import CommandStatus
# from ..event                           import CommandInputEvent
from .event                              import (CommandRegistrationBroadcast,
                                                 CommandRegisterReply)
# from .component                        import InputComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO: a "register commands" event that InputSystem can send out once during
# loading phase... Needs to be after systems are done being created so all
# systems get a chance to respond.


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'input', 'commander')
class Commander:
    '''
    Command Pattern: Command Invoker, sort of.
      - InputSystem can also be seen as Invoker, sort of, since it decideds
        what is a command to be sent here for further processing before
        execution.

    Systems can register commands they want.

    The Commander can then receive input from its owner, InputSystem,
    process it, and invoke the registered receiver.

    The registered receiver /should/ be a function that does minimal processing
    and returns a created event to be sent to EventManager. This way other
    systems are not stealing time from InputSystem/Commander, and do the bulk
    of their command processing in their own context
    '''

    def __init__(self, context: VerediContext) -> None:
        '''
        Initialize Commander.
        '''
        self._commands: Dict[str, Command] = {}

    @property
    def name(self) -> str:
        '''
        The 'dotted string' name this system has. Probably what they used to
        register.
        '''
        return 'veredi.input.commander'

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def subscribe(self, event_manager: EventManager) -> VerediHealth:
        '''
        Gets the Commander set up to receive CommandCreate events during/after
        registration.
        '''
        # Commander subs to:
        # - CommandRegisterReply - for registration during set-up
        event_manager.subscribe(CommandRegisterReply,
                                self.event_register)

        return VerediHealth.HEALTHY

    def registration(self,
                     input_system_id: SystemId,
                     context:         VerediContext
                     ) -> CommandRegistrationBroadcast:
        '''
        Creates and returns a CommandRegistration event.

        InputSystem should kick it EventManager's way. EventManager should
        publish it, and then systems that care can respond with CommandRegister
        events for us.
        '''
        return CommandRegistrationBroadcast(
            input_system_id,
            CommandRegistrationBroadcast.TYPE_NONE,
            context)

    def event_register(self, event: CommandRegisterReply) -> None:
        '''
        Someone is requesting a command be registered.
        Ok.
        '''
        # Name sanity checks.
        if not event.name:
            raise log.exception(
                None,
                CommandRegisterError,
                "CommandRegisterReply has no name; cannot register it. {}",
                event,
                context=event.context)
        elif event.name in self._commands:
            raise log.exception(
                None,
                CommandRegisterError,
                "A command named '{}' is already registered; cannot "
                "register another. registered: {}",
                event.name,
                self._commands[event.name],
                context=event.context)

        # Permission sanity checks.
        if event.permissions == CommandPermission.INVALID:
            raise log.exception(
                None,
                CommandRegisterError,
                "CommandRegisterReply has invalid permissions ({}) for "
                "command named '{}'; cannot register it. {}",
                event.permissions,
                event.name,
                event,
                context=event.context)

        # Event is probably sane.
        # Now turn it into a Command object for our registration map.
        new_command = Command(event)
        self._commands[event.name] = new_command

        background.command.registered(event.source, new_command.name)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _log(self,
             context:      InputContext,
             level:        log.Level,
             entity:       Entity,
             command_name: str,
             command_safe: str,
             message:      str,
             *args:        Any,
             **kwargs:     Any) -> None:
        '''
        Format command info from context into standard command log message,
        then append message and call log.at_level().

        Log's stack level (for method/class auto-print by logger) should be at
        level of caller of this function.
        '''
        ident = None
        if entity:
            ident = entity.get(IdentityComponent)
        ent_name = ident.name if ident else None
        cmd_info = {
            'source': {
                'name': ent_name,
                'group': ident.group if ident else None,
            },
            'name': command_name,
            'input': command_safe,
        }

        fmt_pre = "- command: '{}' invoked by '{}' - "
        msg_pre = fmt_pre.format(command_name, ent_name)
        msg_post = '\n' + pretty.indented(cmd_info)

        log_fmt = msg_pre + message + '{msg_post}'
        kwargs['msg_post'] = msg_post
        log.incr_stack_level(kwargs)
        log.at_level(level, log_fmt, *args, **kwargs)

    # -------------------------------------------------------------------------
    # Sub-Command Functions
    #   (Called by the InputSystem)
    # -------------------------------------------------------------------------

    def maybe_command(self, string_safe: str) -> bool:
        '''
        Checks if string_safe starts with the command prefix
        (`const._TEXT_CMD_PREFIX`).

        If so, returns `command_safe` (`string_safe` minus its
        `const._TEXT_CMD_PREFIX` prefix).

        If not, returns None.
        '''
        # Assuming safe'd, so should also be trimmed/stripped.
        if string_safe.startswith(const._TEXT_CMD_PREFIX):
            return string_safe[len(const._TEXT_CMD_PREFIX):]

        return None

    def execute(self,
                entity:       Entity,
                command_safe: str,
                context:      InputContext) -> CommandStatus:
        '''
        Evaluate `command_safe` (expects a safe, already validated string) into
        a command, parse its args, and invoke its receiver with those args...
        Assuming success of finding the command, then assuming success of
        parsing args.

        Returns CommandStatus.
          - If it failed before invoking receiver, failure will indicate what
            went wrong here, else receiver is responsible for indicating what
            went wrong where.
        '''
        name, input_safe = sanitize.command_split(command_safe)

        # First, gotta actually find it.
        cmd = self._commands.get(name, None)
        if not cmd:
            # Nothing by that name. Log and fail out.
            msg = ("Unknown or unregistered command '{}'. "
                   "Cannot process '{}'.").format(
                       name, command_safe)
            self._log(context,
                      log.Level.INFO,
                      entity,
                      name,
                      command_safe,
                      msg)
            return CommandStatus.unknown_for_user(
                command_safe,
                "Unknown command '{}'".format(name),
                msg
            )

        # Second, gotta check that caller is allowed.
        allowed = cmd.permissions != const.CommandPermission.INVALID
        # TODO [2020-06-15]: Check permissions against caller's
        # authz/roles/whatever!
        if not allowed:
            msg = ("Entity is not allowed to executed command '{}' ('{}'). "
                   "Will not process '{}'.").format(
                       name, cmd.permissions, command_safe)
            self._log(context,
                      log.Level.INFO,
                      entity,
                      name,
                      command_safe,
                      msg)
            return CommandStatus.permissions(
                command_safe,
                "Unknown command '{}'".format(name),
                msg)

        # Third, parse input_safe into args.
        args, kwargs, status = cmd.parse(input_safe, context)
        if not status.success:
            self._log(context,
                      log.Level.INFO,
                      entity,
                      name,
                      command_safe,
                      "Parsing failed for command '{}'. "
                      "Will not execute '{}'.",
                      name, command_safe)
            return status

        # Fourth, execute?
        try:
            status = cmd.execute(*args, **kwargs, context=context)
        except CommandExecutionError as error:
            self._log(context,
                      log.Level.ERROR,
                      entity,
                      name,
                      command_safe,
                      "Execution failed for command '{}', input: '{}'. "
                      "Error: {}",
                      name, command_safe,
                      error)
            # Reraise for our parent system to know about.
            raise

        if status is None:
            raise log.exception(None,
                                CommandExecutionError,
                                "Invoked command '{}' did not return status. "
                                "input: '{}'",
                                name, command_safe)

        # Did a thing; return whether it was a successful doing of a thing.
        return status
