# coding: utf-8

'''
System for handling Identity information (beyond the temporary in-game ID
numbers like MonotonicIds).

Papers, please.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Typing
# ---
from typing import Optional, Union, Set, Type
from veredi.game.ecs.manager import EcsManager
from decimal import Decimal

# ---
# Code
# ---
from veredi.logger                   import log
from veredi.base.const               import VerediHealth
from veredi.base.context             import VerediContext
from veredi.data.config.registry     import register

# Game / ECS Stuff
from veredi.game.ecs.event           import EventManager
from veredi.game.ecs.time            import TimeManager
from veredi.game.ecs.component       import ComponentManager
from veredi.game.ecs.entity          import EntityManager

from veredi.game.ecs.const           import (SystemTick,
                                             SystemPriority)

from veredi.game.ecs.base.identity   import ComponentId
from veredi.game.ecs.base.system     import System
from veredi.game.ecs.base.component  import Component
from veredi.game.ecs.base.exceptions import SystemErrorV

# Identity-Related Events & Components
from .event                          import IdentityRequest, IdentityResult
from .component                      import IdentityComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'game', 'identity', 'system')
class IdentitySystem(System):

    def _configure(self, context: VerediContext) -> None:
        '''
        Make our stuff from context/config data.
        '''

        # ---
        # Health Stuff
        # ---
        self._required_managers:    Optional[Set[Type[EcsManager]]] = {
            TimeManager,
            EventManager,
            ComponentManager,
            EntityManager
        }
        self._health_meter_update:  Optional[Decimal] = None
        self._health_meter_event:   Optional[Decimal] = None

        # ---
        # Ticking Stuff
        # ---
        self._components: Optional[Set[Type[Component]]] = [
            # For ticking, we need the ones with IdentityComponents.
            # They're the ones with Identitys.
            # Obviously.
            IdentityComponent
        ]

        # Just the normal one, for now.
        self._ticks: SystemTick = SystemTick.STANDARD

    @property
    def name(self) -> str:
        '''
        The 'dotted string' name this system has. Probably what they used to
        register.
        '''
        return 'veredi.game.identity.system'

    # -------------------------------------------------------------------------
    # System Registration / Definition
    # -------------------------------------------------------------------------

    def priority(self) -> Union[SystemPriority, int]:
        '''
        Returns a SystemPriority (or int) for when, relative to other systems,
        this should run. Highest priority goes firstest.
        '''
        return SystemPriority.LOW

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def subscribe(self, event_manager: EventManager) -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        super().subscribe(event_manager)

        # IdentitySystem subs to:
        # - IdentityRequests - This covers:
        #   - CodeIdentityRequest
        #   - DataIdentityRequest - may want to ignore or delete these...?
        self._manager.event.subscribe(IdentityRequest,
                                      self.event_identity_req)

        return self._health_check()

    def request_creation(self,
                         event: IdentityRequest) -> ComponentId:
        '''
        Asks ComponentManager to create the IdentityComponent from this event.

        Returns created component's ComponentId or ComponentId.INVALID
        '''
        data = None
        try:
            data = event.data
        except AttributeError as error:
            raise log.exception(
                error,
                SystemErrorV,
                "{} could not get identity data from event {}. context: {}",
                self.__class__.__name__,
                event, event.context
            )

        if not data:
            raise log.exception(
                None,
                SystemErrorV,
                "{} could not create IdentityComponent from no data {}. "
                "event: {}, context: {}",
                self.__class__.__name__,
                data, event, event.context
            )

        retval = self._manager.create_attach(event.id,
                                             IdentityComponent,
                                             event.context,
                                             data=data)

        return retval

    def event_identity_req(self, event: IdentityRequest) -> None:
        '''
        Identity thingy want; make with the component plz.
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

        log.debug("Papers, pleased:. {}", event)

        entity = self._manager.entity.get(event.id)
        if not entity:
            # Entity disappeared, and that's ok.
            log.info("Dropping event {} - no entity for its id: {}",
                     event, event.id,
                     context=event.context)
            # TODO [2020-06-04]: a health thing? e.g.
            # self._health_update(EntityDNE)
            return

        cid = self.request_creation(event)

        # Have EventManager create and fire off event for whoever wants the
        # next step.
        if (cid != ComponentId.INVALID):
            next_event = IdentityResult(event.id, event.type, event.context,
                                        component_id=cid)
            self._event_notify(next_event)

    # -------------------------------------------------------------------------
    # Game Update Loop/Tick Functions
    # -------------------------------------------------------------------------

    def _update(self,
                tick:          SystemTick,
                time_mgr:      TimeManager,
                component_mgr: ComponentManager,
                entity_mgr:    EntityManager) -> VerediHealth:
        '''
        Standard tick. Do we have ticky things to do?
        '''
        # Doctor checkup.
        if not self._healthy():
            self._health_meter_update = self._health_log(
                self._health_meter_update,
                log.Level.WARNING,
                "HEALTH({}): Skipping ticks - our system health "
                "isn't good enough to process.",
                self.health)
            return self._health_check()

        log.critical('todo: a identity tick thingy?')

        # for entity in self._wanted_entities(tick, time_mgr,
        #                                     component_mgr, entity_mgr):
        #     # Check if entity in turn order has a (identity) action queued up
        #     # Also make sure to check if entity/component still exist.
        #     if not entity:
        #         continue
        #     component = component_mgr.get(IdentityComponent)
        #     if not component or not component.has_action:
        #         continue

        #     action = component.dequeue
        #     log.debug("Entity {}, Comp {} has identity action: {}",
        #               entity, component, action)

        #     # Check turn order?
        #     # Would that be, like...
        #     #   - engine.time_flow()?
        #     #   - What does PF2/Starfinder call it? Like the combat vs
        #     #     short-term vs long-term 'things are happening' modes...

        #     # process action
        #     print('todo: a identity thingy', action)

        return self._health_check()
