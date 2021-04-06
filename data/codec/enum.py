# coding: utf-8

'''
Encodable Wrappers for Enums.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Type, Any


import re
import enum as py_enum


from veredi.logs  import log
from veredi.base.strings import label

from .const       import EncodedComplex, Encoding
from .encodable   import Encodable
from .codec       import Codec


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_WRAPPER_CLASS_FMT: str = "Wrapper{name}"


# -----------------------------------------------------------------------------
# Enum Encoding Descriptor & Base Class
# -----------------------------------------------------------------------------

class EnumDescriptor:
    '''
    Provider for the wrapped enum class in EnumEncodableWrapper.
    '''

    def __init__(self,
                 wrapped: Optional[py_enum.Enum],
                 name_descriptor: str = None) -> None:
        self.name: str = name_descriptor
        self.wrapped: py_enum.Enum = wrapped

    def __get__(self,
                instance: Optional[Any],
                owner:    Type[Any]) -> label.DotStr:
        '''
        Returns the enum class we wrap.
        '''
        return self.wrapped

    def __set__(self,
                instance: Optional[Any],
                wrapped:  Optional[py_enum.Enum]) -> None:
        '''
        Setter should not be used during normal operation...
        Wrapped enum should not change.
        '''
        self.wrapped = wrapped

    def __set_name__(self, owner: Type[Any], name: str) -> None:
        '''
        Save our descriptor variable's name in its owner's class.
        '''
        self.name = name


class EnumEncodableWrapper(Encodable):
    '''
    A wrapper class to hold the Encodable functions and dotted/name
    descriptors.
    '''

    enum: EnumDescriptor = EnumDescriptor(None)

    def __init__(self, wrap_enum: Optional[Type[py_enum.Enum]]) -> None:
        if wrap_enum:
            self.enum = wrap_enum

    @classmethod
    def encode_on(klass: 'EnumEncodableWrapper') -> str:
        '''
        What is this class encoding/decoding?
        e.g. 'value' or 'name' or...?
        '''
        raise NotImplementedError(f"{klass.__name__} needs to "
                                  "implement `encode_on()`!")


# -----------------------------------------------------------------------------
# Decorator
# -----------------------------------------------------------------------------

def encodable(name_dotted:         Optional[label.LabelInput] = None,
              name_string:         Optional[str]              = None,
              name_klass:          Optional[str]              = None,
              enum_encode_type:    'EnumEncodableWrapper'     = None):
    '''
    Decorator for wrapping an Enum with Encodable support.

    Required:
      - `name_dotted`
      - `name_string`
      - `enum_encode_type`

    Optional:
      - `name_klass`
        + Will be `Wrapper{wrapped_class_name}` if not supplied.

    Several helper/wrapper classes exist to be supplied as `enum_encode_type`:
      - FlagEncodeValue
      - FlagEncodeName
      - EnumEncodeName

    Does not exist yet; can be quickly made from EnumEncodeName
    and FlagEncodeValue:
      - EnumEncodeValue
    '''
    def decorator(klass) -> Type['EnumEncodableWrapper']:
        # ------------------------------
        # Sanity Checks
        # ------------------------------
        if not issubclass(klass, py_enum.Enum):
            msg = (f"{klass.__name__}: `encodable` decorator should only be "
                   "used on enum classes.")
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
            msg = (f"{klass.__name__}: `encodable` decorator needs an "
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

        if not issubclass(enum_encode_type, EnumEncodableWrapper):
            msg = (f"{klass.__name__}: `encodable` decorator needs an "
                   "`enum_encode_type` that is EnumEncodableWrapper "
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
            enum: EnumDescriptor = EnumDescriptor(klass)

            def __init__(self) -> None:
                super().__init__(klass)

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

        # ------------------------------
        # Done; return the new Wrapper.
        # ------------------------------
        return Wrapper

    return decorator


# -----------------------------------------------------------------------------
# By VALUE: Flag Enum
# -----------------------------------------------------------------------------

class FlagEncodeValue(EnumEncodableWrapper):
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
    def encode_on(klass: 'EnumEncodableWrapper') -> str:
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
                msg = (f"{klass.__name__}: Cannot get decode regex "
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
                                                 value=self.value)
        # print(f"FlagEncodeValue.encode_simple: {self} -> {encoded}")
        return encoded

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(
            f"{self.__class__.__name__}.encode_complex() is not implemented.")

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
            msg = (f"{klass.__name__}: No decode regex - "
                   f"- cannot decode: {data}")
            error = ValueError(msg, data)
            raise log.exception(error, msg)

        # Have regex, but does it work on data?
        match = rx.match(data)
        if not match or not match.group('value'):
            msg = (f"{klass.__name__}: Decode regex failed to match "
                   f"data - cannot decode: {data}")
            error = ValueError(msg, data)
            raise log.exception(error, msg)

        # Have regex, have match. Build instance.
        decoded = klass(int(match.group('value')))
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
        raise NotImplementedError(f"{klass.__name__}.decode_complex() is "
                                  "not implemented.")


# -----------------------------------------------------------------------------
# By NAME: Flag Enum
# -----------------------------------------------------------------------------

class FlagEncodeName(EnumEncodableWrapper):
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
    # EnumEncodableWrapper
    # -------------------------------------------------------------------------

    @classmethod
    def encode_on(klass: 'EnumEncodableWrapper') -> str:
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
                msg = (f"{klass.__name__}: Cannot get decode regex "
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
        for each in self.__class__:
            if each in self:
                names.append(each.name)

        if not names:
            msg = (f"{self.__class__.__name__}: No enum values found?! "
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
            f"{self.__class__.__name__}.encode_complex() is not implemented.")

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
            msg = (f"{klass.__name__}: No decode regex - "
                   f"- cannot decode: {data}")
            error = ValueError(msg, data)
            raise log.exception(error, msg)

        # Have regex, but does it work on data?
        match = rx.match(data)
        if not match or not match.group('names'):
            msg = (f"{klass.__name__}: Decode regex failed to match "
                   f"data - cannot decode: {data}")
            error = ValueError(msg, data)
            raise log.exception(error, msg)

        # Have regex, have match.
        # Chop up match by separator to build flags up.
        names = match.group('names').split('|')
        total = None
        # Ignore the blank ones. Use the rest to OR together flag enums.
        for name in filter(None, names):
            flag = klass[name]
            if total is None:
                total = flag
            else:
                total = total | flag

        # Return final OR'd total.
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
        raise NotImplementedError(f"{klass.__name__}.decode_complex() is "
                                  "not implemented.")


# -----------------------------------------------------------------------------
# By VALUE: Enum
# -----------------------------------------------------------------------------

# Implement when needed.
# class EnumEncodeValue(EnumEncodableWrapper):


# -----------------------------------------------------------------------------
# By NAME: Enum
# -----------------------------------------------------------------------------

class EnumEncodeName(EnumEncodableWrapper):
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
    # EnumEncodableWrapper
    # -------------------------------------------------------------------------

    @classmethod
    def encode_on(klass: 'EnumEncodableWrapper') -> str:
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
                msg = (f"{klass.__name__}: Cannot get decode regex "
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
        name = self.name

        if not name:
            msg = (f"{self.__class__.__name__}: No enum name?!"
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
            f"{self.__class__.__name__}.encode_complex() is not implemented.")

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
            msg = (f"{klass.__name__}: No decode regex - "
                   f"- cannot decode: {data}")
            error = ValueError(msg, data)
            raise log.exception(error, msg)

        # Have regex, but does it work on data?
        match = rx.match(data)
        if not match or not match.group('name'):
            msg = (f"{klass.__name__}: Decode regex failed to match "
                   f"data - cannot decode: {data}")
            error = ValueError(msg, data)
            raise log.exception(error, msg)

        # Have regex, have match.
        # Turn into an enum value.
        name = match.group('name')
        return klass[name]

    @classmethod
    def decode_complex(klass: 'EnumEncodeName',
                       value: EncodedComplex,
                       codec: 'Codec',
                       instance: Optional['EnumEncodeName'] = None
                       ) -> 'EnumEncodeName':
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(f"{klass.__name__}.decode_complex() is "
                                  "not implemented.")
