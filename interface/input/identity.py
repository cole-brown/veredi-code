# coding: utf-8

'''
IDs for InputEvents, Commands, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Type

import uuid

from veredi.base.strings  import labeler
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
        return self._id_class(self._time)


@labeler.dotted('veredi.interface.input.identity.input')
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
    UUID_NAMESPACE = uuid.UUID('6ad31d78-a307-52c8-8497-339026bcf7dc')
    '''
    The 'namespace' for our UUIDs will be static so we can
    reproducably/reliably generate a UUID. Generate by:
      uuid.uuid5(uuid.UUID(int=0), 'veredi.interface.input.identity.InputId')
    '''

    _INVALID_VALUE = None
    '''
    Invalid value for this class is 'None'.
    '''

    _INVALID = None
    '''
    An instance of an InputId with 'None' as its value.
    '''

    _ENCODE_FIELD_NAME = 'iid'
    '''Can override in sub-classes if needed. E.g. 'iid' for input id.'''

    def __init__(self,
                 time_manager: TimeManager,
                 decoding:      bool          = False,
                 decoded_value: Optional[int] = None) -> None:
        '''
        Initialize our ID value. ID is based on:
          current time string + str(sequence)
        '''
        # Decoding into a valid UserId?
        if (decoding                                  # Decode mode is a go.
                and not time_manager                  # Normal mode is a no.
                and isinstance(decoded_value, int)):  # Something decode.
            self._value = uuid.UUID(int=decoded_value)
            # log.debug("UserId.__init__: decoded to: "
            #           f"{self._value}, {str(self)}")

            # Don't forget to return now. >.<
            return

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
