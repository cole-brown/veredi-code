# coding: utf-8

'''
ID Base Classes for Various Kinds of IDs.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, Type, Mapping, Tuple, List, Dict

import re
import uuid

# General Stuff in General
from abc import abstractmethod
# from veredi.base.decorators import abstract_class_attribute
from veredi.base.metaclasses import InvalidProvider, ABC_InvalidProvider

from veredi.data.codec.encodable import Encodable


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO [2020-06-20]: parent class for the init/new/init_invalid bullshit?


# -----------------------------------------------------------------------------
# IN-GAME, PER-SESSION:
#   - Base Class and Generator for internal-only, monotonically increasing IDs.
# -----------------------------------------------------------------------------

class MonotonicIdGenerator:
    '''
    Class that generates monotonically increasing IDs. Not random, not UUID...
    just monotonically increasing.
    '''

    def __init__(self, id_class: Type['MonotonicId']) -> None:
        self._id_class = id_class
        self._last_id = id_class.INVALID.value

    def next(self) -> 'MonotonicId':
        self._last_id += 1
        next_id = self._id_class(self._last_id, allow=True)
        return next_id

    def peek(self) -> 'MonotonicId':
        return self._last_id


class MonotonicId(Encodable, metaclass=InvalidProvider):
    '''
    Integer-based, montonically increasing ID suitable for in-game,
    non-serialized identity.

    For example, this is a good ID class to use for ECS pieces that get created
    for a game, used, and tossed. The actual serialized data should have a
    different, serializable ID.
    '''

    # The value our INVALID instance should have.
    _INVALID_VALUE = 0

    # This is what InvalidProvider looks for to return in its class property.
    _INVALID = None

    _ENCODE_FIELD_NAME = 'id'
    '''Can override in sub-classes if needed. E.g. 'eid' for entity id.'''

    # ------------------------------
    # Initialization
    # ------------------------------

    @classmethod
    def _init_invalid_(klass: Type['MonotonicId']) -> None:
        '''
        This is to prevent creating IDs willy-nilly.
        '''
        if not klass._INVALID:
            # Make our invalid singleton instance.
            klass._INVALID = klass(klass._INVALID_VALUE, True)

    def __new__(klass: Type['MonotonicId'],
                value: int,
                allow: Optional[bool] = False) -> 'MonotonicId':
        '''
        This is to prevent creating IDs willy-nilly.
        '''
        if not allow:
            # Just make all constructed return the INVALID singleton.
            return klass._INVALID

        inst = super().__new__(klass)
        # I guess this is magic bullshit cuz I don't need to init it with
        # `value` but it still gets initialized with `value`?

        # no need: inst.__init__(value)
        return inst

    def __init__(self, value: int, allow: bool = False) -> None:
        '''
        Initialize our ID value.
        '''
        self._value = value

    # ------------------------------
    # Generator
    # ------------------------------

    @classmethod
    def generator(klass: Type['MonotonicId']) -> 'MonotonicIdGenerator':
        '''
        Returns a generator instance for this MonotonicId class.
        '''
        klass._init_invalid_()
        return MonotonicIdGenerator(klass)

    # ------------------------------
    # Properties
    # ------------------------------

    # We get this from our metaclass (InvalidProvider):
    # @property
    # @classmethod
    # def INVALID(klass: Type['MonotonicId']) -> 'MonotonicId':
    #     return klass._INVALID

    @property
    def value(self) -> Any:
        '''
        Returns the underlying value of this ID... whatever it is.
        String? Int? A potato?
        '''
        return self._value

    # ------------------------------
    # Encodable API (Codec Support)
    # ------------------------------

    def encode(self) -> Mapping[str, str]:
        '''
        Returns a representation of ourself as a dictionary.
        '''
        encoded = super().encode()
        encoded.update({
            self._ENCODE_FIELD_NAME: self.value,
        })
        return encoded

    @classmethod
    def decode(klass: 'MonotonicId',
               value: Mapping[str, str]) -> 'MonotonicId':
        '''
        Turns our encoded dict into a MonotonicId instance.
        '''
        klass.error_for_key(klass._ENCODE_FIELD_NAME, value)
        decoded = klass(value[klass._ENCODE_FIELD_NAME])
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
        args = (self.value, )
        kwargs = {}
        return (args, kwargs)

    # ------------------------------
    # To Int
    # ------------------------------

    def __int__(self) -> Any:
        '''
        Returns the underlying value of this ID converted to int.
        '''
        return int(self._value)

    # ------------------------------
    # Equality
    # ------------------------------

    def __eq__(self, other):
        '''Equality check for ids should be value, not instance.'''
        if not isinstance(other, self.__class__):
            return False
        return self.value == other.value

    def __hash__(self):
        '''Since equality is by value, we should hash by that too.'''
        return hash(self.value)

    # ------------------------------
    # To String
    # ------------------------------

    @property
    def _format_(self) -> str:
        '''
        Format our value as a string and return only that.
        '''
        return '{:03d}'.format(self.value)

    @property
    def _short_name_(self) -> str:
        '''
        A short name for the class for abbreviated outputs (e.g. repr).
        '''
        return self._ENCODE_FIELD_NAME

    def __str__(self) -> str:
        return f'{self.__class__.__name__}:{self._format_}'

    def __repr__(self) -> str:
        return f'{self._short_name_}:{self._format_}'


# -----------------------------------------------------------------------------
# SERIALIZABLE:
#   - Base Class and Generator for internal-only, random-esque IDs.
# -----------------------------------------------------------------------------

# class SerializableIdGenerator:
#     '''
#     Class that generates serializable, unique IDs. Probably not used as the
#     database or something will generate?
#     '''
#
#     def __init__(self, id_class: Type['MonotonicId']) -> None:
#         self._id_class = id_class
#         self._last_id = id_class.INVALID
#
#     def next(self) -> 'MonotonicId':
#         self._last_id += 1
#         return self._id_class(self._last_id)
#
#     def peek(self) -> 'MonotonicId':
#         return self._last_id


class SerializableId(Encodable, metaclass=ABC_InvalidProvider):
    '''
    Base class for a serializable ID (e.g. to a file, or primary key value from
    a databse).

    Plese implement:
      Class property or constant:
        - INVALID - The ID value that will always be considered INVALID.

      Instance Methods:
        - _format_() - Returns bare id value formatted as string.
                     - If class is JeffId and value is 42:
                       - jeff._format_() -> "42"
                       - str(jeff) -> "JID::42"
    '''

    _ENCODE_FIELD_NAME = 'serid'
    '''Can override in sub-classes if needed. E.g. 'iid' for input id.'''

    _DECODE_UUID_PREFIX = '{short_name}'
    '''
    Static ident string at front of regex for the class. e.g. 'uid:' for UserId.
    '''

    _DECODE_UUID_PREFIX_SEP = r':'

    _DECODE_UUID_FORM = (
        r'[0-9A-Fa-f]{8}-'
        r'[0-9A-Fa-f]{4}-'
        r'[0-9A-Fa-f]{4}-'
        r'[0-9A-Fa-f]{4}-'
        r'[0-9A-Fa-f]{12}'
    )
    '''
    UUID has hexadecimals separated by dashes in the form 8-4-4-4-12.
    '''

    _DECODE_UUID_RX = re.compile(
        # Start at beginning of string, only allow whitespace until us.
        r'^\s*'
        # Start 'name' capture group.
        + r'(?P<name>'
          # Name capture is our _ENCODE_FIELD_NAME.
        + _DECODE_UUID_PREFIX.format(short_name=_ENCODE_FIELD_NAME)
        + r')'
        + _DECODE_UUID_PREFIX_SEP
          # Start 'value' capture group.
        + r'(?P<value>'
          # Value capture is our UUID hexadecimal form.
        + _DECODE_UUID_FORM
        + r')'
          # More whitespace is ok; anything else isn't. End at end of strig.
        + r'\s*$'
    )

    # ------------------------------
    # Initialization
    # ------------------------------

    @classmethod
    def _init_invalid_(klass: Type['SerializableId']) -> None:
        '''
        Creates our invalid instance that can be gotten from read-only class
        property INVALID.
        '''
        if not klass._INVALID:
            # Make our invalid singleton instance.
            klass._INVALID = klass(klass._INVALID_VALUE)

    def __init__(self,
                 decoding:      bool          = False,
                 decoded_value: Optional[int] = None) -> None:
        '''
        Subclasses should implement their __init__().
        We currently have nothing to do.
        '''
        ...

    # ------------------------------
    # Concrete Properties
    # ------------------------------

    @property
    def value(self) -> Any:
        '''
        Returns the underlying value of this ID... whatever it is.
        String? Int? A potato?
        '''
        return self._value

    # ------------------------------
    # Abstract Properties/Attributes
    # ------------------------------

    # These are 'defined' in our "@abstract_class_attributes" decorators.
    # Leave them around for subclassers to grab as a starting point:

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

    def encode(self) -> Mapping[str, str]:
        '''
        Returns a representation of ourself as a dictionary.
        '''
        encoded = super().encode()
        # So far all of our subclasses are UUID-based, so a check for that
        # makes sense...
        enc_value = self.value
        if isinstance(enc_value, uuid.UUID):
            enc_value = self.value.int
        encoded.update({
            self._ENCODE_FIELD_NAME: enc_value,
        })
        return encoded

    @classmethod
    def _decode(klass: 'SerializableId',
                value: Mapping[str, str]) -> 'SerializableId':
        '''
        Private implementation of decoding. In case anyone wants to disallow
        the long-form encode/decode but allow decode_str() to still use
        _decode().

        Turns our encoded dict into a SerializableId instance.
        '''
        klass.error_for_key(klass._ENCODE_FIELD_NAME, value)
        decoded = klass(None,
                        decoding=True,
                        decoded_value=value[klass._ENCODE_FIELD_NAME])
        return decoded

    @classmethod
    def decode(klass: 'SerializableId',
               value: Mapping[str, str]) -> 'SerializableId':
        '''
        Turns our encoded dict into a SerializableId instance.
        '''
        return klass._decoded(value)

    def encode_str(self) -> str:
        '''
        Encode this instance into a string.

        Return the string.
        '''
        return str(self)

    @classmethod
    def decode_str(klass: 'SerializableId', string: str) -> 'SerializableId':
        '''
        Decode the `string` to a SerializableId instance.

        Return the instance.
        '''
        match = re.match(klass._DECODE_UUID_RX, string)
        if not match:
            return None
        # Get actual value from match, remove nice separators so we have just a
        # hex number...
        hex_str = match.group('value')
        hex_str = hex_str.replace('-', '')
        # Convert that into an actual number.
        # Could throw a value error if something's wrong...
        hex_value = int(hex_str, 16)

        # And now we should be able to decode?
        encoded = super().encode()
        encoded.update({
            klass._ENCODE_FIELD_NAME: hex_value,
        })
        return klass._decode(encoded)

    @classmethod
    def get_decode_rx(klass: 'Encodable') -> Optional[str]:
        '''
        Returns compiled regex of what to look for to claim just a string as
        this class.

        For example, perhaps a UserId for 'jeff' has a normal decode of:
          {
            '_encodable': 'UserId',
            'uid': 'deadbeef-cafe-1337-1234-e1ec771cd00d',
          }
        And perhaps it has str() of 'uid:deadbeef-cafe-1337-1234-e1ec771cd00d'

        This would expect an rx string for the str.
        '''
        return klass._DECODE_UUID_RX

    # ------------------------------
    # Abstract Methods
    # ------------------------------

    # _format_()  # Below in "To String" section.

    # ------------------------------
    # Equality
    # ------------------------------

    def __eq__(self, other):
        '''Equality check for ids should be value, not instance.'''
        if not isinstance(other, self.__class__):
            return False
        return self.value == other.value

    def __hash__(self):
        '''Since equality is by value, we should hash by that too.'''
        return hash(self.value)

    # ------------------------------
    # To String
    # ------------------------------

    @property
    @abstractmethod
    def _format_(self) -> str:
        '''
        Format our value as a string and return only that.
        '''
        raise NotImplementedError

    @property
    def _short_name_(self) -> str:
        '''
        A short name for the class for abbreviated outputs (e.g. repr).
        '''
        # 'sid' is already used a lot as short-hand for SystemId...
        return self._ENCODE_FIELD_NAME

    def __str__(self) -> str:
        return f'{self.__class__.__name__}:{self._format_}'

    def __repr__(self) -> str:
        return f'{self._short_name_}:{self._format_}'
