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


# ---
# Code
# ---
from veredi.data                         import background

from veredi.logger                       import log
from veredi.base.const                   import VerediHealth
from veredi.data.config.registry         import register

# Game / ECS Stuff
from veredi.game.ecs.event               import EventManager
from veredi.game.ecs.time                import TimeManager

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


@register('veredi', 'input', 'system')
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
                None,
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
                                                 'input',
                                                 'command')
        self._historian: Historian = config.make(None,
                                                 'input',
                                                 'history')

        # ---
        # More Context Stuff
        # ---
        # Create our background context now that we have enough info from
        # config.
        bg_data, bg_owner = self._background
        background.input.set(self.name,
                             self._parsers,
                             bg_data,
                             bg_owner)

    @property
    def _background(self):
        '''
        Get background data for background.input.set().
        '''
        self._bg = {
            'name': self.name,
            'commander': self._commander.name,
            'historian': self._historian.name,
        }
        return self._bg, background.Ownership.SHARE

    @property
    def name(self) -> str:
        '''
        The 'dotted string' name this system has. Probably what they used to
        register.
        '''
        return 'veredi.input.system'

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

    def subscribe(self, event_manager: EventManager) -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        super().subscribe(event_manager)

        # InputSystem subs to:
        # - InputRequests
        # TODO [2020-06-04]: Is that a base class we can cover everything
        # easily under, or do we need more?
        self._manager.event.subscribe(CommandInputEvent,
                                      self.event_input_cmd)

        # Commander needs to sub too:
        self._commander.subscribe(event_manager)

        return self._health_check()

    def event_input_cmd(self, event: CommandInputEvent) -> None:
        '''
        Command Input thingy requested to happen; please resolve.
        '''
        # Doctor checkup.
        if not self._healthy():
            self._health_meter_event = self._health_log(
                self._health_meter_event,
                log.Level.WARNING,
                "HEALTH({}): Dropping event {} - our system health "
                "isn't good enough to process.",
                self.health, event,
                context=event.context)
            return

        entity = self._manager.entity.get(event.id)
        if not entity:
            # Entity disappeared, and that's ok.
            log.info("Dropping event {} - no entity for its id: {}",
                     event, event.id,
                     context=event.context)
            # TODO [2020-06-04]: a health thing? e.g.
            # self._health_update(EntityDNE)
            return
        ident = entity.get(IdentityComponent)

        # Check user input.
        log.debug("Input from '{}' (by '{}'). input-string: '{}', event: {}",
                  ident.log_name, ident.log_extra,
                  event.string_unsafe, event)
        string_safe, string_valid = sanitize.validate(event.string_unsafe,
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
                               name=self.name)
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

    # -------------------------------------------------------------------------
    # Game Update Loop/Tick Functions
    # -------------------------------------------------------------------------

    def _update_intra_system(self,
                             time_mgr:      TimeManager,
                             component_mgr: 'ComponentManager',
                             entity_mgr:    'EntityManager') -> VerediHealth:
        '''
        Generic tick function. We do the same thing every tick state we process
        so do it all here.
        '''
        # Already did our broadcast - nothing more to do.
        if self._registration_broadcast:
            log.debug("CommandRegistrationBroadcast: Did our thing already.")
            return self._health_check()

        # Doctor checkup.
        if not self._healthy():
            self._health_meter_update = self._health_log(
                self._health_meter_update,
                log.Level.WARNING,
                "HEALTH({}): Skipping ticks - our system health "
                "isn't good enough to process.",
                self.health)
            return self._health_check()

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
