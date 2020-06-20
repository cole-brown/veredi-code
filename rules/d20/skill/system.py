# coding: utf-8

'''
D20 Skill System for the Game.

Handles:
  - Skill events like:
    - Skill Checks
    - Opposed Skill Checks
    - Skill Checks vs DC
    - Skill Check for Helping Other's Skill Check
  - Other things probably.

That is the bardic/rougish homeworld.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Typing
# ---
from typing import Optional, Set, Type, Union
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
from veredi.game.ecs.component      import ComponentManager
from veredi.game.ecs.entity         import EntityManager

from veredi.game.ecs.const          import (SystemTick,
                                            SystemPriority)

from veredi.game.ecs.base.identity  import ComponentId
from veredi.game.ecs.base.system    import System
from veredi.game.ecs.base.component import Component

# Everything needed to participate in command registration.
from veredi.input.command.reg       import (CommandRegistrationBroadcast,
                                            CommandRegisterReply,
                                            CommandPermission,
                                            CommandArgType,
                                            CommandStatus)
from veredi.math.parser             import MathTree
from veredi.input.context           import InputUserContext

# Skill-Related Events & Components
from .event                         import SkillRequest, SkillResult
from .component                     import SkillComponent
# Eventually: AbilityComponent, others?


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'rules', 'd20', 'skill', 'system')
class SkillSystem(System):

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
            # For ticking, we need the ones with SkillComponents.
            # They're the ones with Skills.
            # Obviously.
            SkillComponent
        ]

        # Just the normal one, for now.
        self._ticks: SystemTick = SystemTick.STANDARD

        # ---
        # Context Stuff
        # ---
        config = ConfigContext.config(context)  # Configuration obj
        if not config:
            raise ConfigContext.exception(
                context,
                None,
                "Cannot configure {} without a Configuration in the "
                "supplied context.",
                self.__class__.__name__)

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

        # SkillSystem subs to:
        # - CommandRegistrationBroadcast
        # - SkillRequests
        self._manager.event.subscribe(CommandRegistrationBroadcast,
                                      self.event_cmd_reg)
        self._manager.event.subscribe(SkillRequest,
                                      self.event_skill_req)

        return self._health_check()

    def event_cmd_reg(self, event: CommandRegistrationBroadcast) -> None:
        '''
        Skill thingy requested to happen; please resolve.
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

        skill_check = CommandRegisterReply(event,
                                           'skill',
                                           CommandPermission.COMPONENT,
                                           self.trigger_skill_req,
                                           help='roll a skill check')
        skill_check.permission_components(SkillComponent)
        skill_check.add_arg('skill name', CommandArgType.VARIABLE)
        skill_check.add_arg('additional math', CommandArgType.MATH,
                            optional=True)

        self._event_notify(skill_check)

    def trigger_skill_req(self,
                          math: MathTree,
                          context: Optional[InputUserContext] = None
                          ) -> CommandStatus:
        '''
        Skill Check command happened. Package it up into a SkillRequest event
        for us to process later.
        '''
        # Doctor checkup.
        if not self._healthy():
            self._health_meter_event = self._health_log(
                self._health_meter_event,
                log.Level.WARNING,
                "HEALTH({}): Dropping skill request trigger '{}', '{}' "
                "- our system health isn't good enough to process.",
                self.health, math,
                context=context)
            return

        # �-TODO-� [2020-06-12]: this
        raise NotImplementedError

    def event_skill_req(self, event: SkillRequest) -> None:
        '''
        Skill thingy requested to happen; please resolve.
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

        eid = event.id
        entity = self._manager.entity.get(eid)
        if not entity:
            # Entity disappeared, and that's ok.
            log.info("Dropping event {} - no entity for its id: {}",
                     event, eid,
                     context=event.context)
            # §-TODO-§ [2020-06-04]: a health thing? e.g.
            # self._health_update(EntityDNE)
            return
        component = entity.get(SkillComponent)
        if not component:
            # Component disappeared, and that's ok.
            log.info("Dropping event {} - no SkillComponent for "
                     "it on entity: {}",
                     event, entity,
                     context=event.context)
            # §-TODO-§ [2020-06-04]: a health thing? e.g.
            # self._health_update(ComponentDNE)
            return

        amount = component.total(event.skill)
        log.debug("Event {} - {} total is: {}",
                  event, event.skill, amount,
                  context=event.context)

        # Have EventManager create and fire off event for whoever wants the
        # next step.
        if component.id != ComponentId.INVALID:
            next_event = SkillResult(event.id, event.type, event.context,
                                     component_id=component.id,
                                     skill=event.skill, amount=amount)
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
        Generic tick function. We do the same thing every tick state we process
        so do it all here.
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

        for entity in self._wanted_entities(tick, time_mgr,
                                            component_mgr, entity_mgr):
            # Check if entity in turn order has a (skill) action queued up.
            # Also make sure to check if entity/component still exist.
            if not entity:
                continue
            component = component_mgr.get(SkillComponent)
            if not component or not component.has_action:
                continue

            action = component.dequeue
            log.debug("Entity {}, Comp {} has skill action: {}",
                      entity, component, action)

            # Check turn order?
            # Would that be, like...
            #   - engine.time_flow()?
            #   - What does PF2/Starfinder call it? Like the combat vs
            #     short-term vs long-term 'things are happening' modes...

            # process action
            print('todo: a skill thingy', action)

        return self._health_check()
