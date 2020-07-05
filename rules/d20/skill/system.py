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
from typing import (TYPE_CHECKING,
                    Optional, Union, Type, Set, Tuple)
from veredi.base.null import Null, Nullable
if TYPE_CHECKING:
    from decimal import Decimal
    from veredi.base.context     import VerediContext
    from veredi.game.ecs.manager import EcsManager


# ---
# Code
# ---
from veredi.logger                  import log
from veredi.base.const              import VerediHealth
from veredi.base                    import dotted
from veredi.data                    import background
from veredi.data.config.registry    import register
from veredi.data.codec.adapter      import definition
from veredi.data.milieu             import ValueMilieu

# Game / ECS Stuff
from veredi.game.ecs.event          import EventManager
from veredi.game.ecs.time           import TimeManager
from veredi.game.ecs.component      import ComponentManager
from veredi.game.ecs.entity         import EntityManager

from veredi.game.ecs.const          import (SystemTick,
                                            SystemPriority)

from veredi.game.ecs.base.identity  import ComponentId, EntityId
from veredi.game.ecs.base.system    import System
from veredi.game.ecs.base.component import Component

# Everything needed to participate in command registration.
from veredi.input.command.reg       import (CommandRegistrationBroadcast,
                                            CommandRegisterReply,
                                            CommandPermission,
                                            CommandArgType,
                                            CommandStatus)
from veredi.math.parser             import MathTree
from veredi.math.system             import MathSystem
from veredi.math.event              import MathOutputEvent
from veredi.input.context           import InputContext

# Skill-Related Events & Components
from .event                         import SkillRequest, SkillResult
from .component                     import SkillComponent
# Eventually: AbilityComponent, others?


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# §-TODO-§ [2020-07-04]: Make this, AbilitySystem, CombatSystem into subclasses
# of a new base class RuleSystem? Put the definition stuff in there?
# Also the 'fill' stuff - or all the stuff in the 'Data Processing' section.


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'rules', 'd20', 'skill', 'system')
class SkillSystem(System):

    def _configure(self, context: 'VerediContext') -> None:
        '''
        Make our stuff from context/config data.
        '''
        self._component_type: Type[Component] = SkillComponent
        '''Set our component type for the get() helper.'''

        # ---
        # Health Stuff
        # ---
        self._required_managers:    Optional[Set[Type[EcsManager]]] = {
            TimeManager,
            EventManager,
            ComponentManager,
            EntityManager
        }
        self._health_meter_update:  Optional['Decimal'] = None
        self._health_meter_event:   Optional['Decimal'] = None

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

        # Ask config for our definition to be deserialized and given to us
        # right now.
        self._skill_defs = definition.Definition(
            definition.DocType.DEF_SYSTEM,
            config.definition(self.dotted, context))

    @property
    def dotted(self) -> str:
        # self._DOTTED magically provided by @register
        return self._DOTTED

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
        if not self._health_ok_event(event):
            return

        skill_check = CommandRegisterReply(event,
                                           self.dotted,
                                           'skill',
                                           CommandPermission.COMPONENT,
                                           self.command_skill,
                                           description='roll a skill check')
        skill_check.set_permission_components(SkillComponent)
        skill_check.add_arg('skill name', CommandArgType.VARIABLE)
        skill_check.add_arg('additional math', CommandArgType.MATH,
                            optional=True)

        self._event_notify(skill_check)

    def command_skill(self,
                      math: MathTree,
                      context: Optional[InputContext] = None
                      ) -> CommandStatus:
        '''
        Skill Check command happened. Package it up into a SkillRequest event
        for us to process later.
        '''
        # Doctor checkup.
        if not self._health_ok_msg("Command ignored due to bad health.",
                                   context=context):
            return CommandStatus.system_health(context)

        eid = InputContext.source_id(context)
        entity, component = self._log_get_both(
            eid,
            SkillComponent,
            context=context,
            preface="Dropping 'skill' command - ")
        if not entity or not component:
            return CommandStatus.does_not_exist(eid,
                                                entity,
                                                component,
                                                SkillComponent,
                                                context)

        # Ok... now just bundle up off to MathSystem's care.
        self._manager.system.get(MathSystem).command(
            math,
            self._skill_defs.canonical,
            self._query,
            MathOutputEvent(entity.id, entity.type_id,
                            context,
                            math,
                            InputContext.input_id(context)),
            context)

        # # Get skill totals for each var that's a skill name.
        # found = False
        # for var in math.each_var():
        #     if self.is_skill(var.name):
        #         found = True
        #         var.value = component.total(var.name)

        # if not found:
        #     return CommandStatus.no_claimed_inputs('skill names')

        return CommandStatus.successful(context)

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

        entity, component = self._log_get_both(event.id,
                                               SkillComponent,
                                               event=event)
        if not entity or not component:
            # Entity or component disappeared, and that's ok.
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

    # -------------------------------------------------------------------------
    # Data Processing
    # -------------------------------------------------------------------------

    def _query(self,
               skill: str,
               context: 'VerediContext') -> Nullable[ValueMilieu]:
        '''
        Takes `skill` (should be canonical already) string and finds
        value/result to fill in from entity's SkillComponent.

        Callers should do checks/logs on entity and component if they want more
        info about missing ent/comp. This just uses Null's cascade to safely
        skip those checks.
        '''
        eid = InputContext.source_id(context)

        # We'll use Null(). Callers should do checks/logs if they want more
        # info about missing ent/comp.
        entity, component = self._log_get_both(eid,
                                               SkillComponent,
                                               context=context)
        if not entity or not component:
            return Null()

        result = self._query_value(component, skill)
        log.debug("'{}' result is: {}",
                  skill, result,
                  context=context)

        return result

    def _query_value(self,
                     component: SkillComponent,
                     skill: Union[str, Tuple[str, str]]
                     ) -> ValueMilieu:
        '''
        `skill` string must be canonicalized. We'll get it from
        the component.

        Returns component query result. Also returns the canonicalized
        `skill` str, in case you need to call back into here for e.g.:
          _query_value(component, 'str.mod')
            -> '(${this.score} - 10) // 2', 'strength.modifier'
          _query_value(component,
                       ('this.score', 'strength.modifier'))
            -> (20, 'strength.score')
        '''
        if isinstance(skill, tuple):
            return self._query_this(component, *skill)

        skill = self._skill_defs.canonical(skill)
        return self._query_split(component, *dotted.split(skill))

    def _query_this(self,
                    component: SkillComponent,
                    skill: str,
                    milieu: str) -> ValueMilieu:
        '''
        Canonicalizes `skill` string, then gets it from the component using
        'milieu' if more information about where the `skill` string is from
        is needed. E.g.:

          _query_value(component,
                      'this.score',
                      'strength.modifier')
            -> (20, 'strength.score')

        In that case, 'this' needs to be turned into 'strength' and the
        `milieu` is needed for that to happen.

        ...I would have called it 'context' but that's already in heavy use, so
        'milieu'.
          "The physical or social setting in which something occurs
          or develops."
        Close enough?
        '''
        skill = self.canonical(skill)
        split_name = dotted.this(skill, milieu)
        return self._query_split(component, *split_name)

    def _query_split(self,
                     component: SkillComponent,
                     *skill: str) -> ValueMilieu:
        '''
        `skill` args must have been canonicalized.

        Gets `skill` from the component. Returns value and dotted
        skill string. E.g.:

          _query_split(component,
                       'strength',
                       'score')
            -> (20, 'strength.score')
        '''
        return ValueMilieu(component.query(*skill),
                           dotted.join(*skill))
