# coding: utf-8

'''
General Combat System for the Game.

Handles:
  - Combat events like: Attack, Damage, etc.
  - Other things probably.

Should probably:
  - Use sub-system type thingies from rules.d11...

That is the nexus of punching people in the face.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Set, Type, Union)
if TYPE_CHECKING:
    from decimal                    import Decimal
    from veredi.base.context        import VerediContext

from veredi.logger        import log
from veredi.base.const    import VerediHealth
from veredi.data          import background

# Game / ECS Stuff
from ..ecs.manager        import EcsManager
from ..ecs.event          import EventManager
from ..ecs.time           import TimeManager
from ..ecs.component      import ComponentManager
from ..ecs.entity         import EntityManager

from ..ecs.const          import (SystemTick,
                                  SystemPriority)

from ..ecs.base.system    import System
from ..ecs.base.component import Component

# Events
from .event import (
    AttackedEvent
)

# Components
from .component import OffensiveComponent, DefensiveComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class CombatSystem(System):

    def _configure(self, context: 'VerediContext') -> None:
        '''
        Make our stuff from context/config data.
        '''

        # ---
        # Health Stuff
        # ---
        self._health_meter_update:  Optional['Decimal'] = None
        self._health_meter_event:   Optional['Decimal'] = None
        self._required_managers:    Optional[Set[Type[EcsManager]]] = {
            TimeManager,
            EventManager,
            ComponentManager,
            EntityManager
        }

        # ---
        # Ticking Stuff
        # ---
        self._components: Optional[Set[Type[Component]]] = [
            # For ticking, we need the ones with OffensiveComponents.
            # They'll be what we check for attacks, etc. Then we process those
            # and event off the rest (resolve against their target's: defense
            # stuff, health stuff, etc).
            OffensiveComponent
        ]

        # Just the normal one, for now.
        self._ticks: SystemTick = SystemTick.STANDARD

        # ---
        # Config Stuff
        # ---
        config = background.config.config
        if not config:
            raise background.config.exception(
                context,
                None,
                "Cannot configure {} without a Configuration in the "
                "supplied context.",
                self.__class__.__name__)

        # What kind of ruleset are we using?
        self._ruleset   = config.get_rules('type')

        self._offensive = config.make('rules', 'combat', 'offensive')
        self._defensive = config.make('rules', 'combat', 'defensive')

        # Don't think this is our's. Think it's a separate system's concern?
        # Things other than combat can do damage. Or heal. Or whatever.
        # self._health    = config.get_rules('combat', 'offensive')

    @property
    def name(self) -> str:
        '''
        The 'dotted string' name this system has. Probably what they used to
        register.
        '''
        return 'veredi.rules.d20.combat.system'

    # -------------------------------------------------------------------------
    # System Registration / Definition
    # -------------------------------------------------------------------------

    def priority(self) -> Union[SystemPriority, int]:
        '''
        Returns a SystemPriority (or int) for when, relative to other systems,
        this should run. Highest priority goes firstest.
        '''
        # Could do a lower priority. Guessing at HIGH because we want to get
        # who's dead out of the way first.
        return SystemPriority.HIGH

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def subscribe(self, event_manager: 'EventManager') -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        super().subscribe(event_manager)

        # CombatSystem subs to:
        # - AttackedEvent
        #   An attack has happened and should be resolved.
        self._manager.event.subscribe(AttackedEvent,
                                      self.event_attacked)

        return self._health_check()

    def event_attacked(self, event: AttackedEvent) -> None:
        '''
        Attack happened; please resolve.
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

        pass
        # if not self._component_manager:
        #     raise log.exception(
        #         None,
        #         SystemErrorV,
        #         "{} could not create anything from event {} - it has no "
        #         "ContextManager. context: {}",
        #         self.__class__.__name__,
        #         event, event.context
        #     )

        # # Have EventManager create and fire off event for whoever wants the
        # # next step?
        # if cid != ComponentId.INVALID:
        #     event = DataLoadedEvent(event.id, event.type, event.context,
        #                             component_id=cid)
        #     self._event_notify(event)

    # -------------------------------------------------------------------------
    # Game Update Loop/Tick Functions
    # -------------------------------------------------------------------------

    def _update(self,
                tick:          SystemTick,
                time_mgr:      'TimeManager',
                component_mgr: 'ComponentManager',
                entity_mgr:    'EntityManager') -> VerediHealth:
        '''
        Main tick function.
        '''
        # Doctor checkup.
        if not self._healthy():
            self._health_meter_update = self._health_log(
                self._health_meter_update,
                log.Level.WARNING,
                "HEALTH({}): Skipping ticks - our system health "
                "isn't good enough to process.",
                self.health)
            return

        for entity in self._wanted_entities(tick, time_mgr,
                                            component_mgr, entity_mgr):
            pass

        # Â§-TODO-Â§ [2020-05-26]: this

        # check if Combat

        # delegate to subsystems and stuff

        # check turn order

        #     check if entity in turn order has a (combat) action queued up
        #     anywhere.

        #     process action

        # check for entities to add to turn order tracker

        return self._health_check()
