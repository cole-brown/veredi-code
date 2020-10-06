# coding: utf-8

'''
D20 Combat System for the Game.

Handles:
  - Combat events like: Attack, Damage, etc.
  - Other things probably.

That is the nexus of punching people in the face.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Set, Type, Union)
if TYPE_CHECKING:
    from decimal             import Decimal
    from veredi.base.context import VerediContext
    from veredi.game.ecs.manager       import EcsManager

from veredi.logger                      import log
from veredi.base.const                  import VerediHealth
from veredi.data                        import background
from veredi.data.config.registry        import register

# Game / ECS Stuff
from veredi.game.ecs.event                        import EventManager
from veredi.game.ecs.time                         import TimeManager
from veredi.game.ecs.component                    import ComponentManager
from veredi.game.ecs.entity                       import EntityManager
from veredi.game.ecs.base.component               import Component

from veredi.game.ecs.const                        import (SystemTick,
                                                          SystemPriority)

from veredi.rules.d20.system                           import D20RulesSystem

# Commands
from veredi.interface.input.command.reg import (CommandRegistrationBroadcast,
                                                CommandRegisterReply,
                                                CommandPermission,
                                                CommandArgType,
                                                CommandStatus)
from veredi.math.parser                 import MathTree
from veredi.interface.input.context     import InputContext

# Combat-Related Events & Components
from .component import (
    AttackComponent,
    DefenseComponent,
)
from .event import (
    AttackRequest,
    AttackResult,
    DefenseRequest,
    DefenseResult,
)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'rules', 'd20', 'pf2', 'combat', 'system')
class CombatSystem(D20RulesSystem):

    def _configure(self, context: 'VerediContext') -> None:
        '''
        Make our stuff from context/config data.
        '''
        self._component_type: Type[Component] = AttackComponent
        '''Set our component type for the get() helper. We have two, so...'''

        super()._configure(context)
        self._config_rules_def(context,
                               background.config.config,
                               'combat')

        # ---
        # Health Stuff
        # ---
        self._required_managers:    Optional[Set[Type['EcsManager']]] = {
            TimeManager,
            EventManager,
            ComponentManager,
            EntityManager
        }

        # ---
        # Ticking Stuff
        # ---
        # For ticking, we need the ones with AttackComponents OR
        # DefenseComponents (or both), so set to 'any' here...
        self._components_req: Optional[Set[Type[Component]]] = [
            AttackComponent,
            DefenseComponent,
        ]
        self._components_req_all = False

        # Combat uses several ticks for different things?
        #   TIME - Any combat event that has a delayed start
        #          (e.g. full round casting time).
        #   PRE  - Any combat numbers that need recalculated each tick?
        #          (But other systems should do most of that (BuffSystem?
        #          StatsSystem?)
        #   STADARD - Do the bulk of our work here.
        #   POST - Any 'at the end of your turn' happens here?
        self._ticks: SystemTick = (SystemTick.TIME
                                   | SystemTick.PRE
                                   | SystemTick.STANDARD
                                   | SystemTick.POST)

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
        # Could do a lower priority. Guessing at HIGH because we want to get
        # who's dead out of the way first.
        return SystemPriority.HIGH

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def _subscribe(self) -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        health = super()._subscribe()

        # CombatSystem subs to:
        # - AttackRequestEvent
        #   - Attacker wants to start an attack.
        # - DefenseRequestEvent
        #   - Defender wants to start a... defense.
        self._manager.event.subscribe(AttackRequest,
                                      self.event_attack_request)
        self._manager.event.subscribe(DefenseRequest,
                                      self.event_defense_request)

        return health.update(VerediHealth.HEALTHY)

    def event_cmd_reg(self, event: CommandRegistrationBroadcast) -> None:
        '''
        Set up all our combat commands.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
            return

        cmd = CommandRegisterReply(event,
                                   self.dotted,
                                   'attack',
                                   CommandPermission.COMPONENT,
                                   self.command_attack,
                                   description='Attack an enemy.')
        cmd.set_permission_components(AttackComponent)
        cmd.add_arg('target', CommandArgType.CSV)
        cmd.add_arg('attack name', CommandArgType.VARIABLE)
        cmd.add_arg('additional math', CommandArgType.MATH,
                    optional=True)

        self._event_notify(cmd)

    def command_attack(self,
                       math: MathTree,
                       context: Optional[InputContext] = None
                       ) -> CommandStatus:
        '''
        Turn command into Attack Request event for us to process later.
        '''
        # Doctor checkup.
        if not self._health_ok_msg("Command ignored due to bad health.",
                                   context=context):
            return CommandStatus.system_health(context)

        eid = InputContext.source_id(context)
        entity, component = self._log_get_both(
            eid,
            self._component_type,
            context=context,
            preface="Dropping 'attack' command - ")
        if not entity or not component:
            return CommandStatus.entity_does_not_exist(eid,
                                                       entity,
                                                       component,
                                                       self._component_type,
                                                       context)

        # Don't process it yet! Need to queue it up for processing in the
        # correct place on the correct turn. Otherwise some values could be
        # wrong (e.g. buffs that show up/leave between now and then).

        # TODO: put this request in component's attack queue.
        # request = AttackRequestEvent(...)
        # component.queue(request)
        # Send request event out? Or CombatInfoEvent or something?

        print("Hello there! You want to attack!", math)
        return CommandStatus.successful(context)

    def event_attack_request(self, event: AttackRequest) -> None:
        '''
        Attack happened; please resolve.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
            return

        print("Hello there! You want to!", event)

        # TODO: Put in resolution queue on target for resolving on the proper
        # tick.

    def event_defense_request(self, event: DefenseRequest) -> None:
        '''
        Defense happened; please resolve.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
            return

        print("Hello there! You want to!", event)

        # TODO: Put in resolution queue on target for resolving on the proper
        # tick.

    # -------------------------------------------------------------------------
    # Game Update Loop/Tick Functions
    # -------------------------------------------------------------------------

    def _update_time(self,
                     time_manager:      TimeManager,
                     component_manager: ComponentManager,
                     entity_manager:    EntityManager) -> VerediHealth:
        '''
        First in Game update loop. Systems should use this rarely as the game
        time clock itself updates in this part of the loop.
        '''
        # Doctor checkup.
        if not self._health_ok_tick(SystemTick.TIME):
            return self.health

        tick = SystemTick.TIME
        print("TODO: THIS TICK!", tick)
        for entity in self._wanted_entities(tick, time_manager,
                                            component_manager, entity_manager):
            # Check if entity in turn order has a combat action queued up.
            # Also make sure to check if entity/component still exist.
            if not entity:
                continue
            component = entity.get(AttackComponent)
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



        # TODO [2020-05-26]: this

        # check turn order

        #     check if entity in turn order has a (combat) action queued up
        #     anywhere.

        #     process action

        # check for entities to add to turn order tracker

        return self._health_check(SystemTick.TIME)

    def _update_pre(self,
                    time_manager:      TimeManager,
                    component_manager: ComponentManager,
                    entity_manager:    EntityManager) -> VerediHealth:
        '''
        Pre-update. For any systems that need to squeeze in something just
        before actual tick.
        '''
        # Doctor checkup.
        if not self._health_ok_tick(SystemTick.PRE):
            return self.health

        tick = SystemTick.PRE
        print("TODO: THIS TICK!", tick)
        for entity in self._wanted_entities(tick, time_manager,
                                            component_manager, entity_manager):
            pass

    def _update(self,
                time_manager:      TimeManager,
                component_manager: ComponentManager,
                entity_manager:    EntityManager) -> VerediHealth:
        '''
        Normal/Standard upate. Basically everything should happen here.
        '''
        # Doctor checkup.
        if not self._health_ok_tick(SystemTick.STANDARD):
            return self.health

        tick = SystemTick.STANDARD
        print("TODO: THIS TICK!", tick)
        for entity in self._wanted_entities(tick, time_manager,
                                            component_manager, entity_manager):
            pass

    def _update_post(self,
                     time_manager:      TimeManager,
                     component_manager: ComponentManager,
                     entity_manager:    EntityManager) -> VerediHealth:
        '''
        Post-update. For any systems that need to squeeze in something just
        after actual tick.
        '''
        # Doctor checkup.
        if not self._health_ok_tick(SystemTick.POST):
            return self.health

        tick = SystemTick.POST
        print("TODO: THIS TICK!", tick)
        for entity in self._wanted_entities(tick, time_manager,
                                            component_manager, entity_manager):
            pass
