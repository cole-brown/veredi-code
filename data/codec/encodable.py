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

    # -------------------------------------------------------------------------
    # Identity / Ownership
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # API for encoding/decoding.
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Helpers: Validation / Error
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Helpers: Encoding
    # -------------------------------------------------------------------------

    def _encode_map(self,
                    encode_from: Mapping,
                    encode_to:   Optional[Mapping] = None,
                    ) -> Mapping[str, Union[str, int, float, None]]:
        '''
        If `encode_to` is supplied, use that. Else create an empty `encode_to`
        dictionary. Get values in `encode_from` dict, encode them, and put them
        in `encode_to` under an encoded key.

        Returns `encode_to` instance (either the new one we created or the
        existing updated one).
        '''
        if encode_to is None:
            encode_to = {}

        # log.debug(f"\n\nlogging._encode_map: {encode_from}\n\n")
        for key, value in encode_from.items():
            field = self._encode_key(key)
            node = self._encode_value(value)
            encode_to[field] = node

        # log.debug(f"\n\n   done._encode_map: {encode_to}\n\n")
        return encode_to

    def _encode_key(self, key: Any) -> str:
        '''
        Encode a dict key.
        '''
        # log.debug(f"\n\nlogging._encode_key: {key}\n\n")
        field = None
        if isinstance(key, str):
            field = key
        elif isinstance(key, enum.Enum):
            field = key.value
        else:
            field = str(key)

        # log.debug(f"\n\n   done._encode_key: {field}\n\n")
        return field

    def _encode_value(self, value: Any) -> str:
        '''
        Encode a dict value.

        If value is:
          - dict or encodable: Step in to them for encoding.
          - enum: Use the enum's value.

        Else assume it is already encoded.
        '''
        # log.debug(f"\n\nlogging._encode_value: {value}\n\n")
        node = None
        if isinstance(value, dict):
            node = self._encode_map(value)

        elif isinstance(value, Encodable):
            # Encode via its function.
            node = value.encode()

        elif isinstance(value, (enum.Enum, enum.IntEnum)):
            node = value.value

        else:
            node = value

        # log.debug(f"\n\n   done._encode_value: {node}\n\n")
        return node

    # -------------------------------------------------------------------------
    # Helpers: Decoding
    # -------------------------------------------------------------------------

    @classmethod
    def _decode_map(klass: 'Encodable',
                    mapping: Mapping
                    ) -> Mapping[str, Any]:
        '''
        Decode a mapping.
        '''
        # log.debug(f"\n\nlogging._decode_map {type(mapping)}: {mapping}\n\n")

        # ---
        # Decode the Base Level
        # ---
        decoded = {}
        for key, value in mapping.items():
            field = klass._decode_key(key)
            node = klass._decode_value(value)
            decoded[field] = node

        # ---
        # Is It Anything Special?
        # ---
        # Sub-classes could check in about this spot in their override...
        # if AnythingSpecial.claim(decoded):
        #     decoded = AnythingSpecial.decode(decoded)

        # log.debug(f"\n\n   done._decode_map: {decoded}\n\n")
        return decoded

    @classmethod
    def _decode_key(klass: 'Encodable', key: Any) -> str:
        '''
        Decode a mapping's key.

        Encodable is pretty stupid. string is only supported type. Override or
        smart-ify if you need support for more key types.
        '''
        # log.debug(f"\n\nlogging._decode_key {type(key)}: {key}\n\n")
        field = None
        if isinstance(key, str):
            field = key
        else:
            raise EncodableError(f"Don't know how to decode key: {key}",
                                 None)

        # log.debug(f"\n\n   done._decode_key: {field}\n\n")
        return field

    @classmethod
    def _decode_value(klass: 'Encodable', value: Any) -> str:
        '''
        Decode a mapping's value.

        Encodable is pretty stupid. dict and Encodable are further decoded -
        everything else is just assumed to be decoded alreday. Override or
        smart-ify if you need support for more/better assumptions.
        '''

        # log.debug(f"\n\nlogging._decode_value {type(value)}: {value}\n\n")
        node = None
        if isinstance(value, dict):
            node = klass._decode_map(value)

        elif isinstance(value, Encodable):
            # Decode via its function.
            node = value.decode()

        else:
            # Simple value like int, str? Hopefully?
            node = value

        # log.debug(f"\n\n   done._decode_value: {node}\n\n")
        return node
