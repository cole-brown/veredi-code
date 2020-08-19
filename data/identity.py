# coding: utf-8

'''
ID Base Classes for Various Kinds of IDs.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Type, Mapping, Tuple, Dict, Union

import uuid

from veredi.logger        import log
from veredi.base.identity import SerializableId
import veredi.time.machine


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# UserId
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

    def __new__(klass:         Type['UserId'],
                seed:          str,
                name:          str,
                allow:         Optional[bool] = False,
                decoding:      bool           = False,
                decoded_value: Optional[int]  = None) -> 'UserId':
        '''
        This is to prevent creating IDs willy-nilly.
        '''
        if not allow:
            # Just make all constructed return the INVALID singleton.
            return klass._INVALID

        # log.debug(f"UserId.__new__: seed: {seed}, name: {name}, "
        #           f"allow: {allow}, decoding: {decoding}, "
        #           f"dec_val: {decoded_value}")

        inst = super().__new__(klass, name, allow=True)
        # inst.__init__(seed, name,
        #               allow=allow,
        #               decoding=decoding,
        #               decoded_value=decoded_value)
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
        # log.debug(f"UserId.__!!INIT!!__: seed: {seed}, name: {name}, "
        #           f"allow: {allow}, decoding: {decoding}, "
        #           f"dec_val: {decoded_value}")

        # Decoding into a valid UserId?
        if (allow and decoding                        # Decode mode is a go.
                and not seed and not name             # Normal mode is a no.
                and isinstance(decoded_value, int)):  # Something decode.
            self._value = uuid.UUID(int=decoded_value)
            # log.debug("UserId.__init__: decoded to: "
            #           f"{self._value}, {str(self)}")

            # Don't forget to return now. >.<
            return

        # Constructing _INVALID instance?
        if not seed or not name:
            self._value                       = self._INVALID_VALUE
            return

        # Generate a valid UserId?
        self._value = uuid.uuid5(self.UUID_NAMESPACE, seed + name)

    # We get this from our metaclass (InvalidProvider):
    # @property
    # @classmethod
    # def INVALID(klass: Type['UserId']) -> 'UserId':
    #     '''
    #     Returns a constant value which is considered invalid by whatever
    #     provides these UserIds.
    #     '''
    #     return klass._INVALID

    # ------------------------------
    # Encodable API (Codec Support)
    # ------------------------------

    def encode(self) -> Mapping[str, int]:
        '''
        Returns a representation of ourself as a dictionary.
        '''
        encoded = super().encode()
        encoded[self._ENCODE_FIELD_NAME] = self.value.int
        return encoded

    @classmethod
    def decode(klass: 'UserId',
               mapping: Mapping[str, int]) -> 'UserId':
        '''
        Turns our encoded dict into a UserId instance.
        '''
        klass.error_for(mapping, keys=[klass._ENCODE_FIELD_NAME])
        decoded = klass(None, None,
                        allow=True, decoding=True,
                        decoded_value=mapping[klass._ENCODE_FIELD_NAME])
        return decoded

    # ------------------------------
    # Pickleable API
    # ------------------------------

    def __getnewargs_ex__(self) -> Tuple[Tuple, Dict]:
        '''
        Returns a 2-tuple of:
          - a tuple for *args
          - a dict for **kwargs
        These values will be used in __new__ for unpickling ourself.
        '''
        # Set it up for the 'decoding & pickle' path through __new__ for the
        # unpickle.
        args = (None, None)  # seed, name
        kwargs = {
            'allow': True,
            'decoding': True,
            'decoded_value': self.value.int,
        }
        return (args, kwargs)

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


# -----------------------------------------------------------------------------
# UserKey
# -----------------------------------------------------------------------------

class UserKeyGenerator:
    '''
    Class that generates serializable user keys.
    '''

    def __init__(self,
                 id_class: Type['UserKey']) -> None:
        self._id_class = id_class

    def next(self, seed: Union[str, int]) -> 'UserKey':
        time_seed = veredi.time.machine.unique()
        seed = str(seed)
        ret = self._id_class(seed, time_seed, allow=True)
        return ret


class UserKey(SerializableId):
    '''
    Serializable UserKey class.
    '''

    UUID_NAMESPACE = uuid.UUID('c3c6c728-6ad9-5173-afb0-e16c9dac800b')
    '''
    The 'namespace' for our UUIDs will be static so we can
    reproducably/reliably generate a UUID. Generate by:
      uuid.uuid5(uuid.UUID(int=0), 'veredi.data.identity.UserKey')
    '''

    _INVALID_VALUE = None
    '''
    Invalid value for this class is 'None'.
    '''

    _INVALID = None
    '''
    An instance of an InputId with 'None' as its value.
    '''

    _ENCODE_FIELD_NAME = 'ukey'
    '''Short abbreviation for UserKey.'''

    # ------------------------------
    # Initialization
    # ------------------------------

    def __new__(klass:         Type['UserKey'],
                seed:          str,
                time_seed:     str,
                allow:         Optional[bool] = False,
                decoding:      bool           = False,
                decoded_value: Optional[int]  = None) -> 'UserKey':
        '''
        This is to prevent creating IDs willy-nilly.
        '''
        if not allow:
            # Just make all constructed return the INVALID singleton.
            return klass._INVALID

        # log.debug(f"UserKey.__new__: seed: {seed}, time_seed: {time_seed}, "
        #           f"allow: {allow}, decoding: {decoding}, "
        #           f"dec_val: {decoded_value}")

        inst = super().__new__(klass, seed, allow=True)
        # inst.__init__(seed, time_seed,
        #               allow=allow,
        #               decoding=decoding,
        #               decoded_value=decoded_value)
        return inst

    def __init__(self, seed: str, time_seed: str,
                 allow:         bool          = False,
                 decoding:      bool          = False,
                 decoded_value: Optional[int] = None) -> None:
        '''
        Initialize our ID value. ID is based on:
          supplied `seed` string, current time string, and UUID_NAMESPACE.

        If `decoding`, just use `decode_value'.
        '''
        # log.debug(f"UserKey.__!!INIT!!__: seed: {seed}, "
        #           f"time_seed: {time_seed}, "
        #           f"allow: {allow}, decoding: {decoding}, "
        #           f"dec_val: {decoded_value}")

        # Decoding into a valid UserKey?
        if (allow and decoding                        # Decode mode is a go.
                and not seed and not time_seed        # Normal mode is a no.
                and isinstance(decoded_value, int)):  # Something decode.
            self._value = uuid.UUID(int=decoded_value)
            # log.debug("UserKey.__init__: decoded to: "
            #           f"{self._value}, {str(self)}")

            # Don't forget to return now. >.<
            return

        # Constructing _INVALID instance?
        if not seed or not time_seed:
            self._value                       = self._INVALID_VALUE
            return

        # Generate a valid UserKey?
        self._value = uuid.uuid5(self.UUID_NAMESPACE, seed + time_seed)

    # We get this from our metaclass (InvalidProvider):
    # @property
    # @classmethod
    # def INVALID(klass: Type['UserKey']) -> 'UserKey':
    #     '''
    #     Returns a constant value which is considered invalid by whatever
    #     provides these UserKeys.
    #     '''
    #     return klass._INVALID

    # ------------------------------
    # Encodable API (Codec Support)
    # ------------------------------

    def encode(self) -> Mapping[str, int]:
        '''
        Returns a representation of ourself as a dictionary.
        '''
        encoded = super().encode()
        encoded[self._ENCODE_FIELD_NAME] = self.value.int
        return encoded

    @classmethod
    def decode(klass: 'UserKey',
               mapping: Mapping[str, int]) -> 'UserKey':
        '''
        Turns our encoded dict into a UserKey instance.
        '''
        klass.error_for(mapping, keys=[klass._ENCODE_FIELD_NAME])
        decoded = klass(None, None,
                        allow=True, decoding=True,
                        decoded_value=mapping[klass._ENCODE_FIELD_NAME])
        return decoded

    # ------------------------------
    # Pickleable API
    # ------------------------------

    def __getnewargs_ex__(self) -> Tuple[Tuple, Dict]:
        '''
        Returns a 2-tuple of:
          - a tuple for *args
          - a dict for **kwargs
        These values will be used in __new__ for unpickling ourself.
        '''
        # Set it up for the 'decoding & pickle' path through __new__ for the
        # unpickle.
        args = (None, None)  # time_seed, seed
        kwargs = {
            'allow': True,
            'decoding': True,
            'decoded_value': self.value.int,
        }
        return (args, kwargs)

    # ------------------------------
    # Generator
    # ------------------------------

    @classmethod
    def generator(klass: Type['UserKey']) -> 'UserKeyGenerator':
        '''
        Returns a generator instance for UserKeys.
        '''
        klass._init_invalid_()
        return UserKeyGenerator(klass)

    # ------------------------------
    # To String
    # ------------------------------

    @property
    def _format_(self) -> str:
        '''
        Format our value as a string and return only that.
        '''
        return str(self.value)
