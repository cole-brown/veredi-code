# coding: utf-8

'''
ID Base Classes for Various Kinds of IDs.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Type, Mapping, Tuple, Dict, Union

import uuid

from veredi.logs          import log
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
        seed = veredi.time.machine.unique()
        next_id = self._id_class(seed, user)
        return next_id


class UserId(SerializableId,
             name_dotted='veredi.data.identity.user.id',
             name_string='uid'):
    '''
    Serializable UserId class.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # ------------------------------
    # Static UUIDs
    # ------------------------------

    _UUID_NAMESPACE = uuid.UUID('dbf113a9-a1bf-57af-b85b-09708d367e8e')
    '''
    The 'namespace' for our UUIDs will be static so we can
    reproducably/reliably generate a UUID. Generate by:
      uuid.uuid5(uuid.UUID(int=0), 'veredi.data.identity.UserId')
    '''

    _UUID_SID_BROADCAST = uuid.UUID('5a47c4cb-d42d-51f9-a9ef-0e9d82107378')
    '''
    A static UUID for 'all connected users'. Generate by:
      uuid.uuid5(_UUID_NAMESPACE, 'special.broadcast')
    '''

    # ------------------------------
    # Static/Class UUIDs
    # ------------------------------

    _INVALID_VALUE = None
    '''
    Invalid value for this class is 'None'.
    '''

    _INVALID = None
    '''
    An instance of an InputId with 'None' as its value.
    '''

    _BROADCAST = None
    '''
    An instance of an InputId with '_UUID_SID_BROADCAST' as its value.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    @classmethod
    def _init_invalid_(klass: Type['UserId']) -> None:
        '''
        Creates our invalid instance that can be gotten from read-only class
        property INVALID.
        '''
        if not klass._INVALID:
            # Make our invalid singleton instance.
            klass._INVALID = klass(klass._INVALID_VALUE, klass._INVALID_VALUE)

    def __init__(self, seed: str, name: str,
                 decoding:      bool          = False,
                 decoded_value: Optional[int] = None) -> None:
        '''
        Initialize our ID value. ID is based on:
          current time string, name string, and _UUID_NAMESPACE.
        '''
        # log.debug(f"UserId.__!!INIT!!__: seed: {seed}, name: {name}, "
        #           f"decoding: {decoding}, "
        #           f"dec_val: {decoded_value}")

        # Decoding into a valid UserId?
        if (decoding                                  # Decode mode is a go.
                and not seed and not name             # Normal mode is a no.
                and isinstance(decoded_value, int)):  # Something decode.
            self._value = uuid.UUID(int=decoded_value)
            # log.debug("UserId.__init__: decoded to: "
            #           f"{self._value}, {str(self)}")

            # Don't forget to return now. >.<
            return

        # Constructing _INVALID instance?
        if not seed or not name:
            self._value = self._INVALID_VALUE
            return

        # Generate a valid UserId.
        self._value = uuid.uuid5(self._UUID_NAMESPACE, seed + name)

    # -------------------------------------------------------------------------
    # Properties / Getters
    # -------------------------------------------------------------------------

    # We get this from our metaclass (InvalidProvider):
    # @property
    # @classmethod
    # def INVALID(klass: Type['UserId']) -> 'UserId':
    #     '''
    #     Returns a constant value which is considered invalid by whatever
    #     provides these UserIds.
    #     '''
    #     return klass._INVALID

    @classmethod
    def broadcast(klass: Type['UserId']) -> 'UserId':
        '''
        Returns the static UserId for "broadcast to all users".
        '''
        if not klass._BROADCAST:
            # Make our singleton instance, then replace its value with the
            # proper constant.
            broadcast = klass("don't", "care")
            broadcast._value = klass._UUID_SID_BROADCAST
            klass._BROADCAST = broadcast

        return klass._BROADCAST

    # -------------------------------------------------------------------------
    # Encodable API
    # -------------------------------------------------------------------------

    @classmethod
    def _decode_simple_init(klass: Type['UserId'],
                            value: int,
                            codec: 'Codec') -> 'UserId':
        '''
        Subclasses can override this if they have a different constructor.
        '''
        decoded = klass(None, None,
                        decoding=True,
                        decoded_value=value)
        return decoded

    # -------------------------------------------------------------------------
    # Generator
    # -------------------------------------------------------------------------

    @classmethod
    def generator(klass:        Type['UserId'],
                  unit_testing: bool = False) -> 'UserIdGenerator':
        '''
        Returns a generator instance for UserIds.
        '''
        klass._init_invalid_()
        if unit_testing:
            return MockUserIdGenerator(klass)
        return UserIdGenerator(klass)

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

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
        next_key = self._id_class(seed, time_seed)
        return next_key


class UserKey(SerializableId,
              name_dotted='veredi.data.identity.user.key',
              name_string='ukey'):
    '''
    Serializable UserKey class.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # ------------------------------
    # Static UUIDs
    # ------------------------------

    _UUID_NAMESPACE = uuid.UUID('c3c6c728-6ad9-5173-afb0-e16c9dac800b')
    '''
    The 'namespace' for our UUIDs will be static so we can
    reproducably/reliably generate a UUID. Generate by:
      uuid.uuid5(uuid.UUID(int=0), 'veredi.data.identity.UserKey')
    '''

    _UUID_SKEY_BROADCAST = uuid.UUID('4b2a5916-127b-55e2-802e-32683687ea6f')
    '''
    A static UUID for 'all connected users'. Generate by:
      uuid.uuid5(_UUID_NAMESPACE, 'special.broadcast')
    '''

    # ------------------------------
    # Static/Class UUIDs
    # ------------------------------

    _INVALID_VALUE = None
    '''
    Invalid value for this class is 'None'.
    '''

    _INVALID = None
    '''
    An instance of an InputId with 'None' as its value.
    '''

    _BROADCAST = None
    '''
    An instance of an InputId with '_UUID_SID_BROADCAST' as its value.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    @classmethod
    def _init_invalid_(klass: Type['UserKey']) -> None:
        '''
        Creates our invalid instance that can be gotten from read-only class
        property INVALID.
        '''
        if not klass._INVALID:
            # Make our invalid singleton instance.
            klass._INVALID = klass(klass._INVALID_VALUE, klass._INVALID_VALUE)

    def __init__(self, seed: str, time_seed: str,
                 decoding:      bool          = False,
                 decoded_value: Optional[int] = None) -> None:
        '''
        Initialize our ID value. ID is based on:
          supplied `seed` string, current time string, and _UUID_NAMESPACE.
        '''
        # log.debug(f"UserKey.__!!INIT!!__: seed: {seed}, "
        #           f"time_seed: {time_seed}, "
        #           f"decoding: {decoding}, "
        #           f"dec_val: {decoded_value}")

        # Decoding into a valid UserKey?
        if (decoding                                  # Decode mode is a go.
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
        self._value = uuid.uuid5(self._UUID_NAMESPACE, seed + time_seed)

    # -------------------------------------------------------------------------
    # Properties / Getters
    # -------------------------------------------------------------------------

    # We get this from our metaclass (InvalidProvider):
    # @property
    # @classmethod
    # def INVALID(klass: Type['UserKey']) -> 'UserKey':
    #     '''
    #     Returns a constant value which is considered invalid by whatever
    #     provides these UserKeys.
    #     '''
    #     return klass._INVALID

    @classmethod
    def broadcast(klass: Type['UserKey']) -> 'UserKey':
        '''
        Returns the static UserKey for "broadcast to all users".
        '''
        if not klass._BROADCAST:
            # Make our singleton instance, then replace its value with the
            # proper constant.
            broadcast = klass("don't", "care")
            broadcast._value = klass._UUID_SKEY_BROADCAST
            klass._BROADCAST = broadcast

        return klass._BROADCAST

    # -------------------------------------------------------------------------
    # Encodable API
    # -------------------------------------------------------------------------

    @classmethod
    def _decode_simple_init(klass: Type['UserKey'],
                            value: int,
                            codec: 'Codec') -> 'UserKey':
        '''
        Subclasses can override this if they have a different constructor.
        '''
        decoded = klass(None, None,
                        decoding=True,
                        decoded_value=value)
        return decoded

    # -------------------------------------------------------------------------
    # Generator
    # -------------------------------------------------------------------------

    @classmethod
    def generator(klass:        Type['UserKey'],
                  unit_testing: bool = False) -> 'UserKeyGenerator':
        '''
        Returns a generator instance for UserKeys.
        '''
        klass._init_invalid_()
        if unit_testing:
            return MockUserKeyGenerator(klass)
        return UserKeyGenerator(klass)

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    @property
    def _format_(self) -> str:
        '''
        Format our value as a string and return only that.
        '''
        return str(self.value)


# -----------------------------------------------------------------------------
# Unit-Test ID Generators
# -----------------------------------------------------------------------------

class MockUserIdGenerator(UserIdGenerator):
    '''
    Class that generates serializable UserIds that will always be the same for
    the same inputs so... UUIDs that are not "universally unique" at all.
    '''

    def __init__(self,
                 id_class: Type['UserId']) -> None:
        super().__init__(id_class)

        self._ut_seeds: Dict[str, int] = {}
        '''Username strings to whatever ints you want as your UserId values.'''

    def ut_set_up(self, user_names_to_ids: Dict[str, int]) -> None:
        '''
        Set up this 'generator' to 'generate' UserIds using the ints associated
        with the username.
        '''
        self._ut_seeds = user_names_to_ids

    def next(self, user: str) -> 'UserId':
        # Need a constant for seed instead of time.
        value = self._ut_seeds[user]

        # Pretend we're decoding so we directly set instead of allowing UUID to
        # generate a random value.
        next_id = self._id_class(None, None,
                                 decoding=True,
                                 decoded_value=value)
        return next_id


class MockUserKeyGenerator(UserKeyGenerator):
    '''
    Class that generates serializable user keys that will always be the same
    for the same inputs so... UUIDs that are not "universally unique" at all.
    '''

    def __init__(self,
                 id_class: Type['UserId']) -> None:
        super().__init__(id_class)

        self._ut_seeds: Dict[Union[str, int], int] = {}
        '''
        User key strings/ints to whatever ints you want as your UserKey values.
        '''

    def ut_set_up(self, user_keys_to_ids: Dict[Union[str, int], int]) -> None:
        '''
        Set up this 'generator' to 'generate' UserIds using the ints associated
        with the username.
        '''
        self._ut_seeds = user_keys_to_ids

    def next(self, seed: Union[str, int]) -> 'UserKey':
        # Need a constant for seed instead of time.
        value = self._ut_seeds[seed]

        # Pretend we're decoding so we directly set instead of allowing UUID to
        # generate a random value.
        next_id = self._id_class(None, None,
                                 decoding=True,
                                 decoded_value=value)
        return next_id
