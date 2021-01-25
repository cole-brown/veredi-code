# coding: utf-8

'''
A D20 Rules System Base Class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Type, Union, Tuple)
from veredi.base.null import Null, Nullable
if TYPE_CHECKING:
    from veredi.base.context import VerediContext
    from ..meeting           import Meeting

from abc import abstractmethod


from veredi.logger                         import log
from veredi.base.const                     import VerediHealth
from veredi.base                           import label
from veredi.data                           import background
from veredi.data.records                   import DocType, Definition, Saved
from veredi.data.repositiory.taxon         import LabelTaxon.
from veredi.data.milieu                    import ValueMilieu
from veredi.data.config.config             import Configuration

# Game / ECS Stuff
from veredi.game.ecs.event                 import EventManager

from veredi.game.ecs.base.identity         import EntityId, SystemId
from veredi.game.ecs.base.system           import System
from veredi.game.ecs.base.component        import Component

# Commands
from veredi.interface.input.command.reg    import CommandRegistrationBroadcast


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class D20RulesSystem(System):

    def __init__(self,
                 context:  Optional['VerediContext'],
                 sid:      SystemId,
                 managers: 'Meeting') -> None:
        self._component_type: Type[Component] = None
        '''Set our component type for the _query() helper.'''

        self._rule_defs_key:  str             = None
        '''Set our primary key for our rules definition.'''

        super().__init__(context, sid, managers)

    def _configure(self, context: 'VerediContext') -> None:
        '''
        Make our stuff from context/config data.
        '''
        # ---
        # Config Stuff
        # ---
        # config = background.config.config(self.__class__.__name__,
        #                                   self.dotted(),
        #                                   context)
        pass

    def _config_rules_def(self,
                          context:     'VerediContext',
                          config:      Configuration,
                          primary_key: str) -> None:
        '''
        Get rules definition file and configure it for use.
        '''
        # Ask config for our definition to be deserialized and given to us
        # right now.
        self._rule_defs = self._manager.data.load_definition(
            self.dotted(),
            DocType.definition.system,
            LabelTaxon(self.dotted()),
        )
        self._rule_defs.configure(primary_key)
        if not self._rule_defs:
            raise background.config.exception(
                context,
                "Cannot configure {} without its system definitions.",
                self.__class__.__name__)

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def _subscribe(self) -> VerediHealth:
        '''
        Default to subscribing to CommandRegistrationBroadcast. Most rules
        systems should have commands to invoke things related to them...
        '''
        self._manager.event.subscribe(CommandRegistrationBroadcast,
                                      self.event_cmd_reg)

        return VerediHealth.HEALTHY

    @abstractmethod
    def event_cmd_reg(self, event: CommandRegistrationBroadcast) -> None:
        '''
        Set up any commands that need registering here.
        '''
        ...

    # -------------------------------------------------------------------------
    # Data Processing
    # -------------------------------------------------------------------------

    def _query(self,
               entity_id: EntityId,
               entry: str,
               context: 'VerediContext') -> Nullable[ValueMilieu]:
        '''
        Get entry from entity's `self._component_type` and return it.

        Callers should do checks/logs on entity and component if they want more
        info about missing ent/comp. This just uses Null's cascade to safely
        skip those checks.
        '''
        # We'll use Null(). Callers should do checks/logs if they want more
        # info about missing ent/comp.
        entity, component = self._manager.get_with_log(
            f'{self.__class__.__name__}._query',
            entity_id,
            self._component_type,
            context=context)
        if not entity or not component:
            return Null()

        result = self._query_value(component, entry)
        log.debug("'{}' result is: {}",
                  entry, result,
                  context=context)

        return result

    def _query_value(self,
                     component: Component,
                     entry: Union[str, Tuple[str, str]]
                     ) -> ValueMilieu:
        '''
        `entry` string must be canonicalized. We'll get it from
        the component.

        Returns component query result. Also returns the canonicalized
        `entry` str, in case you need to call back into here for e.g.:
          _query_value(component, 'str.mod')
            -> '(${this.score} - 10) // 2', 'strength.modifier'
          _query_value(component,
                    ('this.score', 'strength.modifier'))
            -> (20, 'strength.score')
        '''
        if isinstance(entry, tuple):
            return self._query_this(component, *entry)

        entry = self._rule_defs.canonical(entry, None)
        return self._query_split(component, *label.regularize(entry))

    def _query_this(self,
                    component: Component,
                    entry: str,
                    milieu: str) -> ValueMilieu:
        '''
        Canonicalizes `entry` string, then gets it from the component using
        'milieu' if more information about where the `entry` string is from
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
        split_name = label.this(entry, milieu)
        entry = self._rule_defs.canonical(entry, milieu)
        return self._query_split(component, *split_name)

    def _query_split(self,
                     component: Component,
                     *entry: str) -> ValueMilieu:
        '''
        `entry` args must have been canonicalized.

        Gets `entry` from the component. Returns value and dotted
        entry string. E.g.:

          _query_split(component,
                       'strength',
                       'score')
            -> (20, 'strength.score')
        '''
        return ValueMilieu(component.query(*entry),
                           label.normalize(*entry))
