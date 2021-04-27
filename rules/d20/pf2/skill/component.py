# coding: utf-8

'''
Skills Component
  - A component that has all them skills you can roll in it.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Any, Mapping, MutableMapping, Dict)
if TYPE_CHECKING:
    from veredi.data.config.context import ConfigContext
    from .event                     import SkillEvent


from veredi.logs                     import log
from veredi.base.strings             import label
from veredi.game.interface.component import queue

from veredi.game.data.component      import DataComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class SkillComponent(DataComponent, queue.IQueueSingle['SkillEvent'],
                     name_dotted='veredi.rules.d20.pf2.skill.component',
                     name_string='skill.component'):
    '''
    Component with skill numbers, probably other stuff...
    '''

    # TODO [2020-06-04]: Some sort of rules config file where this sort
    # of thing would live?
    _CLASS_BONUS = 3

    # TEMP: a way to verify we got something, and to verify we're using the
    # verify() function...
    _REQ_KEYS = {
        # None of the actual skills are required, so...
        'skill': [],
    }

    # -------------------------------------------------------------------------
    # Init Stuff
    # -------------------------------------------------------------------------

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''
        Allows components to grab, from the context/config, anything that
        they need to set up themselves.
        '''
        # ---
        # Context Init Section
        # ---
        # Nothing at the moment.

        # ---
        # Misc Section
        # ---
        self._init_queue()

    def _from_data(self, data: MutableMapping[str, Any] = None) -> None:
        '''
        Configure our data into whatever it needs to be for runtime.
        '''
        actual_data = data['skill']
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

    def is_class(self, skill: str) -> bool:
        '''
        True/False for if `skill` is flagged as a class skill.
        '''
        entry = self._skill(skill)
        return self._is_class(entry)

    def bonus_class(self, skill: str) -> int:
        '''
        Get ranks invested in `skill`.
        '''
        entry = self._skill(skill)
        return self._bonus_class(entry)

    def ranks(self, skill: str) -> int:
        '''
        Get ranks invested in `skill`.
        '''
        entry = self._skill(skill)
        return self._ranks(entry)

    def total(self, skill: str) -> int:
        '''
        Get ranks invested in `skill`, apply class bonus if appropriate, add
        other bonuses from e.g.:
          - abilities
          - other things eventually probably
        '''
        entry = self._skill(skill)
        ranks = self._ranks(entry)
        klass = self._bonus_class(entry)
        # ... other things eventually probably
        return (ranks + klass)

    # -------------------------------------------------------------------------
    # Skill Stuff
    # -------------------------------------------------------------------------

    def _skill(self, name: str) -> Dict[str, Any]:
        '''
        Get `name`'s entry in our persistent data.
        '''
        entry = self.persistent.get(name, None)
        log.debug("SKILL: {} entry for {}: {}",
                  self.klass, name, entry)
        return entry

    def _is_class(self, entry: Mapping[str, Any]) -> bool:
        '''
        True/False for if `skill` is flagged as a class skill.
        '''
        return bool(entry.get('class', False))

    def _bonus_class(self, entry: Mapping[str, Any]) -> int:
        '''
        Get skill amount from class-skill bonus if applicable, else returns 0.
        '''
        bonus = 0
        if not self._is_class(entry):
            return bonus

        if self._ranks(entry) > 0:
            # TODO [2020-06-09]: d20 consts.py, or d20 const yaml config to
            # hold stuff like this magic number.
            bonus = 3
        return bonus

    def _ranks(self, entry: Mapping[str, Any]) -> int:
        '''
        Get ranks invested in `skill`.
        '''
        return entry.get('ranks', 0)
