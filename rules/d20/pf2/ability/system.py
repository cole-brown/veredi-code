# coding: utf-8

'''
D20 Ability System for the Game.

Handles:
  - Ability stuff. Strength, strength modifiers, strength checks...
  - Just strength.

Open doors the aggressive way.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Set, Type, Union)
if TYPE_CHECKING:
    from veredi.base.context import VerediContext
    from ..ecs.manager       import EcsManager


from veredi.logger                      import log
from veredi.base.const                  import VerediHealth
from veredi.data                        import background
from veredi.data.config.registry        import register

# Game / ECS Stuff
from veredi.game.ecs.event              import EventManager
from veredi.game.ecs.time               import TimeManager
from veredi.game.ecs.component          import ComponentManager
from veredi.game.ecs.entity             import EntityManager

from veredi.game.ecs.const              import (SystemTick,
                                                SystemPriority)

from veredi.game.ecs.base.component     import Component

from veredi.rules.d20.system            import D20RulesSystem

# Commands
from veredi.interface.input.command.reg import (CommandRegistrationBroadcast,
                                                CommandRegisterReply,
                                                CommandPermission,
                                                CommandArgType,
                                                CommandStatus)
from veredi.interface.input.context     import InputContext
from veredi.math.parser                 import MathTree
from veredi.math.system                 import MathSystem
from veredi.interface.output.event      import OutputType
from veredi.math.event                  import MathOutputEvent

# Ability-Related Events & Components
from .component import (
    AbilityComponent,
)
from .event import (
    AbilityRequest,
    AbilityResult,
)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'rules', 'd20', 'pf2', 'ability', 'system')
class AbilitySystem(D20RulesSystem):

    def _configure(self, context: 'VerediContext') -> None:
        '''
        Make our stuff from context/config data.
        '''
        self._component_type: Type[Component] = AbilityComponent

        super()._configure(context)
        self._config_rules_def(context,
                               background.config.config,
                               'ability')

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
        # For ticking, we only need the ones with AbilityComponents.
        self._components_req: Optional[Set[Type[Component]]] = [
            AbilityComponent,
        ]

        # Ability uses several ticks for better responsiveness?
        #   PRE, STADARD, POST - Might should just go to standard?
        self._ticks: SystemTick = (SystemTick.PRE
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
        # Medium so combat can do requests if it needs to before we go?
        return SystemPriority.MEDIUM

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def subscribe(self, event_manager: 'EventManager') -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        super().subscribe(event_manager)

        self._manager.event.subscribe(AbilityRequest,
                                      self.event_ability_req)

        return self._health_check()

    def event_cmd_reg(self, event: CommandRegistrationBroadcast) -> None:
        '''
        Set up all our ability commands.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
            return

        # ---
        # General Command
        # ---
        cmd = CommandRegisterReply(event,
                                   self.dotted,
                                   'ability',
                                   CommandPermission.COMPONENT,
                                   self.command_ability,
                                   description='Ability check.')
        cmd.set_permission_components(AbilityComponent)
        cmd.add_arg('ability name', CommandArgType.VARIABLE)
        cmd.add_arg('additional math', CommandArgType.MATH,
                    optional=True)

        # ---
        # Alias Commands
        # ---
        # for each ability in def, define alias command
        for ability in self._rule_defs['ability']:
            canon = self._rule_defs.canonical(ability, None)
            cmd.add_alias(ability, 'ability ' + canon)

        for ability in self._rule_defs['alias']:
            canon = self._rule_defs.canonical(ability, None,
                                              no_error_log=True,
                                              raise_error=False)
            if canon:
                cmd.add_alias(ability, 'ability ' + canon)

        # ---
        # Alright, done. Send it!
        # ---
        self._event_notify(cmd)

    def command_ability(self,
                        math: MathTree,
                        context: Optional[InputContext] = None
                        ) -> CommandStatus:
        '''
        Turn command into Ability Request event for us to process later.
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
            preface="Dropping 'ability' command - ")
        if not entity or not component:
            return CommandStatus.does_not_exist(eid,
                                                entity,
                                                component,
                                                self._component_type,
                                                context)

        # Ok... now just bundle up off to MathSystem's care with our callbacks.
        self._manager.system.get(MathSystem).command(
            math,
            self._rule_defs.canonical,
            self._query,
            MathOutputEvent(entity.id, entity.type_id,
                            context,
                            InputContext.input_id(context),
                            # TODO [2020-07-11]: a proper output type...
                            OutputType.BROADCAST,
                            math),
            context)

        return CommandStatus.successful(context)

    def event_ability_req(self, event: AbilityRequest) -> None:
        '''
        Ability check - please do the thing.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
            return

        entity, component = self._log_get_both(event.id,
                                               self._component_type,
                                               event=event)
        if not entity or not component:
            # Entity or component disappeared, and that's ok.
            return

        result = self._query(event.id,
                             event.ability,
                             event.context)

        # Have EventManager create and fire off event for whoever wants the
        # next step.
        next_event = AbilityResult(event, result)
        self._event_notify(next_event)