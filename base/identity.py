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

from abc import abstractmethod

from veredi.logs              import log
# from veredi.base.decorators import abstract_class_attribute
from veredi.base.metaclasses  import InvalidProvider, ABC_InvalidProvider

from veredi.data.codec        import (Codec,
                                      Encoding,
                                      Encodable,
                                      EncodedComplex)


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


class MonotonicId(Encodable,
                  name_dotted='veredi.base.identity.monotonic',
                  name_string='v.mid',
                  metaclass=ABC_InvalidProvider):
    '''
    Integer-based, montonically increasing ID suitable for in-game,
    non-serialized identity.

    For example, this is a good ID class to use for ECS pieces that get created
    for a game, used, and tossed. The actual serialized data should have a
    different, serializable ID.
    '''

    # ------------------------------
    # Constants: Invalid
    # ------------------------------

    _INVALID_VALUE: int = 0
    '''The value our INVALID instance should have.'''

    _INVALID: 'MonotonicId' = None
    '''Our INVALID instance singleton is stored here.'''

    # ------------------------------
    # Constants: Encodable
    # ------------------------------

    _ENCODABLE_RX_FLAGS: re.RegexFlag = re.IGNORECASE
    '''Flags used when creating _ENCODABLE_RX.'''

    _ENCODABLE_RX_STR_FMT: str = r'^{type_field}:(?P<value>\d+)$'
    '''Format string for making MonotonicId a bit more subclassable.'''

    _ENCODABLE_RX_STR: str = None
    '''
    Actual string used to compile regex - created from _ENCODABLE_RX_STR_FMT
    in MonotonicId.__init_subclass__().
    '''

    _ENCODABLE_RX: re.Pattern = None
    '''
    Compiled regex pattern for decoding MonotonicIds.
    '''

    _ENCODE_SIMPLE_FMT: str = '{type_field}:{value}'
    '''
    String format for encoding MonotonicIds.
    '''

    # ------------------------------
    # Initialization
    # ------------------------------

    def __init_subclass__(klass:    Type['Encodable'],
                          **kwargs: Any) -> None:
        '''
        Initialize sub-classes.
        '''
        # Pass up to parent.
        super().__init_subclass__(**kwargs)

        # ---
        # _INVALID singleton
        # ---
        MonotonicId._init_invalid_()  # Init base class's INVALID.
        klass._init_invalid_()        # Init this class's INVALID.

        # ---
        # Encodable RX
        # ---
        if not klass.encoding().has(Encoding.COMPLEX):
            return

        # Do we need to init _ENCODABLE_RX_STR?
        if klass._ENCODABLE_RX_STR is None:
            # Format string with field name.
            klass._ENCODABLE_RX_STR = klass._ENCODABLE_RX_STR_FMT.format(
                type_field=klass.type_field())

            # ...and then use it to compile the regex.
            klass._ENCODABLE_RX = re.compile(klass._ENCODABLE_RX_STR,
                                             klass._ENCODABLE_RX_FLAGS)

    @classmethod
    def _init_invalid_(klass: Type['MonotonicId']) -> None:
        '''
        This is to prevent creating IDs willy-nilly.
        '''
        # Make one if we don't have one of our (sub)class.
        if isinstance(klass._INVALID, klass):
            return

        # Make our invalid singleton instance.
        klass._INVALID = klass(klass._INVALID_VALUE, True)

    def __init__(self, value: int, allow: bool = False) -> None:
        '''
        Initialize our ID value.
        '''
        self._value: int = value

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
    def value(self) -> int:
        '''
        Returns the underlying value of this ID.
        '''
        return self._value

    # ------------------------------
    # Encodable API (Codec Support)
    # ------------------------------

    @classmethod
    def encoding(klass: Type['MonotonicId']) -> Encoding:
        '''We are too simple to bother with being a complex type.'''
        return Encoding.SIMPLE

    @classmethod
    def _get_decode_str_rx(klass: Type['MonotonicId']) -> Optional[str]:
        '''
        Returns regex /string/ (not compiled regex) of what to look for to
        claim just a string as this class.
        '''
        if not klass._ENCODABLE_RX_STR:
            # Build it from the format str.
            klass._ENCODABLE_RX_STR = klass._ENCODABLE_RX_STR_FMT.format(
                type_field=klass.type_field())

        return klass._ENCODABLE_RX_STR

    @classmethod
    def _get_decode_rx(klass: Type['MonotonicId']) -> re.Pattern:
        '''
        Returns /compiled/ regex (not regex string) of what to look for to
        claim just a string as this class.
        '''
        if not klass._ENCODABLE_RX:
            # Build it from the regex str.
            rx_str = klass._get_decode_str_rx()
            if not rx_str:
                msg = (f"{klass.klass}: Cannot get decode regex "
                       "- there is no decode regex string to compile it from.")
                error = ValueError(msg, rx_str)
                raise log.exception(error, msg)

            klass._ENCODABLE_RX = re.compile(rx_str, klass._ENCODABLE_RX_FLAGS)

        return klass._ENCODABLE_RX

    def encode_simple(self, codec: 'Codec') -> str:
        '''
        Encode ourself as a string, return that value.
        '''
        return self._ENCODE_SIMPLE_FMT.format(type_field=self.type_field(),
                                              value=self.value)

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(
            f"{self.klass}.encode_complex() is not implemented.")

    @classmethod
    def decode_simple(klass: Type['MonotonicId'],
                      data:  str,
                      codec: 'Codec') -> 'MonotonicId':
        '''
        Decode ourself from a string, return a new instance of `klass` as
        the result of the decoding.
        '''
        rx = klass._get_decode_rx()
        if not rx:
            msg = (f"{klass.klass}: No decode regex - "
                   f"- cannot decode: {data}")
            error = ValueError(msg, data)
            raise log.exception(error, msg)

        # Have regex, but does it work on data?
        match = rx.match(data)
        if not match or not match.group('value'):
            msg = (f"{klass.klass}: Decode regex failed to match "
                   f"data - cannot decode: {data} "
                   f"(regex: {klass._get_decode_str_rx()})")
            error = ValueError(msg, data)
            raise log.exception(error, msg)

        value = int(match.group('value'))
        # And now we should be able to decode.
        return klass._decode_simple_init(value, codec)

    @classmethod
    def _decode_simple_init(klass: Type['MonotonicId'],
                            value: int,
                            codec: 'Codec') -> 'MonotonicId':
        '''
        Subclasses can override this if they have a different constructor.
        '''
        decoded = klass(value,
                        allow=True)
        return decoded

    @classmethod
    def decode_complex(klass: Type['MonotonicId'],
                       value: EncodedComplex,
                       codec: 'Codec',
                       instance: Optional['MonotonicId'] = None
                       ) -> 'MonotonicId':
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(f"{klass.klass}.decode_complex() is "
                                  "not implemented.")

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

    def __str__(self) -> str:
        return f'{self.klass}:{self._format_}'

    def __repr__(self) -> str:
        return f'{self.name}:{self._format_}'


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


class SerializableId(Encodable,
                     name_dotted='veredi.base.identity.serializable',
                     name_string='identity.serializable',
                     metaclass=ABC_InvalidProvider):
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

    # ------------------------------
    # Static UUIDs
    # ------------------------------

    _UUID_NAMESPACE: uuid.UUID = uuid.UUID(
        '77a1d3cb-a755-50d5-902f-21d18dfc08fd'
    )
    '''
    NOTE: Subclasses SHOULD OVERRIDE THIS with their own!!!

    The 'namespace' for our UUIDs will be static so we can
    reproducably/reliably generate a UUID. Generated by:
      uuid.uuid5(uuid.UUID(int=0), 'veredi.base.identity.serializable')
    '''

    # ------------------------------
    # Constants: Invalid
    # ------------------------------

    _INVALID_VALUE: int = 0
    '''The value our INVALID instance should have.'''

    _INVALID: 'SerializableId' = None
    '''Our INVALID instance singleton is stored here.'''

    # ------------------------------
    # Constants: Encodable
    # ------------------------------

    _ENCODABLE_RX_FLAGS: re.RegexFlag = re.IGNORECASE
    '''Flags used when creating _ENCODABLE_RX.'''

    _ENCODE_RX_UUID_FORM: str = (
        r'[0-9A-Fa-f]{8}-'
        r'[0-9A-Fa-f]{4}-'
        r'[0-9A-Fa-f]{4}-'
        r'[0-9A-Fa-f]{4}-'
        r'[0-9A-Fa-f]{12}'
    )
    '''
    UUID has hexadecimals separated by dashes in the form 8-4-4-4-12.
    '''

    _ENCODABLE_RX_STR_FMT: str = (
        # Start at beginning of string.
        r'^'
        # Start 'name' capture group.
        + r'(?P<name>'
        # Name capture is our type_field().
        + '{type_field}'
        + r')'
        # Separate name and value with colon.
        + r':'
        # Start 'value' capture group.
        + r'(?P<value>'
        # Value capture is our UUID hexadecimal form.
        + '{encode_uuid_rx}'
        + r')'
        # End at end of string.
        + r'$'
    )
    '''
    Actual string used to compile regex.
    '''

    _ENCODABLE_RX_STR: str = None
    '''
    Actual string used to compile regex. Leave as None for __init_subclass__ to
    set to _encodable_rx_str_base with subclass's klass.name.
    '''

    _ENCODABLE_RX: re.Pattern = None
    '''
    Compiled regex pattern for decoding SerializableIds.
    '''

    _ENCODE_SIMPLE_FMT: str = '{type_field}:{value}'
    '''
    String format for encoding SerializableIds.
    '''

    # ------------------------------
    # Initialization
    # ------------------------------

    def __init_subclass__(klass:    Type['Encodable'],
                          dotted:   Optional[str] = None,
                          **kwargs: Any) -> None:
        '''
        Initialize sub-classes.
        '''
        # Pass up to parent.
        super().__init_subclass__(**kwargs)

        # ---
        # _INVALID singleton
        # ---
        # SerializableIds are abstract - no need to init INVALID.
        # SerializableId._init_invalid_()  # Init base class's INVALID.
        klass._init_invalid_()           # Init this class's INVALID.

        # ---
        # Encodable RX
        # ---
        if not klass.encoding().has(Encoding.SIMPLE):
            return

        # Do we need to init _ENCODABLE_RX_STR?
        if klass._ENCODABLE_RX_STR is None:
            # Format string with field name.
            klass._ENCODABLE_RX_STR = klass._ENCODABLE_RX_STR_FMT.format(
                type_field=klass.type_field(),
                encode_uuid_rx=klass._ENCODE_RX_UUID_FORM)

            # ...and then use it to compile the regex.
            klass._ENCODABLE_RX = re.compile(klass._ENCODABLE_RX_STR,
                                             klass._ENCODABLE_RX_FLAGS)

    @classmethod
    def _init_invalid_(klass: Type['SerializableId']) -> None:
        '''
        Creates our invalid instance that can be gotten from read-only class
        property INVALID.
        '''
        # Make one if we don't have one of our (sub)class.
        if isinstance(klass._INVALID, klass):
            return

        # Make our invalid singleton instance.
        klass._INVALID = klass(klass._INVALID_VALUE, klass._INVALID_VALUE)

    def __init__(self, seed: str, name: str,
                 decoding:      bool          = False,
                 decoded_value: Optional[int] = None) -> None:
        '''
        Initialize our ID value. ID is based on:
          current time string, name string, and _UUID_NAMESPACE.
        '''
        # log.debug("SerializableId.__!!INIT!!__: "
        #           f"seed: {seed}, name: {name}, "
        #           f"decoding: {decoding}, "
        #           f"dec_val: {decoded_value}")

        # Decoding into a valid SerializableId?
        if (decoding                                  # Decode mode is a go.
                and not seed and not name             # Normal mode is a no.
                and isinstance(decoded_value, int)):  # Something decode.
            self._value = uuid.UUID(int=decoded_value)
            # log.debug("SerializableId.__init__: decoded to: "
            #           f"{self._value}, {str(self)}")

            # Don't forget to return now. >.<
            return

        # If we don't have a required input, make ourself INVALID.
        if not seed or not name:
            self._value = self._INVALID_VALUE
            return

        # Generate a valid SerializableId.
        self._value = uuid.uuid5(self._UUID_NAMESPACE, seed + name)

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

    @classmethod
    def encoding(klass: Type['SerializableId']) -> Encoding:
        '''We are too simple to bother with being a complex type.'''
        return Encoding.SIMPLE

    @classmethod
    def _get_decode_str_rx(klass: Type['SerializableId']) -> Optional[str]:
        '''
        Returns regex /string/ (not compiled regex) of what to look for to
        claim just a string as this class.
        '''
        return klass._ENCODABLE_RX_STR

    @classmethod
    def _get_decode_rx(klass: Type['SerializableId']) -> re.Pattern:
        '''
        Returns /compiled/ regex (not regex string) of what to look for to
        claim just a string as this class.
        '''
        return klass._ENCODABLE_RX

    def encode_simple(self, codec: 'Codec') -> str:
        '''
        Encode ourself as a string, return that value.
        '''
        return self._ENCODE_SIMPLE_FMT.format(type_field=self.type_field(),
                                              value=self.value)

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(
            f"{self.klass}.encode_complex() is not implemented.")

    @classmethod
    def decode_simple(klass: Type['SerializableId'],
                      data:  str,
                      codec: 'Codec') -> 'SerializableId':
        '''
        Decode ourself from a string, return a new instance of `klass` as
        the result of the decoding.

        Raises:
          - ValueError if value isn't a hyphen-separated, base 16 int string.
        '''
        rx = klass._get_decode_rx()
        if not rx:
            msg = (f"{klass.klass}: No decode regex - "
                   f"- cannot decode: {data}")
            error = ValueError(msg, data)
            raise log.exception(error, msg)

        # Have regex, but does it work on data?
        match = rx.match(data)
        if not match or not match.group('value'):
            msg = (f"{klass.klass}: Decode regex failed to match "
                   f"data - cannot decode: {data}")
            error = ValueError(msg, data)
            raise log.exception(error, msg)

        # Get actual value from match, remove nice separators so we have just a
        # hex number...
        hex_str = match.group('value')
        hex_str = hex_str.replace('-', '')
        # Convert that into an actual number.
        # Could throw a value error if something's wrong...
        hex_value = int(hex_str, 16)

        # And now we should be able to decode.
        return klass._decode_simple_init(hex_value, codec)

    @classmethod
    def _decode_simple_init(klass: Type['SerializableId'],
                            value: int,
                            codec: 'Codec') -> 'SerializableId':
        '''
        Subclasses can override this if they have a different constructor.
        '''
        decoded = klass(None, None,
                        decoding=True,
                        decoded_value=value)
        return decoded

    @classmethod
    def decode_complex(klass: Type['SerializableId'],
                       value: EncodedComplex,
                       codec: 'Codec',
                       instance: Optional['SerializableId'] = None
                       ) -> 'SerializableId':
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(f"{klass.klass}.encode_complex() is "
                                  "not implemented.")

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
        raise NotImplementedError(f"{self.klass}._format() is "
                                  "not implemented.")

    def __str__(self) -> str:
        return f'{self.klass}:{self._format_}'

    def __repr__(self) -> str:
        return f'{self.name}:{self._format_}'
