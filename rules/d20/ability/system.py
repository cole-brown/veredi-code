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
                    Optional, Set, Type, Union, Tuple)
if TYPE_CHECKING:
    from veredi.base.context import VerediContext
    from ..ecs.manager       import EcsManager


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

from veredi.game.ecs.base.system    import System
from veredi.game.ecs.base.component import Component

# Commands
from veredi.input.command.reg       import (CommandRegistrationBroadcast,
                                            CommandRegisterReply,
                                            CommandPermission,
                                            CommandArgType,
                                            CommandStatus)
from veredi.math.parser             import MathTree
from veredi.input.context           import InputContext

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

@register('veredi', 'rules', 'd20', 'ability', 'system')
class AbilitySystem(System):

    def _configure(self, context: 'VerediContext') -> None:
        '''
        Make our stuff from context/config data.
        '''

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
        self._ability_defs = definition.Definition(
            definition.DocType.DEF_SYSTEM,
            config.definition(self.name, context))

    @property
    def name(self) -> str:
        '''
        The 'dotted string' name this system has. Probably what they used to
        register.
        '''
        return 'veredi.rules.d20.ability.system'

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

        # AbilitySystem subs to:
        # - CommandRegistrationBroadcast - For commands.
        # - AbilityRequestEvent
        self._manager.event.subscribe(CommandRegistrationBroadcast,
                                      self.event_cmd_reg)
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
                                   self.name,
                                   'ability',
                                   CommandPermission.COMPONENT,
                                   self.trigger_ability_req,
                                   description='Ability check.')
        cmd.set_permission_components(AbilityComponent)
        cmd.add_arg('ability name', CommandArgType.STRING)
        self._event_notify(cmd)

        # ---
        # Alias Commands
        # ---
        # for each ability in def, define alias command
        for ability in self._ability_defs['ability']:
            print(self.name, 'cmd reg:', ability)
            # cmd = CommandRegisterReply(event,
            #                            self.name,

        for ability in self._ability_defs['alias']:
            print(self.name, 'cmd reg:', ability)
            # cmd = CommandRegisterReply(event,
            #                            self.name,

    def trigger_ability_req(self,
                            math: MathTree,
                            context: Optional[InputContext] = None
                            ) -> CommandStatus:
        '''
        Turn command into Ability Request event for us to process later.
        '''
        # Doctor checkup.
        if not self._health_ok_msg("Command ignored due to bad health.",
                                   context=context):
            return

        eid = InputContext.source_id(context)
        entity = self._manager.entity.get(eid)
        component = entity.get(AbilityComponent)
        if not entity or not component:
            log.info("Dropping 'skill' command - no entity or comp "
                     "for its id: {}",
                     eid,
                     context=context)

    def event_ability_req(self, event: AbilityRequest) -> None:
        '''
        Ability check - please do the thing.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
            return

        eid = event.id
        entity = self._manager.entity.get(eid)
        if not entity:
            # Entity disappeared, and that's ok.
            log.info("Dropping event {} - no entity for its id: {}",
                     event, eid,
                     context=event.context)
            # TODO [2020-06-04]: a health thing? e.g.
            # self._health_update(EntityDNE)
            return
        component = entity.get(AbilityComponent)
        if not component:
            # Component disappeared, and that's ok.
            log.info("Dropping event {} - no AbilityComponent for "
                     "it on entity: {}",
                     event, entity,
                     context=event.context)
            # TODO [2020-06-04]: a health thing? e.g.
            # self._health_update(ComponentDNE)
            return

        canon = self.canonical(event.ability)
        result = self._get_value(component, canon)
        log.debug("Event {} - '{}'->'{}' result is: {}",
                  event, event.ability, canon, result,
                  context=event.context)

        # Have EventManager create and fire off event for whoever wants the
        # next step.
        next_event = AbilityResult(event, result)
        self._event_notify(next_event)

    # -------------------------------------------------------------------------
    # Data Processing
    # -------------------------------------------------------------------------

    def canonical(self, string: str) -> str:
        '''
        Takes `string` and tries to normalize it to canonical value.
        e.g.:
          'strength' -> 'strength.score'
          'Strength' -> 'strength.score'
          'str.mod' -> 'strength.modifier'
        '''
        # 1) Make sure it's long enough?
        # TODO: could also check for final element being an expected leaf name?
        names = dotted.split(string)
        if len(names) < 2:
            names.append(self._ability_defs['default']['key'])

        canon = []
        for name in names:
            if name in self._ability_defs['alias']:
                canon.append(self._ability_defs['alias'][name])
            else:
                canon.append(name)

        return dotted.join(*canon)

    def _get_value(self,
                   component: AbilityComponent,
                   ability: Union[str, Tuple[str, str]]
                   ) -> ValueMilieu:
        '''
        `ability` string must be canonicalized. We'll get it from
        the component.

        Returns component query result. Also returns the canonicalized
        `ability` str, in case you need to call back into here for e.g.:
          _get_value(component, 'str.mod')
            -> '(${this.score} - 10) // 2', 'strength.modifier'
          _get_value(component,
                    ('this.score', 'strength.modifier'))
            -> (20, 'strength.score')
        '''
        if isinstance(ability, tuple):
            return self._get_this(component, *ability)

        ability = self.canonical(ability)
        return self._get_split(component, *dotted.split(ability))

    def _get_this(self,
                  component: AbilityComponent,
                  ability: str,
                  milieu: str) -> ValueMilieu:
        '''
        Canonicalizes `ability` string, then gets it from the component using
        'milieu' if more information about where the `ability` string is from
        is needed. E.g.:

          _get_value(component,
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
        ability = self.canonical(ability)
        split_name = dotted.this(ability, milieu)
        return self._get_split(component, *split_name)

    def _get_split(self,
                   component: AbilityComponent,
                   *ability: str) -> ValueMilieu:
        '''
        `ability` args must have been canonicalized.

        Gets `ability` from the component. Returns value and dotted
        ability string. E.g.:

          _get_split(component,
                     'strength',
                     'score')
            -> (20, 'strength.score')
        '''
        return ValueMilieu(component.query(*ability),
                           dotted.join(*ability))
