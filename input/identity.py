# coding: utf-8

'''
IDs for InputEvents, Commands, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Type

import uuid

from veredi.base.identity import SerializableId
from veredi.game.ecs.time import TimeManager


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Identification
# -----------------------------------------------------------------------------

class InputIdGenerator:
    '''
    Class that generates serializable UUIDs. Probably should switch to
    something provided by the Repository?
    '''

    def __init__(self,
                 id_class: Type['InputId'],
                 time_manager: TimeManager) -> None:
        self._id_class = id_class
        self._time = time_manager

    def next(self) -> 'InputId':
        return self._id_class(self._time, allow=True)


class InputId(SerializableId):
    '''
    ID for Input (events, commands, etc).

    Use SerializableId instead of MonotonicId so that input history can be
    serialized for cross-session history and undo.
    '''

    # TODO [2020-06-18]: Have each Repo be in charge of providing a
    # SerializableId type, maybe?

    # For now, we'll be a uuid, I guess
    #
    UUID_NAMESPACE = uuid.UUID('737c039c-a365-5b6e-9353-eca32695d300')
    '''
    The 'namespace' for our UUIDs will be static so we can
    reproducably/reliably generate a UUID. Generate by:
      uuid.uuid5(uuid.UUID(int=0), 'veredi.input.identity.InputId')
    '''

    _INVALID_VALUE = None
    '''
    Invalid value for this class is 'None'.
    '''

    _INVALID = None
    '''
    An instance of an InputId with 'None' as its value.
    '''

    def __init__(self, time_manager: TimeManager, allow: bool = False) -> None:
        '''
        Initialize our ID value. ID is based on:
          current time string + str(sequence)
        '''
        # Constructing _INVALID instance?
        if time_manager is self._INVALID_VALUE:
            self._value = self._INVALID_VALUE
            return

        # I do want UUIDs namespaced; that sounds... correct?.. to do. But at
        # the same time a user could throw two identical commands back to back
        # and so it seems silly to rely on anything useful for the UUID name
        # value (like username, input string, time received...). So we could
        # probably just UUID4 this, but whatever.

        # Get a unique time value to use as our UUID5 name?
        value = time_manager.machine.unique
        self._value = uuid.uuid5(self.UUID_NAMESPACE, value)

    # We get this from our metaclass (InvalidProvider):
    # @property
    # @classmethod
    # def INVALID(klass: Type['SerializableId']) -> 'SerializableId':
    #     '''
    #     Returns a constant value which is considered invalid by whatever
    #     provides these SerializableIds.
    #     '''
    #     return klass._INVALID

    # ---
    # Generator
    # ---

    @classmethod
    def generator(klass: Type['InputId'],
                  time_manager: TimeManager) -> 'InputIdGenerator':
        '''
        Returns a generator instance for this MonotonicId class.
        '''
        klass._init_invalid_()
        return InputIdGenerator(klass, time_manager)

    # ---
    # To String
    # ---

    @property
    def _format_(self) -> str:
        '''
        Format our value as a string and return only that.
        '''
        return str(self.value)

    @property
    def _short_name_(self) -> str:
        '''
        A short name for the class for abbreviated outputs (e.g. repr).
        '''
        return 'iid'
