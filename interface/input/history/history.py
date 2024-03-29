# coding: utf-8

'''
Input Sub-system for input history.
  - Undo tree?
  - Assigning IDs to input events.
  - Holding on to inputs until outputs are ready?
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Typing
from typing import Optional, Any, Dict, List

# General Veredi Stuff
from veredi.data                         import background
from veredi.logs                         import log
from veredi.base.context                 import VerediContext
from veredi.base.strings                 import label
from veredi.base.strings.mixin           import NamesMixin

# Identity Stuff
from veredi.game.ecs.base.identity       import EntityId
from veredi.game.data.identity.component import IdentityComponent

# Game / ECS Stuff
from veredi.game.ecs.base.entity         import Entity
from veredi.game.ecs.meeting             import Meeting

# Our Stuff
from ..identity                          import InputId, InputIdGenerator
from ..command.args                      import CommandStatus
# from .component                        import InputComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# History Classes
# -----------------------------------------------------------------------------

class History:
    '''
    A thing that happend that should be saved.
    '''
    pass


class InputHistory(History):
    '''
    An Input that happened that should be saved.
    '''

    def __init__(self,
                 id: InputId,
                 input: Any,
                 entity: Entity) -> None:
        '''
        Create a history marker with an id and a... something. Input of some
        sort.
        '''
        self._id = id
        self._input = input

        self._eid = None
        self._name_entity = None
        self._name_group = None

        if entity:
            self._eid = entity.id
            ident = entity.get(IdentityComponent)
            if ident:
                self._name_entity = ident.designation
                self._name_group = ident.group
                self._name_controller = ident.controller
                # TODO: controller id? need something for serializing so we can
                # backlink later if needed?..

        # Filled in later.
        self._status = None

    # -------------------------------------------------------------------------
    # Properties - Getters/Setters
    # -------------------------------------------------------------------------

    @property
    def input_id(self) -> InputId:
        return self._id

    @property
    def entity_id(self) -> EntityId:
        return self._eid

    @property
    def status(self) -> CommandStatus:
        return self._status

    @status.setter
    def status(self, value: CommandStatus) -> None:
        self._status = value


# -----------------------------------------------------------------------------
# History Keeper - A Wholly Owned Sub-System of InputSystem, Inc.
# -----------------------------------------------------------------------------

class Historian(NamesMixin,
                name_dotted='veredi.interface.input.historian',
                name_string='historian'):
    '''
    TODO [2020-06-18]: This should be our undo history class. See:
      https://en.wikipedia.org/wiki/Undo
    for some options on how to implement using our Inputs/Commands as its undo
    history.
    '''

    def __init__(self, context: VerediContext) -> None:
        '''
        Initialize Historian.
        '''
        self._global:    List[InputHistory]                 = []
        self._by_input:  Dict[InputId, InputHistory]        = {}
        self._by_entity: Dict[EntityId, List[InputHistory]] = {}

        self._manager:   Meeting                = background.manager

        self._input_id:  InputIdGenerator       = InputId.generator(
            self._manager.time)

        # TODO [2020-06-21]: Write history to disk after x time?
        # TODO [2020-06-21]: Drop history from lists after y time?

    # -------------------------------------------------------------------------
    # History Getters
    # -------------------------------------------------------------------------

    def most_recent(self,
                    entity_id: EntityId) -> Optional[InputHistory]:
        '''
        Gets the most recent InputHistory of `entity_id`.
        '''
        full_history = self._by_entity.get(entity_id, [])
        # Return last if we have any, otherwise None.
        return full_history[-1] if full_history else None

    def history(self,
                entity_id: EntityId,
                amount:    int) -> List[InputHistory]:
        '''
        Get up to the `amount` number of `entity_id`'s most recent InputHistory
        items.
        '''
        full_history = self._by_entity.get(entity_id, [])
        if len(full_history) > amount:
            # Truncate down to the most recent number.
            returned_history = full_history[-amount:]
        else:
            returned_history = full_history

        return returned_history

    def get_id(self,
               entity: Entity,
               input_safe: str) -> InputId:
        '''
        Get an InputId from entity and input values.
        '''
        return self._input_id.next()

    def add_text(self,
                 entity: Entity,
                 input_safe: str) -> InputId:
        '''
        Add an input string that is about to be processed to the history.
        Mainly so that historian will assign it an InputId for ongoing use.
        '''
        if not entity:
            log.debug("No entity for input history; dropping: {}",
                      input_safe)
            return

        iid = self.get_id(entity, input_safe)
        entry = InputHistory(iid, input_safe, entity)

        # Add entry to global history and to entity's history.
        self._global.append(entry)
        self._by_entity.setdefault(entity.id, []).append(entry)
        self._by_input[iid] = entry

        return iid

    def update_executed(self,
                        input_id: InputId,
                        status: CommandStatus) -> None:
        '''
        Update a history entry. This history will now be for a command, which
        has been executed.

        If `status` indicates this was not successfully invoked, we will most
        likely throw away the history item since it resulted in nothing
        happening.
        '''
        # TODO [2020-06-21]: Mark for earlier throw away if failure?
        entry = self._by_input[input_id]
        entry.status = status

    def update_result(self,
                      id: InputId,
                      result: Any) -> None:
        '''
        This probably needs some actual commands... It should... save whatever
        actually happened for reference by users and for undoing/redoing.
        '''
        # TODO THIS
        raise NotImplementedError("todo")
