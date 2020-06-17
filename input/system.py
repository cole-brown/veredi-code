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
                    Optional, Union, Type, Set, Tuple)
if TYPE_CHECKING:
    from veredi.game.ecs.component      import ComponentManager
    from veredi.game.ecs.entity         import EntityManager

from veredi.game.ecs.manager import EcsManager
from decimal import Decimal


# ---
# Code
# ---
from veredi.logger                  import log
from veredi.base.const              import VerediHealth
from veredi.base.context            import VerediContext
from veredi.data.config.context     import ConfigContext
from veredi.data.config.registry    import register

# Game / ECS Stuff
from veredi.game.ecs.event          import EventManager
from veredi.game.ecs.time           import TimeManager

from veredi.game.ecs.const          import (SystemTick,
                                            SystemPriority)

from veredi.game.ecs.base.identity  import ComponentId
from veredi.game.ecs.base.system    import System
from veredi.game.ecs.base.component import Component
from veredi.game.identity.component import IdentityComponent

from .context import InputSystemContext, InputUserContext
from . import sanitize
from .parse import Parcel
from .commander import Commander

# Input-Related Events & Components
from .event                         import CommandInputEvent
# from .component                     import InputComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# §-TODO-§ [2020-06-11]: This or the Commander would be the place to capture
# everything required for undo?


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


@register('veredi', 'input', 'system')
class InputSystem(System):

    def _configure(self, context: VerediContext) -> None:
        '''
        Make our stuff from context/config data.
        '''

        self._registration_broadcast: bool = False

        # ---
        # Health Stuff
        # ---
        self._required_managers:   Optional[Set[Type[EcsManager]]] = {
            TimeManager,
            EventManager
        }
        self._health_meter_update: Optional[Decimal] = None
        self._health_meter_event:  Optional[Decimal] = None

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
        self._context = InputSystemContext('veredi.input.system')
        self._context.pull(context)

        config = ConfigContext.config(context)  # Configuration obj
        if not config:
            raise ConfigContext.exception(
                context,
                None,
                "Cannot configure {} without a Configuration in the "
                "supplied context.",
                self.__class__.__name__)
        # Our input parsers collection. Will create our interfaces (Mather)
        # which will create our ruleset parsers from the context/config data
        # (e.g. a 'D11Parser' math parser).
        self._parsers: Parcel = Parcel(context)
        # Our command sub-system.
        self._commander: Commander = config.make(None,
                                                 'input',
                                                 'parser',
                                                 'command')

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
        # Â§-TODO-Â§ [2020-06-04]: Is that a base class we can cover everything
        # easily under, or do we need more?
        self._manager.event.subscribe(CommandInputEvent,
                                      self.event_input_cmd)

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
            # Â§-TODO-Â§ [2020-06-04]: a health thing? e.g.
            # self._health_update(EntityDNE)
            return
        user = None
        player = None
        ident = entity.get(IdentityComponent)
        if ident:
            user = ident.log_user
            player = ident.log_player

        # Check user input.
        log.debug("Input from u:'{}' p:'{}'. input-string: '{}', event: {}",
                  user, player,
                  event.string_unsafe, event)
        string_safe, string_valid = sanitize.validate(event.string_unsafe,
                                                      entity.user,
                                                      entity.player,
                                                      event.context)

        if string_valid != sanitize.InputValid.VALID:
            log.info("Input from u:'{}' p:'{}': "
                     "Dropping event {} - input failed validation.",
                     event,
                     context=event.context)
            # §-TODO-§ [2020-06-11]: Keep track of how many times user was
            # potentially naughty?
            return

        # Get the command processed.
        todo this

        # TODO: fire off event for whoever's next?

        # # Have EventManager create and fire off event for whoever wants the
        # # next step.
        # if component.id != ComponentId.INVALID:
        #     next_event = InputResult(event.id, event.type, event.context,
        #                              component_id=component.id,
        #                              input=event.input, amount=amount)
        #     self._event_notify(next_event)

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

        # All we want to do is send out the command registration broadcast.
        # Then we want to not tick this again.
        self._event_notify(self._commander.registration(self.id,
                                                        self.context))
        self._registration_broadcast = True

        return self._health_check()
