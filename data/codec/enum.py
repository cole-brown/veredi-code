# coding: utf-8

'''
Encodable Mixins for Enums.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional


import re
import enum


from veredi.logs  import log
from veredi.base.strings import label

from .const       import EncodedComplex, Encoding
from .encodable   import Encodable
from .codec       import Codec


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# By VALUE: Flag Enum
# -----------------------------------------------------------------------------

class FlagEncodeValueMixin(Encodable):
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

    @classmethod
    def type_field(klass: 'FlagEncodeValueMixin') -> str:
        '''
        A short, unique name for encoding an instance into a field in a dict.
        Override this if you don't like what veredi.base.label.auto() and
        veredi.base.label.munge_to_short() do for your type field.
        '''
        return label.munge_to_short(label.auto(klass))

    @classmethod
    def encoding(klass: 'FlagEncodeValueMixin') -> Encoding:
        '''We are too simple to bother with being a complex type.'''
        return Encoding.SIMPLE

    @classmethod
    def _get_decode_str_rx(klass: 'FlagEncodeValueMixin') -> Optional[str]:
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
    def _get_decode_rx(klass: 'FlagEncodeValueMixin') -> re.Pattern:
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
        # print(f"FlagEncodeValueMixin.encode_simple: {self} -> {encoded}")
        return encoded

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(
            f"{self.__class__.__name__}.encode_complex() is not implemented.")

    @classmethod
    def decode_simple(klass: 'FlagEncodeValueMixin',
                      data:  str,
                      codec: 'Codec') -> 'FlagEncodeValueMixin':
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
        # print(f"FlagEncodeValueMixin.decode_simple: {data} -> {decoded}")
        return decoded

    @classmethod
    def decode_complex(klass: 'FlagEncodeValueMixin',
                       value: EncodedComplex,
                       codec: 'Codec',
                       instance: Optional['FlagEncodeValueMixin'] = None
                       ) -> 'FlagEncodeValueMixin':
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(f"{klass.__name__}.decode_complex() is "
                                  "not implemented.")


# -----------------------------------------------------------------------------
# By NAME: Flag Enum
# -----------------------------------------------------------------------------

class FlagEncodeNameMixin(Encodable):
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

    @classmethod
    def type_field(klass: 'FlagEncodeNameMixin') -> str:
        '''
        A short, unique name for encoding an instance into a field in a dict.
        Override this if you don't like what veredi.base.label.auto() and
        veredi.base.label.munge_to_short() do for your type field.
        '''
        return label.munge_to_short(label.auto(klass))

    @classmethod
    def encoding(klass: 'FlagEncodeNameMixin') -> Encoding:
        '''We are too simple to bother with being a complex type.'''
        return Encoding.SIMPLE

    @classmethod
    def _get_decode_str_rx(klass: 'FlagEncodeNameMixin') -> Optional[str]:
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
    def _get_decode_rx(klass: 'FlagEncodeNameMixin') -> re.Pattern:
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
        # names that I don't want to because we're just a mixin...
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
    def decode_simple(klass: 'FlagEncodeNameMixin',
                      data:  str,
                      codec: 'Codec') -> 'FlagEncodeNameMixin':
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
    def decode_complex(klass: 'FlagEncodeNameMixin',
                       value: EncodedComplex,
                       codec: 'Codec',
                       instance: Optional['FlagEncodeNameMixin'] = None
                       ) -> 'FlagEncodeNameMixin':
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(f"{klass.__name__}.decode_complex() is "
                                  "not implemented.")


# -----------------------------------------------------------------------------
# By VALUE: Enum
# -----------------------------------------------------------------------------

# Implement when needed.
# class EnumEncodeValueMixin(Encodable):


# -----------------------------------------------------------------------------
# By NAME: Enum
# -----------------------------------------------------------------------------

class EnumEncodeNameMixin(Encodable):
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

    @classmethod
    def type_field(klass: 'EnumEncodeNameMixin') -> str:
        '''
        A short, unique name for encoding an instance into a field in a dict.
        Override this if you don't like what veredi.base.label.auto() and
        veredi.base.label.munge_to_short() do for your type field.
        '''
        return label.munge_to_short(label.auto(klass))

    @classmethod
    def encoding(klass: 'EnumEncodeNameMixin') -> Encoding:
        '''We are too simple to bother with being a complex type.'''
        return Encoding.SIMPLE

    @classmethod
    def _get_decode_str_rx(klass: 'EnumEncodeNameMixin') -> Optional[str]:
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
    def _get_decode_rx(klass: 'EnumEncodeNameMixin') -> re.Pattern:
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
    def decode_simple(klass: 'EnumEncodeNameMixin',
                      data:  str,
                      codec: 'Codec') -> 'EnumEncodeNameMixin':
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
    def decode_complex(klass: 'EnumEncodeNameMixin',
                       value: EncodedComplex,
                       codec: 'Codec',
                       instance: Optional['EnumEncodeNameMixin'] = None
                       ) -> 'EnumEncodeNameMixin':
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(f"{klass.__name__}.decode_complex() is "
                                  "not implemented.")
