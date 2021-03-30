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
                    Optional, Union, Type, Set)
if TYPE_CHECKING:
    from decimal import Decimal
    from veredi.base.context     import VerediContext
    from veredi.game.ecs.manager import EcsManager


# ---
# Code
# ---
from veredi.logs                        import log
from veredi.base.const                  import VerediHealth
from veredi.base.strings                import label
from veredi.data                        import background

# Game / ECS Stuff
from veredi.game.ecs.event              import EventManager
from veredi.game.ecs.time               import TimeManager
from veredi.game.ecs.component          import ComponentManager
from veredi.game.ecs.entity             import EntityManager

from veredi.game.ecs.const              import (SystemTick,
                                                SystemPriority)

from veredi.game.ecs.base.identity      import ComponentId
from veredi.game.ecs.base.component     import Component
from veredi.rules.d20.system            import D20RulesSystem

# Everything needed to participate in command registration.
from veredi.interface.input.command.reg import (CommandRegistrationBroadcast,
                                                CommandRegisterReply,
                                                CommandPermission,
                                                CommandArgType,
                                                CommandStatus)
from veredi.math.parser                 import MathTree
from veredi.math.system                 import MathSystem
from veredi.interface.output.event      import Recipient
from veredi.math.event                  import MathOutputEvent
from veredi.interface.input.context     import InputContext

# Skill-Related Events & Components
from .event                             import SkillRequest, SkillResult
from .component                         import SkillComponent
# Eventually: AbilityComponent, others?


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO [2020-07-04]: Make this, AbilitySystem, CombatSystem into subclasses
# of a new base class RuleSystem? Put the definition stuff in there?
# Also the 'fill' stuff - or all the stuff in the 'Data Processing' section.


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class SkillSystem(D20RulesSystem):

    def _configure(self, context: 'VerediContext') -> None:
        '''
        Make our stuff from context/config data.
        '''
        self._component_type: Type[Component] = SkillComponent

        super()._configure(context)
        config = background.config.config(self.__class__.__name__,
                                          self.dotted(),
                                          context)
        self._config_rules_def(context, config, 'skill')

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

    @classmethod
    def dotted(klass: 'SkillSystem') -> label.DotStr:
        return 'veredi.rules.d20.pf2.skill.system'

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
        health = super()._subscribe()
        self._manager.event.subscribe(SkillRequest,
                                      self.event_skill_req)

        return health.update(VerediHealth.HEALTHY)

    def event_cmd_reg(self, event: CommandRegistrationBroadcast) -> None:
        '''
        Skill thingy requested to happen; please resolve.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
            return

        skill_check = CommandRegisterReply(event,
                                           self.dotted(),
                                           'skill',
                                           CommandPermission.COMPONENT,
                                           self.command_skill,
                                           description='roll a skill check')
        skill_check.set_permission_components(SkillComponent)
        skill_check.add_arg('skill name', CommandArgType.VARIABLE)
        skill_check.add_arg('additional math', CommandArgType.MATH,
                            optional=True)

        # TODO [2020-07-13]: do I want each skill as sub-command?
        # # for each skill in def, define alias command
        # for skill in self._rule_defs['skill']:
        #     canon = self._rule_defs.canonical(skill, None)
        #     cmd.add_alias(skill, 'skill ' + canon)

        # for skill in self._rule_defs['alias']:
        #     canon = self._rule_defs.canonical(skill, None,
        #                                       no_error_log=True,
        #                                       raise_error=False)
        #     if canon:
        #         cmd.add_alias(skill, 'skill ' + canon)

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
        entity, component = self._manager.get_with_log(
            f'{self.__class__.__name__}.command_skill',
            eid,
            self._component_type,
            context=context,
            preface="Dropping 'skill' command - ")
        if not entity or not component:
            return CommandStatus.does_not_exist(eid,
                                                entity,
                                                component,
                                                self._component_type,
                                                context)

        # Ok... now just bundle up off to MathSystem's care.
        self._manager.system.get(MathSystem).command(
            math,
            self._rule_defs.canonical,
            self._query,
            MathOutputEvent(entity.id, entity.type_id,
                            math, context,
                            InputContext.input_id(context),
                            # TODO [2020-07-11]: a proper output type...
                            Recipient.BROADCAST),
            context)

        return CommandStatus.successful(context)

    def event_skill_req(self, event: SkillRequest) -> None:
        '''
        Skill thingy requested to happen; please resolve.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
            return

        entity, component = self._manager.get_with_log(
            f'{self.__class__.__name__}.command_skill',
            event.id,
            self._component_type,
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

    def _update(self) -> VerediHealth:
        '''
        SystemTick.STANDARD tick function.
        '''
        # Doctor checkup.
        if not self._health_ok_tick(SystemTick.STANDARD):
            return self.health

        for entity in self._wanted_entities(SystemTick.STANDARD):
            # Check if entity in turn order has a (skill) action queued up.
            # Also make sure to check if entity/component still exist.
            if not entity:
                continue
            component = self.manager.component.get(self._component_type)
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

        return self._health_check(SystemTick.STANDARD)
