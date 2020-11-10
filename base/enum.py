# coding: utf-8

'''
Mixins and/or Base/Basic Enum Things
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, Type, Dict


import enum
import re


from veredi.logger               import log
from veredi.base                 import dotted
from veredi.data.codec.encodable import (Encodable,
                                         EncodedComplex)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class FlagCheckMixin:
    '''
    Helper functions for checking if an instance of a enum.Flag has specific
    enum.Flag flags set.
    '''

    def has(self, flag: 'FlagCheckMixin'):
        '''
        Returns true if this enum has all the flags specified.
        '''
        return ((self & flag) == flag)

    def any(self, *flags: 'FlagCheckMixin') -> bool:
        '''
        Returns true if this instance has any of the flags specified.

        Can still require multiple by OR'ing e.g.:
          type.any(JeffFlag.JEFF | JeffFlag.JEFFORY, JeffFlag.GEOFF)

        That will look for either a JEFF that is a JEFFORY, or a GEOFF.
        '''
        for each in flags:
            if self.has(each):
                return True
        return False

    @property
    def is_solo(flag: 'FlagCheckMixin') -> bool:
        '''
        Returns True if this instance is exactly one flag bit.
        Returns False if this instance has:
          - More than one bit set.
          - Zero bits set.
          - Invalid `flag` value (e.g. None).
        '''
        # ---
        # Simple Cases
        # ---

        if not isinstance(flag, enum.Flag):
            msg = (f"FlagCheckMixin.is_solo: '{flag}' is not an "
                   "enum.Flag derived type.")
            error = ValueError(msg, flag)
            raise log.exception(error,
                                None,
                                msg)

        # A nice clean-looking way of doing, but could miss some cases. For
        # example, if a flag mask exists as a value in the enum and the flag
        # value passed in happens to be equal to that mask.
        if flag not in flag.__class__:
            return False

        # ---
        # Not As Simple Case
        # ---

        # Count the bits set to get a sure answer. Apparently this ridiculous
        # "decimal number -> binary string -> count characters" is fast for
        # small, non-parallel/vectorizable things.
        #   https://stackoverflow.com/a/9831671/425816
        bits_set = bin(flag.value).count("1")
        return bits_set == 1


class FlagSetMixin:
    '''
    Helper functions for setting, unsetting flags in an enum.Flag instance.
    '''

    def set(self, flag: 'FlagSetMixin') -> bool:
        '''
        Returns an instance of this enum.Flag with `flag` added
        (OR'd into self).
        '''
        return self | flag

    def unset(self, flag: 'FlagSetMixin') -> bool:
        '''
        Returns an instance of this enum.Flag with `flag` removed
        (NOT-AND'd out of self).
        '''
        return self & ~flag


# -----------------------------------------------------------------------------
# Encodable
# -----------------------------------------------------------------------------

class FlagEncodeValueMixin(Encodable, dotted=Encodable._DO_NOT_REGISTER):
    '''
    REQUIREMENT: Enums that use this must also have: dotted='a.dotted.str'
    in their class arguments list!
    Example:
      class JeffFlag(FlagEncodeValueMixin, enum.Flag,
                     dotted='veredi.jeff.flag'):
          ...

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
    def _type_field(klass: 'FlagEncodeValueMixin') -> str:
        '''
        A short, unique name for encoding an instance into a field in a dict.
        Override this if you don't like what veredi.base.dotted.auto() and
        veredi.base.dotted.munge_to_short() do for your type field.
        '''
        return dotted.munge_to_short(dotted.auto(klass))

    @classmethod
    def _encode_simple_only(klass: 'FlagEncodeValueMixin') -> bool:
        '''We are too simple to bother with being a complex type.'''
        return True

    @classmethod
    def _get_decode_str_rx(klass: 'FlagEncodeValueMixin') -> Optional[str]:
        '''
        Returns regex /string/ (not compiled regex) of what to look for to
        claim just a string as this class.
        '''
        if not klass._ENCODABLE_RX_STR:
            # Build it from the format str.
            klass._ENCODABLE_RX_STR = klass._ENCODABLE_RX_STR_FMT.format(
                type_field=klass._type_field())

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
                raise log.exception(error, None,
                                    msg)

            klass._ENCODABLE_RX = re.compile(rx_str, klass._ENCODABLE_RX_FLAGS)

        return klass._ENCODABLE_RX

    def _encode_simple(self) -> str:
        '''
        Encode ourself as a string, return that value.
        '''
        encoded = self._ENCODE_SIMPLE_FMT.format(type_field=self._type_field(),
                                                 value=self.value)
        # print(f"FlagEncodeValueMixin.encode_simple: {self} -> {encoded}")
        return encoded

    def _encode_complex(self) -> EncodedComplex:
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(
            f"{self.__class__.__name__}._encode_complex() is not implemented.")

    @classmethod
    def _decode_simple(klass: 'FlagEncodeValueMixin',
                       data: str) -> 'FlagEncodeValueMixin':
        '''
        Decode ourself from a string, return a new instance of `klass` as
        the result of the decoding.
        '''
        rx = klass._get_decode_rx()
        if not rx:
            msg = (f"{klass.__name__}: No decode regex - "
                   f"- cannot decode: {data}")
            error = ValueError(msg, data)
            raise log.exception(error, None,
                                msg)

        # Have regex, but does it work on data?
        match = rx.match(data)
        if not match or not match.group('value'):
            msg = (f"{klass.__name__}: Decode regex failed to match "
                   f"data - cannot decode: {data}")
            error = ValueError(msg, data)
            raise log.exception(error, None,
                                msg)

        # Have regex, have match. Build instance.
        decoded = klass(int(match.group('value')))
        # print(f"FlagEncodeValueMixin.decode_simple: {data} -> {decoded}")
        return decoded

    @classmethod
    def _decode_complex(klass: 'FlagEncodeValueMixin',
                        value: EncodedComplex) -> 'FlagEncodeValueMixin':
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(f"{klass.__name__}._decode_complex() is "
                                  "not implemented.")


class FlagEncodeNameMixin(Encodable, dotted=Encodable._DO_NOT_REGISTER):
    '''
    REQUIREMENT: Enums that use this must also register manually:
    Example:
      class JeffFlag(FlagEncodeValueMixin, enum.Flag):
          ...
          @classmethod
          def dotted(klass: 'JeffFlag') -> str:
                return 'veredi.jeff.system.flag'
          ...

      # Enums and that auto-register parameter "dotted='jeff.whatever'" don't
      # get along - registering manually...
      JeffFlag.register_manually()

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
    def _type_field(klass: 'FlagEncodeNameMixin') -> str:
        '''
        A short, unique name for encoding an instance into a field in a dict.
        Override this if you don't like what veredi.base.dotted.auto() and
        veredi.base.dotted.munge_to_short() do for your type field.
        '''
        return dotted.munge_to_short(dotted.auto(klass))

    @classmethod
    def _encode_simple_only(klass: 'FlagEncodeNameMixin') -> bool:
        '''We are too simple to bother with being a complex type.'''
        return True

    @classmethod
    def _get_decode_str_rx(klass: 'FlagEncodeNameMixin') -> Optional[str]:
        '''
        Returns regex /string/ (not compiled regex) of what to look for to
        claim just a string as this class.
        '''
        if not klass._ENCODABLE_RX_STR:
            # Build it from the format str.
            klass._ENCODABLE_RX_STR = klass._ENCODABLE_RX_STR_FMT.format(
                type_field=klass._type_field())

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
                raise log.exception(error, None,
                                    msg)

            klass._ENCODABLE_RX = re.compile(rx_str, klass._ENCODABLE_RX_FLAGS)

        return klass._ENCODABLE_RX

    def _encode_simple(self) -> str:
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
            raise log.exception(error, None,
                                msg)

        # Turn list of names into one string for final return string.
        return self._ENCODE_SIMPLE_FMT.format(type_field=self._type_field(),
                                              names='|'.join(names))

    def _encode_complex(self) -> EncodedComplex:
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(
            f"{self.__class__.__name__}._encode_complex() is not implemented.")

    @classmethod
    def _decode_simple(klass: 'FlagEncodeValueMixin',
                       data: str) -> 'FlagEncodeValueMixin':
        '''
        Decode ourself from a string, return a new instance of `klass` as
        the result of the decoding.
        '''
        rx = klass._get_decode_rx()
        if not rx:
            msg = (f"{klass.__name__}: No decode regex - "
                   f"- cannot decode: {data}")
            error = ValueError(msg, data)
            raise log.exception(error, None,
                                msg)

        # Have regex, but does it work on data?
        match = rx.match(data)
        if not match or not match.group('names'):
            msg = (f"{klass.__name__}: Decode regex failed to match "
                   f"data - cannot decode: {data}")
            error = ValueError(msg, data)
            raise log.exception(error, None,
                                msg)

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
    def _decode_complex(klass: 'FlagEncodeValueMixin',
                        value: EncodedComplex) -> 'FlagEncodeValueMixin':
        '''
        NotImplementedError: We don't do complex.
        '''
        raise NotImplementedError(f"{klass.__name__}._decode_complex() is "
                                  "not implemented.")
