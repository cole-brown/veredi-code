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
from typing import Union, Any, Dict

# ---
# Code
# ---
from veredi.logger                  import log
from veredi.logger                  import pretty
from veredi.base.const              import VerediHealth
from veredi.base.context            import VerediContext
from veredi.data.config.registry    import register

# Game / ECS Stuff
from veredi.game.ecs.event          import EventManager
# from veredi.game.ecs.time           import TimeManager
# from veredi.game.ecs.component      import ComponentManager
# from veredi.game.ecs.entity         import EntityManager

from veredi.game.ecs.base.identity  import SystemId
# from veredi.game.ecs.base.system    import System
# from veredi.game.ecs.base.component import Component
# from veredi.game.identity.component import IdentityComponent

from .. import sanitize
from . import const
from .const import CommandPermission
from ..context import InputSystemContext, InputUserContext
from .exceptions           import (CommandRegisterError,
                                   CommandExecutionError)
from .command import Command
from .args import CommandStatus
# from ..event                        import CommandInputEvent
from .event                         import (CommandRegistrationBroadcast,
                                            CommandRegisterReply)
# from .component                     import InputComponent


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

    def __init__(self) -> None:
        '''
        Initialize Commander.
        '''
        self._commands: Dict[str, Command] = {}

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
        self._commands[event.name] = Command(event)

    # -------------------------------------------------------------------------
    # Sub-Command Functions
    #   (Called by the InputSystem)
    # -------------------------------------------------------------------------

    def _log(context: Union[InputSystemContext, InputUserContext],
             level: log.Level,
             command_name: str,
             command_safe: str,
             message: str,
             *args: Any,
             **kwargs: Any) -> None:
        '''
        Format command info from context into standard command log message,
        then append message and call log.at_level().

        Log's stack level (for method/class auto-print by logger) should be at
        level of caller of this function.
        '''

        cmd_info = {
            'source0': context.source0,
            'source1': context.source1,
            'name': command_name,
            'input': command_safe,
            'permissions': context.permissions,
        }

        fmt_pre = "- command: '{}' invoked by '{}' - "
        msg_pre = fmt_pre.format(command_name, context.source0)
        msg_post = '\n' + pretty.indented(cmd_info)

        log_fmt = msg_pre + message + msg_post
        log.incr_stack_level(kwargs)
        log.at_level(level, log_fmt, args, kwargs)

    def execute(self,
                command_safe: str,
                context: InputUserContext) -> CommandStatus:
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
            self._log(context,
                      log.Level.INFO,
                      name,
                      command_safe,
                      "Unknown or unregistered command '{}'. "
                      "Cannot process '{}'.",
                      name, command_safe)
            return CommandStatus.unknown_for_user(
                command_safe,
                "Unknown command '{}'".format(name))

        # Second, gotta check that caller is allowed.
        allowed = cmd.permissions != const.CommandPermission.INVALID
        # §-TODO-§ [2020-06-15]: Check permissions against caller's
        # authz/roles/whatever!
        if not allowed:
            self._log(context,
                      log.Level.INFO,
                      name,
                      command_safe,
                      "Insufficient permissions for command '{}'. "
                      "Will not process '{}'.",
                      name, command_safe)
            return CommandStatus.permissions(
                command_safe,
                "Unknown command '{}'".format(name))

        # Third, parse input_safe into args.
        args, kwargs, status = cmd.parse(input_safe, context)
        if not status.success:
            self._log(context,
                      log.Level.INFO,
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
                      name,
                      command_safe,
                      "Execution failed for command '{}', input: '{}'. "
                      "Error: {}",
                      name, command_safe,
                      error)
            # Reraise for our parent system to know about.
            raise

        # Did a thing; return whether it was a successful doing of a thing.
        return status
