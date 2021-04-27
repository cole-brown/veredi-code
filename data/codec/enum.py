# coding: utf-8

'''
Encodable Wrappers for Enums.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Type, Any,
                    TypeVar, Generic,
                    Callable, Dict, Tuple)
if TYPE_CHECKING:
    from .codec import Codec


import re
import enum as py_enum
import inspect


from veredi.logs  import log
from veredi.base.strings import label

from .const       import EncodedComplex, Encoding
from .encodable   import Encodable


# -----------------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------------

EnumEncode = TypeVar('EnumEncode',
                     py_enum.Enum,
                     py_enum.Flag)
'''
Types that EnumWrap supports.
'''


EnumWrapTypesTuple = (py_enum.Enum, py_enum.IntEnum,
                      py_enum.Flag, py_enum.IntFlag)
'''
The enum types that should be wrapped (i.e. all of them).

Could reduce to just EnumEncode's two, or just 'py_enum.Enum', but this is more
explicit...
'''


# -----------------------------------------------------------------------------
# Constants & Variables
# -----------------------------------------------------------------------------

_WRAPPER_CLASS_FMT: str = "Wrap{name}"


_WRAPPED_ENUMS: Dict[Type[EnumEncode], 'EnumWrap'] = {}
'''
All the enums that have gone through our `encodable()` function.
'''

_DOTTED: label.DotStr = label.normalize('veredi.data.codec.enum')


# -----------------------------------------------------------------------------
# Enum Encoding Descriptor & Base Class
# -----------------------------------------------------------------------------

class EnumDescriptor:
    '''
    Provider for the wrapped enum class in EnumWrap.
    '''

    # -------------------------------------------------------------------------
    # Class Vars
    # -------------------------------------------------------------------------

    def __init__(self,
                 wrap:            Union[py_enum.Enum, Any, None],
                 type:            Optional[py_enum.Enum],
                 name_descriptor: str = None) -> None:
        self.name:       str                = name_descriptor
        self.wrap_type:  Type[py_enum.Enum] = type
        self.wrap_value: py_enum.Enum       = None

        self._set(wrap)

    def __get__(self,
                instance: Optional[Any],
                owner:    Type[Any]) -> label.DotStr:
        '''
        Returns the enum class we wrap.
        '''
        return self.wrap_value

    def _set(self, input: Optional[py_enum.Enum]) -> None:
        '''
        Set `self.wrap_value` based on `input`.

        Will just set if given the actual enum value. Will try to create/get
        the enum value from `input` otherwise.
        '''
        if input in EnumWrapTypesTuple:
            self.wrap_value = input
        elif input:
            # Got the wrap_type.value... hopefully.
            # Use it to get the enum const.
            self.wrap_value = self.wrap_type(input)

    def __set__(self,
                instance: Optional[Any],
                wrap:     Optional[py_enum.Enum]) -> None:
        '''
        Setter should not be used during normal operation...
        Wrapped enum should not change.
        '''
        self._set(wrap)

    def __set_name__(self, owner: Type[Any], name: str) -> None:
        '''
        Save our descriptor variable's name in its owner's class.
        '''
        self.name = name

    def __str__(self) -> str:
        return f"{self.wrap_type}:{self.wrap_value}"

    def __repr__(self) -> str:
        return f"<{str(self)}>"


class EnumWrap(Encodable, Generic[EnumEncode]):
    '''
    A wrapper class to hold the Encodable functions and dotted/name
    descriptors.
    '''

    enum: EnumDescriptor = EnumDescriptor(None, None, None)
    type: Type[py_enum.Enum] = None

    def __init__(self, wrap_enum: Optional[py_enum.Enum]) -> None:
        if wrap_enum:
            self.enum = wrap_enum

    @classmethod
    def encode_on(klass: 'EnumWrap') -> str:
        '''
        What is this class encoding/decoding?
        e.g. 'value' or 'name' or...?
        '''
        raise NotImplementedError(f"{klass.klass} needs to "
                                  "implement `encode_on()`!")

    @classmethod
    def wrap_type(klass: 'EnumWrap') -> Type[py_enum.Enum]:
        '''
        Returns the class type of the enum we are wrapping.
        '''
        return klass.enum.wrap_type

    def __str__(self) -> str:
        return f"{self.klass}['{self.dotted}','{self.name}']:{self.enum}"

    def __repr__(self) -> str:
        return f"<{str(self)}>"


# -----------------------------------------------------------------------------
# Registration Helper
# -----------------------------------------------------------------------------

def _to_class(coi: Union[EnumEncode, Type[EnumEncode]]
              ) -> Tuple[Type[EnumEncode], bool]:
    '''
    Convert class or instance `coi` to a class.

    Returns a tuple of (class, `coi`-is-class)
    '''
    if inspect.isclass(coi):
        return coi, True
    return coi.__class__, False


def _known(coi: Union['EnumWrap', Type['EnumWrap']]) -> bool:
    '''
    Returns true if we have class or instance `coi` as a known wrapped enum.
    '''
    klass, _ = _to_class(coi)
    return klass in _WRAPPED_ENUMS


def needs_wrapped(cls_or_instance: Union[Encodable, Type[Encodable]]) -> bool:
    '''
    Returns true if the `klass` needs an EnumWrap for providing its Encodable
    functionality.
    '''
    klass, _ = _to_class(cls_or_instance)
    return issubclass(klass, EnumWrapTypesTuple)


def needs_unwrapped(cls_or_instance: Union[Encodable, Type[Encodable]]
                    ) -> bool:
    '''Returns true if this `klass` is an EnumWrap that should be unwrapped.'''
    klass, _ = _to_class(cls_or_instance)
    return issubclass(klass, EnumWrap)


def is_encodable(cls_or_instance: Union[Encodable, Type[Encodable]]) -> bool:
    '''
    Returns true if this `klass` is an enum registered with a WrapEnum.
    '''
    return (needs_wrapped(cls_or_instance)
            and _known(cls_or_instance))


def is_decodable(cls_or_instance: Union[Encodable, Type[Encodable]]) -> bool:
    '''
    Returns true if this `klass` is registered with a WrapEnum.
    '''
    return needs_unwrapped(cls_or_instance)


def wrap(cls_or_instance: Union[EnumEncode, Type[EnumEncode]]
         ) -> Union['EnumWrap', Type['EnumWrap']]:
    '''
    Returns the EnumWrap class for this enum `klass`.

    Returns None if not found.
    '''
    # Get Class:
    klass, is_class = _to_class(cls_or_instance)

    # Do we know of this guy?
    wrap_type = _WRAPPED_ENUMS.get(klass, None)

    # Return what we were given: instance or class type
    if is_class:
        log.data_processing(label.normalize(_DOTTED, 'wrap'),
                            "wrap:\n"
                            "  --in--> {}\n"
                            "  --type- {}\n"
                            "  <-type- {}",
                            cls_or_instance, wrap_type,
                            wrap_type)
        return wrap_type

    wrap_instance = wrap_type(cls_or_instance)
    log.data_processing(label.normalize(_DOTTED, 'wrap'),
                        "wrap:\n"
                        "  -in--> {}\n"
                        "  -type- {}\n"
                        "  <-out- {}",
                        cls_or_instance, wrap_type,
                        wrap_instance)
    return wrap_instance


def unwrap(instance: Union['EnumWrap', 'Encodable']) -> EnumEncode:
    '''
    If `instance` is an EnumWrap, returns the enum instance/value that the
    EnumWrap `instance` contains. Else returns `instance`.
    '''
    if not isinstance(instance, EnumWrap):
        log.data_processing(label.normalize(_DOTTED, 'unwrap'),
                            "unwrap:\n"
                            "  --ignore-> {}\n"
                            "  <-ignore-- {}",
                            instance, instance)
        return instance

    log.data_processing(label.normalize(_DOTTED, 'unwrap'),
                        "unwrap:\n"
                        "  -in--> {}\n"
                        "  <-out- {}",
                        instance, instance.enum)
    return instance.enum


# -----------------------------------------------------------------------------
# Wrapper Class Creator
# -----------------------------------------------------------------------------

def encodable(klass:               Type[EnumEncode],
              name_dotted:         Optional[label.LabelInput] = None,
              name_string:         Optional[str]              = None,
              name_klass:          Optional[str]              = None,
              enum_encode_type:    'EnumWrap'                 = None
              ) -> Type['EnumWrap']:
    '''
    Helper for creating an EnumWrap subclass for a specific Enum that needs to
    be Encodable. The enum itself cannot be an Encodable, but it will use this
    wrapper class to provide its Encodable functionality.

    Required:
      - `name_dotted`
      - `name_string`
      - `enum_encode_type`

    Optional:
      - `name_klass`
        + Will be `Wrap{wrapped_class_name}` if not supplied.

    Several helper/wrapper classes exist to be supplied as `enum_encode_type`:
      - FlagEncodeValue
      - FlagEncodeName
      - EnumEncodeName

    Does not exist yet; can be quickly made from EnumEncodeName
    and FlagEncodeValue:
      - EnumEncodeValue
    '''
    # ------------------------------
    # Sanity Checks
    # ------------------------------
    if not issubclass(klass, EnumWrapTypesTuple):
        msg = (f"{klass.klass}: `encodable` decorator should only be "
               f"used on enum classes: {EnumWrapTypesTuple}")
        error = ValueError(msg, klass, enum_encode_type)
        raise log.exception(error, msg,
                            data={
                                'class': klass,
                                'dotted': name_dotted,
                                'name': name_string,
                                'klass': name_klass,
                                'wrapper': enum_encode_type,
                            })

    if not enum_encode_type:
        msg = (f"{klass.klass}: `encodable` decorator needs an "
               "`enum_encode_type` class to use for the wrapper.")
        error = ValueError(msg, klass, enum_encode_type)
        raise log.exception(error, msg,
                            data={
                                'class': klass,
                                'dotted': name_dotted,
                                'name': name_string,
                                'klass': name_klass,
                                'wrapper': enum_encode_type,
                            })

    if not issubclass(enum_encode_type, EnumWrap):
        msg = (f"{klass.klass}: `encodable` decorator needs an "
               "`enum_encode_type` that is an EnumWrap "
               "or a subclass.")
        error = ValueError(msg, klass, enum_encode_type)
        raise log.exception(error, msg,
                            data={
                                'class': klass,
                                'dotted': name_dotted,
                                'name': name_string,
                                'klass': name_klass,
                                'wrapper': enum_encode_type,
                            })

    # ------------------------------
    # Define Wrapper Class
    # ------------------------------
    class Wrapper(enum_encode_type,
                  name_dotted=name_dotted,
                  name_string=name_string,
                  name_klass=name_klass):
        '''
        Wrapper class for an enum that wants to be encodable.
        '''
        enum: EnumDescriptor = EnumDescriptor(None, klass, None)
        '''Init EnumDescriptor with the wrapper's class type.'''
        type: Type[py_enum.Enum] = klass
        '''Wrapped enum's type.'''

    # Dynamically set class name to something more specific
    # than `Wrapper`.
    name = (
        # Prefer user supplied.
        name_klass
        if name_klass else
        # Else build one using our formatting string.
        _WRAPPER_CLASS_FMT.format(name=klass.__name__)
    )

    Wrapper.__name__ = name
    Wrapper.__qualname__ = name

    global _WRAPPED_ENUMS
    _WRAPPED_ENUMS[klass] = Wrapper

    log.group_multi([log.Group.REGISTRATION, log.Group.DATA_PROCESSING],
                    label.normalize(_DOTTED, 'encodable'),
                    "encodable enum:\n"
                    "             klass: {}\n"
                    "       name_dotted: {}\n"
                    "       name_string: {}\n"
                    "        name_klass: {}\n"
                    "  enum_encode_type: {}\n"
                    "      <--  wrapper: {}",
                    klass,
                    name_dotted,
                    name_string,
                    name_klass,
                    enum_encode_type,
                    Wrapper)

    # ------------------------------
    # Done; return the new Wrapper.
    # ------------------------------
    return Wrapper


# -----------------------------------------------------------------------------
# By VALUE: Flag Enum
# -----------------------------------------------------------------------------

class FlagEncodeValue(EnumWrap[py_enum.Flag]):
    '''
    Helpers for encoding a flag enum for codec support.

    NOTE: This encodes the /value/ of the enum. If encoded and saved, this
    means the enum values CANNOT be changed. It is better for enums-in-flight
    that just never get saved to disk.
    '''

    _ENCODABLE_RX_FLAGS: re.RegexFlag = re.IGNORECASE
    '''Flags used when creating _ENCODABLE_RX.'''

    _ENCODABLE_RX_STR_FMT: str = r'^{type_field}:(?P<value>\d+)$'
    '''
    Format string for MsgType regex. Type field, followed by the flag(s) value
    as int.
    '''

    _ENCODABLE_RX_STR: str = None
    '''
    Actual string used to compile regex - created from _ENCODABLE_RX_STR_FMT.
    '''

    _ENCODABLE_RX: re.Pattern = None
    '''
    Compiled regex pattern for decoding MonotonicIds.
    '''

    _ENCODE_SIMPLE_FMT: str = '{type_field}:{value}'
    '''
    String format for encoding MonotonicIds.
    '''

    # -------------------------------------------------------------------------
    # EnumEncode
    # -------------------------------------------------------------------------

    @classmethod
    def encode_on(klass: 'EnumWrap') -> str:
        '''
        This class is encoding on the enum's value.
        '''
        return 'value'

    # -------------------------------------------------------------------------
    # Encodable
    # -------------------------------------------------------------------------

    @classmethod
    def encoding(klass: 'FlagEncodeValue') -> Encoding:
        '''We are too simple to bother with being a complex type.'''
        return Encoding.SIMPLE

    @classmethod
    def _get_decode_str_rx(klass: 'FlagEncodeValue') -> Optional[str]:
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
    def _get_decode_rx(klass: 'FlagEncodeValue') -> re.Pattern:
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
        encoded = self._ENCODE_SIMPLE_FMT.format(type_field=self.type_field(),
                                                 value=self.enum.value)
        # print(f"FlagEncodeValue.encode_simple: {self} -> {encoded}")
        return encoded

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(
            f"{self.klass}.encode_complex() is not implemented.")

    @classmethod
    def decode_simple(klass: 'FlagEncodeValue',
                      data:  str,
                      codec: 'Codec') -> 'FlagEncodeValue':
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
                   f"data - cannot decode: {data}")
            error = ValueError(msg, data)
            raise log.exception(error, msg)

        # Have regex, have match. Init enum (not wrapping) from it.
        decoded = klass.type(int(match.group('value')))
        # print(f"FlagEncodeValue.decode_simple: {data} -> {decoded}")
        return decoded

    @classmethod
    def decode_complex(klass: 'FlagEncodeValue',
                       value: EncodedComplex,
                       codec: 'Codec',
                       instance: Optional['FlagEncodeValue'] = None
                       ) -> 'FlagEncodeValue':
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(f"{klass.klass}.decode_complex() is "
                                  "not implemented.")


# -----------------------------------------------------------------------------
# By NAME: Flag Enum
# -----------------------------------------------------------------------------

class FlagEncodeName(EnumWrap[py_enum.Flag]):
    '''
    Helpers for encoding a flag enum for codec support.

    NOTE: This encodes the /name/ of the enum. If encoded and saved, this means
    the enum names CANNOT be changed. Make sure you like them or be prepared to
    write migration scripts maybe I guess.
    '''

    _ENCODABLE_RX_FLAGS: re.RegexFlag = re.IGNORECASE
    '''Flags used when creating _ENCODABLE_RX.'''

    _ENCODABLE_RX_STR_FMT: str = r'^{type_field}:(?P<names>[|\w]+)$'
    '''
    Format string for MsgType regex. Type field, followed by the flag(s) value
    as strings separated by pipes. Just get the whole pipe-separated thing as
    one big chunk... My regex-fu is insufficient for chopping up the names.
    Names examples:
      - JEFF
      - JEFF|JEFFORY
      - JEFF|JEFFORY|GEOFF|...
    '''

    _ENCODABLE_RX_STR: str = None
    '''
    Actual string used to compile regex - created from _ENCODABLE_RX_STR_FMT.
    '''

    _ENCODABLE_RX: re.Pattern = None
    '''
    Compiled regex pattern for decoding MonotonicIds.
    '''

    _ENCODE_SIMPLE_FMT: str = '{type_field}:{names}'
    '''
    String format for encoding MonotonicIds.
    '''

    # -------------------------------------------------------------------------
    # EnumWrap
    # -------------------------------------------------------------------------

    @classmethod
    def encode_on(klass: 'EnumWrap') -> str:
        '''
        This class is encoding on the enum's value.
        '''
        return 'name'

    # -------------------------------------------------------------------------
    # Encodable
    # -------------------------------------------------------------------------

    @classmethod
    def encoding(klass: 'FlagEncodeName') -> Encoding:
        '''We are too simple to bother with being a complex type.'''
        return Encoding.SIMPLE

    @classmethod
    def _get_decode_str_rx(klass: 'FlagEncodeName') -> Optional[str]:
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
    def _get_decode_rx(klass: 'FlagEncodeName') -> re.Pattern:
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
        # These will be all our separated flags' names.
        names = []

        # Haven't found a better way without using power-of-two assumption for
        # names that I don't want to because we're just a ...
        #
        # Iterate over /all/ flags defined.
        for each in self.enum.__class__:
            if each in self.enum:
                names.append(each.name)

        if not names:
            msg = (f"{self.klass}: No enum values found?! "
                   f"'{str(self)}' didn't resolve to any of its class's "
                   "enums values.")
            error = ValueError(msg, self, names)
            raise log.exception(error, msg)

        # Turn list of names into one string for final return string.
        return self._ENCODE_SIMPLE_FMT.format(type_field=self.type_field(),
                                              names='|'.join(names))

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(
            f"{self.klass}.encode_complex() is not implemented.")

    @classmethod
    def decode_simple(klass: 'FlagEncodeName',
                      data:  str,
                      codec: 'Codec') -> 'FlagEncodeName':
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
        if not match or not match.group('names'):
            msg = (f"{klass.klass}: Decode regex failed to match "
                   f"data - cannot decode: {data}")
            error = ValueError(msg, data)
            raise log.exception(error, msg)

        # Have regex, have match.
        # Chop up match by separator to build flags up.
        names = match.group('names').split('|')
        total = None
        # Ignore the blank ones. Use the rest to OR together flag enums.
        for name in filter(None, names):
            flag = klass.type[name]
            if total is None:
                total = flag
            else:
                total = total | flag

        # Return final OR'd enum instance.
        return total

    @classmethod
    def decode_complex(klass: 'FlagEncodeName',
                       value: EncodedComplex,
                       codec: 'Codec',
                       instance: Optional['FlagEncodeName'] = None
                       ) -> 'FlagEncodeName':
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(f"{klass.klass}.decode_complex() is "
                                  "not implemented.")


# -----------------------------------------------------------------------------
# By VALUE: Enum
# -----------------------------------------------------------------------------

# Implement when needed.
# class EnumEncodeValue(EnumWrap):


# -----------------------------------------------------------------------------
# By NAME: Enum
# -----------------------------------------------------------------------------

class EnumEncodeName(EnumWrap[py_enum.Enum]):
    '''
    Helpers for encoding a enum enum for codec support.

    NOTE: This encodes the /name/ of the enum. If encoded and saved, this means
    the enum names CANNOT be changed. Make sure you like them or be prepared to
    write migration scripts maybe I guess.
    '''

    _ENCODABLE_RX_FLAGS: re.RegexFlag = re.IGNORECASE
    '''Flags used when creating _ENCODABLE_RX.'''

    _ENCODABLE_RX_STR_FMT: str = r'^{type_field}:(?P<name>[_\w]+)$'
    '''
    Format string for MsgType regex. Type field, followed by the name of the
    enum.
    '''

    _ENCODABLE_RX_STR: str = None
    '''
    Actual string used to compile regex - created from _ENCODABLE_RX_STR_FMT.
    '''

    _ENCODABLE_RX: re.Pattern = None
    '''
    Compiled regex pattern for decoding MonotonicIds.
    '''

    _ENCODE_SIMPLE_FMT: str = '{type_field}:{name}'
    '''
    String format for encoding MonotonicIds.
    '''

    # -------------------------------------------------------------------------
    # EnumWrap
    # -------------------------------------------------------------------------

    @classmethod
    def encode_on(klass: 'EnumWrap') -> str:
        '''
        This class is encoding on the enum's value.
        '''
        return 'name'

    # -------------------------------------------------------------------------
    # Encodable
    # -------------------------------------------------------------------------

    @classmethod
    def encoding(klass: 'EnumEncodeName') -> Encoding:
        '''We are too simple to bother with being a complex type.'''
        return Encoding.SIMPLE

    @classmethod
    def _get_decode_str_rx(klass: 'EnumEncodeName') -> Optional[str]:
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
    def _get_decode_rx(klass: 'EnumEncodeName') -> re.Pattern:
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
        # This is our enum value/instance's name.
        name = self.enum.name

        if not name:
            msg = (f"{self.klass}: No enum name?!"
                   f"'{str(self)}' didn't resolve to any of its class's "
                   "enums values.")
            error = ValueError(msg, self, name)
            raise log.exception(error, msg)

        # Encode it.
        return self._ENCODE_SIMPLE_FMT.format(type_field=self.type_field(),
                                              name=name)

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(
            f"{self.klass}.encode_complex() is not implemented.")

    @classmethod
    def decode_simple(klass: 'EnumEncodeName',
                      data:  str,
                      codec: 'Codec') -> 'EnumEncodeName':
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
        if not match or not match.group('name'):
            msg = (f"{klass.klass}: Decode regex failed to match "
                   f"data - cannot decode: {data}")
            error = ValueError(msg, data)
            raise log.exception(error, msg)

        # Have regex, have match.
        # Turn into an enum value.
        name = match.group('name')
        flag = klass.type[name]
        return flag

    @classmethod
    def decode_complex(klass: 'EnumEncodeName',
                       value: EncodedComplex,
                       codec: 'Codec',
                       instance: Optional['EnumEncodeName'] = None
                       ) -> 'EnumEncodeName':
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(f"{klass.klass}.decode_complex() is "
                                  "not implemented.")
