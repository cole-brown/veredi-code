# coding: utf-8

'''
ID Base Classes for Various Kinds of IDs.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Type, Mapping

import uuid

from veredi.base.identity import SerializableId
import veredi.time.machine


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class UserIdGenerator:
    '''
    Class that generates serializable UUIDs. Maybe could switch to
    something provided by the Repository?
    '''

    def __init__(self,
                 id_class: Type['UserId']) -> None:
        self._id_class = id_class

    def next(self, user: str) -> 'UserId':
        # return self._id_class(MachineTime.unique, user, allow=True)
        seed = veredi.time.machine.unique()
        ret = self._id_class(seed, user, allow=True)
        return ret


class UserId(SerializableId):
    '''
    Serializable UserId class.
    '''

    UUID_NAMESPACE = uuid.UUID('dbf113a9-a1bf-57af-b85b-09708d367e8e')
    '''
    The 'namespace' for our UUIDs will be static so we can
    reproducably/reliably generate a UUID. Generate by:
      uuid.uuid5(uuid.UUID(int=0), 'veredi.data.identity.UserId')
    '''

    _INVALID_VALUE = None
    '''
    Invalid value for this class is 'None'.
    '''

    _INVALID = None
    '''
    An instance of an InputId with 'None' as its value.
    '''

    _ENCODE_FIELD_NAME = 'uid'
    '''Short abbreviation for UserId.'''

    # ------------------------------
    # Initialization
    # ------------------------------

    def __new__(klass: Type['SerializableId'],
                seed: str,
                name: str,
                allow: Optional[bool] = False) -> 'SerializableId':
        '''
        This is to prevent creating IDs willy-nilly.
        '''
        if not allow:
            # Just make all constructed return the INVALID singleton.
            return klass._INVALID

        inst = super().__new__(klass, name, allow=True)
        inst.__init__(seed, name, allow=True)
        # I guess this is magic bullshit cuz I don't need to init it with
        # `value` but it still gets initialized with `value`?

        # no need: inst.__init__(value)
        return inst

    def __init__(self, seed: str, name: str,
                 allow:         bool          = False,
                 decoding:      bool          = False,
                 decoded_value: Optional[int] = None) -> None:
        '''
        Initialize our ID value. ID is based on:
          current time string, name string, and UUID_NAMESPACE.

        If `decoding`, just use `decode_value'.
        '''
        # Decoding into a valid UserId?
        if (allow and decoding                        # Decode mode is a go.
                and not seed and not name             # Normal mode is a no.
                and isinstance(decoded_value, int)):  # Something decode.
            self._value = uuid.UUID(decoded_value)

        # Constructing _INVALID instance?
        if not seed or not name:
            self._value                       = self._INVALID_VALUE
            return

        # Generate a valid UserId?
        self._value = uuid.uuid5(self.UUID_NAMESPACE, seed + name)

    # We get this from our metaclass (InvalidProvider):
    # @property
    # @classmethod
    # def INVALID(klass: Type['SerializableId']) -> 'SerializableId':
    #     '''
    #     Returns a constant value which is considered invalid by whatever
    #     provides these SerializableIds.
    #     '''
    #     return klass._INVALID

    # ------------------------------
    # Encodable API (Codec Support)
    # ------------------------------

    def encode(self) -> Mapping[str, int]:
        '''
        Returns a representation of ourself as a dictionary.
        '''
        encoded = {
            self._ENCODE_FIELD_NAME: self.value.int,
        }
        return encoded

    @classmethod
    def decode(klass: 'SerializableId',
               value: Mapping[str, int]) -> 'SerializableId':
        '''
        Turns our encoded dict into a SerializableId instance.
        '''
        decoded = klass(None, None,
                        allow=True, decoding=True,
                        decoded_value=value[klass._ENCODE_FIELD_NAME])
        return decoded

    # ------------------------------
    # Generator
    # ------------------------------

    @classmethod
    def generator(klass: Type['UserId']) -> 'UserIdGenerator':
        '''
        Returns a generator instance for UserIds.
        '''
        klass._init_invalid_()
        return UserIdGenerator(klass)

    # ------------------------------
    # To String
    # ------------------------------

    @property
    def _format_(self) -> str:
        '''
        Format our value as a string and return only that.
        '''
        return str(self.value)
