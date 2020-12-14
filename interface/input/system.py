# coding: utf-8

'''
Input System for Veredi.

Handles:
  - Input Events like
    - Commands
    - Rolls
    - Chat
    - Literally all input from users in game.
  - Other things probably.

Alot of Inputs.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Typing
# ---
from typing import (TYPE_CHECKING,
                    Optional, Union, Type, Set)
from veredi.base.null import Null
if TYPE_CHECKING:
    from decimal                   import Decimal

    from veredi.base.context       import VerediContext
    from veredi.game.ecs.component import ComponentManager
    from veredi.game.ecs.entity    import EntityManager
    from veredi.game.ecs.manager   import EcsManager

    from veredi.game.ecs.base.entity    import Entity
    from veredi.game.ecs.event    import Event


# ---
# Code
# ---
from veredi.data                         import background

from veredi.logger                       import log
from veredi.base.const                   import VerediHealth
from veredi.data.config.registry         import register

# Game / ECS Stuff
from veredi.game.ecs.event               import EventManager
from veredi.game.ecs.time                import TimeManager, MonotonicTimer

from veredi.game.ecs.const               import (SystemTick,
                                                 SystemPriority)

from veredi.game.ecs.base.system         import System
from veredi.game.ecs.base.component      import Component
from veredi.game.data.identity.component import IdentityComponent

from .context                            import InputContext
from .                                   import sanitize
from .parse                              import Parcel
from .command.commander                  import Commander
from .history.history                    import Historian

# Input-Related Events & Components
from .event                              import CommandInputEvent
# from .component                        import InputComponent

from ..mediator.event                    import MediatorToGameEvent
from ..mediator.const                    import MsgType
# from ..mediator.message                import Message

# TODO [2020-06-27]: Better place to do these registrations.
import veredi.zest.debug.registration


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO [2020-06-11]: This or the Commander would be the place to capture
# everything required for undo?


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


@register('veredi', 'interface', 'input', 'system')
class InputSystem(System):

    def _configure(self, context: 'VerediContext') -> None:
        '''
        Make our stuff from context/config data.
        '''

        self._registration_broadcast: bool            = False
        self._component_type:         Type[Component] = None
        '''Don't have a component type for input right now.'''

        # ---
        # Health Stuff
        # ---
        self._required_managers:   Optional[Set[Type['EcsManager']]] = {
            TimeManager,
            EventManager
        }
        self._health_meter_update: Optional['Decimal'] = None
        self._health_meter_event:  Optional['Decimal'] = None

        # ---
        # Ticking Stuff
        # ---
        self._components: Optional[Set[Type[Component]]] = None

        # Just the post-setup; pre-game-loop tick for now.
        # We'll do our CommandRegistrationBroadcast here and that's it.
        self._ticks: SystemTick = SystemTick.INTRA_SYSTEM

        # ---
        # Context Stuff
        # ---
        config = background.config.config
        if not config:
            raise background.config.exception(
                context,
                "Cannot configure {} without a Configuration in the "
                "supplied context.",
                self.__class__.__name__)
        # Our input parsers collection. Will create our interfaces (Mather)
        # which will create our ruleset parsers from the context/config data
        # (e.g. a 'D11Parser' math parser).
        self._parsers: Parcel = Parcel(context)

        # ---
        # Our Sub-System Stuff
        # ---
        self._commander: Commander = config.make(None,
                                                 'server',
                                                 'input',
                                                 'command')
        self._historian: Historian = config.make(None,
                                                 'server',
                                                 'input',
                                                 'history')

        # ---
        # More Context Stuff
        # ---
        # Create our background context now that we have enough info from
        # config.
        bg_data, bg_owner = self._background
        background.input.set(self.dotted(),
                             self._parsers,
                             bg_data,
                             bg_owner)

    @property
    def _background(self):
        '''
        Get background data for background.input.set().
        '''
        self._bg = {
            'dotted': self.dotted(),
            'commander': self._commander.dotted(),
            'historian': self._historian.dotted(),
        }
        return self._bg, background.Ownership.SHARE

    @classmethod
    def dotted(klass: 'InputSystem') -> str:
        # klass._DOTTED magically provided by @register
        return klass._DOTTED

    @property
    def historian(self) -> Historian:
        '''
        Getter for InputSystem's historian sub-system.
        '''
        return self._historian

    # -------------------------------------------------------------------------
    # System Registration / Definition
    # -------------------------------------------------------------------------

    def priority(self) -> Union[SystemPriority, int]:
        '''
        Returns a SystemPriority (or int) for when, relative to other systems,
        this should run. Highest priority goes firstest.
        '''
        # Trying out MEDIUM... why not?
        return SystemPriority.MEDIUM

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def _subscribe(self) -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        # InputSystem subs to:
        # - CommandInputEvent
        # - MediatorToGameEvent
        self._manager.event.subscribe(CommandInputEvent,
                                      self.event_input_cmd)
        self._manager.event.subscribe(MediatorToGameEvent,
                                      self.event_mediator_input)
        # TODO: Set MediatorToGameEvent wrongly to self.event_input_cmd.
        # zest_websocket_and_cmds will fail something (like test_ability_cmd).
        # Use this failure to fix
        # engine/MediatorSystem/zest_websocket_and_cmds's leaving the
        # MediatorServer sub-process running.

        # Commander needs to sub too:
        self._commander.subscribe(self._manager.event)

        return VerediHealth.HEALTHY

    def _event_to_cmd(self,
                      string_unsafe: str,
                      entity:        'Entity',
                      event:         'Event',
                      context:       'VerediContext') -> None:
        '''
        Take args, verify, and send on to commander for further processing.
        '''
        ident = entity.get(IdentityComponent)
        if not ident:
            log.debug("No IdentityComponent for entity - cannot process "
                      "input event. Entity '{}'. input-string: '{}', "
                      "event: {}",
                      entity, string_unsafe, event)
            return

        string_unsafe = None
        try:
            string_unsafe = event.payload
        except AttributeError:
            try:
                string_unsafe = event.string_unsafe
            except AttributeError as err:
                log.exception(err,
                              "Event {} does not have 'payload' or "
                              "'string_unsafe' property - input system "
                              "cannot process it as a command.",
                              event,
                              context=context)

        log.debug("Input from '{}' (by '{}'). input-string: '{}', event: {}",
                  ident.log_name, ident.log_extra,
                  string_unsafe, event)

        string_safe, string_valid = sanitize.validate(string_unsafe,
                                                      ident.log_name,
                                                      ident.log_extra,
                                                      event.context)

        if string_valid != sanitize.InputValid.VALID:
            log.info("Input from '{}' (by '{}'): "
                     "Dropping event {} - input failed validation.",
                     ident.log_name, ident.log_extra,
                     event,
                     context=event.context)
            # TODO [2020-06-11]: Keep track of how many times user was
            # potentially naughty?
            return

        command_safe = self._commander.maybe_command(string_safe)
        if not command_safe:
            log.info("Input from '{}' (by '{}'): "
                     "Dropping event {} - input failed `maybe_command()`.",
                     ident.log_name, ident.log_extra,
                     event,
                     context=event.context)
            # TODO [2020-06-11]: Keep track of how many times user was
            # potentially naughty?
            return

        # Create history, generate ID.
        input_id = self._historian.add_text(entity, string_safe)

        # Get the command processed.
        cmd_ctx = InputContext(input_id, command_safe,
                               entity.id,
                               ident.log_name,
                               self.dotted())
        cmd_ctx.pull(event.context)
        status = self._commander.execute(entity, command_safe, cmd_ctx)
        # Update history w/ status.
        self._historian.update_executed(input_id, status)

        # TODO [2020-06-21]: Success/Failure OutputEvent?

        if not status.success:
            log.error("Failed to execute command: {}",
                      string_safe,
                      context=cmd_ctx)
            return

        # Else, success. And nothing more to do now at this point.

    def event_mediator_input(self, event: MediatorToGameEvent) -> None:
        '''
        Input event from a client via the MediatorSystem.
        '''
        # We only care about the text-based messages.
        if event.type != MsgType.TEXT:
            return

        # Doctor checkup.
        if not self._health_ok_event(event):
            return

        entity = self._manager.entity.get_with_log(
            f'{self.__class__.__name__}',
            event.id,
            event=event)
        if not entity:
            # Entity disappeared, and that's ok.
            return

        # Check user input, send to commander, etc.
        self._event_to_cmd(event.payload, entity, event, event.context)

    def event_input_cmd(self, event: CommandInputEvent) -> None:
        '''
        Command Input thingy requested to happen; please resolve.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
            return

        entity = self._manager.entity.get_with_log(
            f'{self.__class__.__name__}',
            event.id,
            event=event)
        if not entity:
            # Entity disappeared, and that's ok.
            return

        # Check user input, send to commander, etc.
        self._event_to_cmd(event.string_unsafe, entity, event, event.context)

    # -------------------------------------------------------------------------
    # Game Update Loop/Tick Functions
    # -------------------------------------------------------------------------

    def _update_intra_system(self) -> VerediHealth:
        '''
        Generic tick function. We do the same thing every tick state we process
        so do it all here.
        '''
        # Already did our broadcast - nothing more to do.
        if self._registration_broadcast:
            log.debug("CommandRegistrationBroadcast: Did our thing already.")
            return self._health_check(SystemTick.INTRA_SYSTEM)

        # Doctor checkup.
        if not self._healthy(SystemTick.INTRA_SYSTEM):
            self._health_meter_update = self._health_log(
                self._health_meter_update,
                log.Level.WARNING,
                "HEALTH({}): Skipping ticks - our system health "
                "isn't good enough to process.",
                self.health)
            return self._health_check(SystemTick.INTRA_SYSTEM)

        reg_broadcast = self._commander.registration(self.id,
                                                     Null())
        log.debug("CommandRegistrationBroadcast about to broadcast: {}",
                  reg_broadcast)
        # TODO [2020-06-27]: better place to register these?
        veredi.zest.debug.registration.register(reg_broadcast)

        # All we want to do is send out the command registration broadcast.
        # Then we want to not tick this again.
        self._event_notify(reg_broadcast)
        self._registration_broadcast = True

        # Did a thing this tick so say we're PENDING...
        return VerediHealth.PENDING
