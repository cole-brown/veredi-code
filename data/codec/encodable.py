# coding: utf-8

'''
Encodable mixin class for customizing how a class is encoded/decoded by Codecs.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, Iterable, Mapping


from ..exceptions import EncodableError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Encodable:
    '''
    Mixin for classes that want to support encoding/decoding themselves.

    The class should convert its data to/from a mapping of strings to basic
    value-types (str, int, etc). If anything it (directly) contains also needs
    encoding/decoding, the class should ask it to during the encode/decode.
    '''

    @classmethod
    def _type_field(klass: 'Encodable') -> str:
        '''
        A short, unique name for encoding an instance into the field of a dict.

        E.g.: If an instance of whatever has a "Jeff" class instance with
        _type_field() returning 'jeff' and instance vars of x=1, y=2 is encoded
        to json:
          {
            ...
            'jeff': { 'x': 1, 'y': 2 },
            ...
          }
        '''
        raise NotImplementedError

    @classmethod
    def claim(klass: 'Encodable', mapping: Mapping[str, Any]) -> bool:
        '''
        Returns true if this Encodable class thinks it can/should decode this
        mapping.
        '''
        return (klass._type_field in mapping
                and mapping[klass._type_field] == klass.__name__)

    def encode(self) -> Mapping[str, Any]:
        '''
        Encode self as a Mapping of strings to (basic) values (str, int, etc).
        '''
        return {
            self._type_field: self.__class__.__name__,
        }

    @classmethod
    def decode(klass: 'Encodable', mapping: Mapping[str, Any]) -> 'Encodable':
        '''
        Decode a Mapping of strings to (basic) values (str, int, etc), using it
        to build an instance of this class.

        Return the instance.
        '''
        ...

    def encode_str(self) -> str:
        '''
        If it is a simple Encodable, perhaps it can be encoded into just a str
        field. If so, implement encode_str(), decode_str() and
        get_decode_str_rx().

        Encode this instance into a string.

        Return the string.
        '''
        return str(self)

    @classmethod
    def decode_str(klass: 'Encodable', string: str) -> 'Encodable':
        '''
        If it is a simple Encodable, perhaps it can be encoded into just a str
        field. If so, implement encode_str(), decode_str() and
        get_decode_str_rx().

        Decode the `string` to a `klass` instance.

        Return the instance.
        '''
        ...

    @classmethod
    def get_decode_str_rx(klass: 'Encodable') -> Optional[str]:
        '''
        Returns regex /string/ (not compiled regex) of what to look for to
        claim just a string as this class.

        For example, perhaps a UserId for 'jeff' has a normal decode of:
          {
            '_encodable': 'UserId',
            'uid': 'deadbeef-cafe-1337-1234-e1ec771cd00d',
          }
        And perhaps it has str() of 'uid:deadbeef-cafe-1337-1234-e1ec771cd00d'

        This would expect an rx string for the str.
        '''
        ...

    @classmethod
    def error_for_claim(klass: 'Encodable',
                        mapping: Mapping[str, Any]) -> None:
        '''
        Raises an EncodableError if claim() returns false.
        '''
        if not klass.claim(mapping):
            raise EncodableError(
                f"Cannot claim for {klass.__name__} for decoding: {mapping}",
                None)

    @classmethod
    def error_for_key(klass: 'Encodable',
                      key: str,
                      mapping: Mapping[str, Any]) -> None:
        '''
        Raises an EncodableError if supplied `key` is not in `mapping`.
        '''
        if key not in mapping:
            raise EncodableError(
                f"Cannot decode to {klass.__name__}: {mapping}",
                None)

    @classmethod
    def error_for_value(klass:   'Encodable',
                        key:     str,
                        value:   Any,
                        mapping: Mapping[str, Any]) -> None:
        '''
        Raises an EncodableError if `key` value in `mapping` is not equal to
        supplied `value`.

        Assumes `error_for_key()` has been called for the key.
        '''
        if mapping[key] != value:
            raise EncodableError(
                f"Cannot decode to {klass.__name__}. "
                f"Value of '{key}' is incorrect. "
                f"Expected '{value}'; got '{mapping[key]}"
                f": {mapping}",
                None)

    @classmethod
    def error_for(klass:   'Encodable',
                  mapping: Mapping[str, Any],
                  keys:    Iterable[str]     = [],
                  values:  Mapping[str, Any] = {}) -> None:
        '''
        Runs:
          - error_for_claim()
          - error_for_key() on all `keys`
          - error_for_value() on all key/value pairs in `values`.
        '''
        klass.error_for_claim(mapping)

        for key in keys:
            klass.error_for_key(key, mapping)

        for key in values:
            klass.error_for_value(key, values[key], mapping)
