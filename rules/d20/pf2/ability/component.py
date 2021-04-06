# coding: utf-8

'''
AbilityComponent
  - abilities and abilility modifiers
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Any, MutableMapping, Dict)
from veredi.base.null import Null, Nullable
if TYPE_CHECKING:
    from veredi.data.config.context  import ConfigContext

from veredi.logs                     import log
from veredi.base.strings             import label
from veredi.game.data.component      import DataComponent
from veredi.game.interface.component import queue

from .event                          import AbilityEvent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Component
# -----------------------------------------------------------------------------

class AbilityComponent(DataComponent, queue.IQueueSingle[AbilityEvent],
                       name_dotted='veredi.rules.d20.pf2.ability.component',
                       name_string='component.ability'):
    '''
    Component with ability numbers, ability action queue, probably
    other stuff...
    '''

    # TEMP: a way to verify we got something, and to verify we're using the
    # verify() function...
    _REQ_KEYS = {
        'ability': {
            'strength':     ['score', 'modifier'],
            'dexterity':    ['score', 'modifier'],
            'constitution': ['score', 'modifier'],
            'intelligence': ['score', 'modifier'],
            'wisdom':       ['score', 'modifier'],
            'charisma':     ['score', 'modifier'],
        }
    }

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''
        Allows components to grab, from the context/config, anything that
        they need to set up themselves.
        '''
        # ---
        # Members
        # ---

        # Set up our queue.
        self._init_queue()

        # ---
        # Context Init Section
        # ---
        # Nothing at the moment.

    def _from_data(self, data: MutableMapping[str, Any] = None) -> None:
        '''
        Configure our data into whatever it needs to be for runtime.
        '''
        actual_data = data['ability']
        super()._from_data(actual_data)

    # -------------------------------------------------------------------------
    # Queue Interface
    # -------------------------------------------------------------------------

    # @property
    # def is_queued(self) -> bool:
    #     ...
    # @property
    # def queued(self) -> Nullable[QType]:
    #     ...
    # @property
    # def dequeue(self) -> QType:
    #     ...
    # @queued.setter
    # def enqueue(self, value: NullNoneOr[QType]) -> None:
    #     ...

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def score(self, ability: str) -> int:
        '''
        Get amount of ability. We have no bonuses right now so this is
        just 'score'.

        TODO: 'innate'? base? base plus 'permanent' from e.g. magic belts
        TODO: well. TODO all the bonus tags.
        '''
        return self._score(ability)

    def modifier(self, ability: str) -> int:
        '''
        Get modifier amount of ability.
        '''
        return self._modifier(ability)

    # -------------------------------------------------------------------------
    # Ability Stuff
    # -------------------------------------------------------------------------

    def _ability(self, name: str) -> Dict[str, Any]:
        '''
        Get `name`'s entry in our persistent data or null.
        '''
        entry = self.persistent.get(name, Null())
        log.debug("ABILITY: {} entry for {}: {}",
                  self.__class__.__name__, name, entry)
        return entry

    def _score(self, name: str) -> int:
        '''
        Get ability score integer for `name` ability.
        '''
        return self._ability(name).get('score', 0)

    def _modifier(self, name: str) -> Nullable[str]:
        '''
        Get ability modifier math string for `name` ability.
        '''
        return self._ability(name).get('modifier', Null())
