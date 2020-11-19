# coding: utf-8

'''
Serializable mixin class for customizing how a class is
serialized/deserialized by Serdeses.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, Any, Iterable, TextIO


from ..exceptions import SerializableError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

class Serializable:
    '''
    Mixin for classes that want to support serializing/deserializing
    themselves.

    The class should convert its data to/from a string/bytes/stream to basic
    value-types (str, int, etc), Serializable members, etc. If anything it
    (directly) contains also needs serializing/deserializing, the class should
    ask it to during the serialize/deserialize.
    '''

    # TODO [2020-11-03]: Updated Serializable to work like Encodable does now.

    @classmethod
    def _type_field(klass: 'Serializable') -> str:
        '''
        A short, unique name for serializing an instance.
        '''
        raise NotImplementedError(f"{klass.__name__}._type_field() "
                                  "is not implemented.")

    @classmethod
    def claim(klass: 'Serializable',
              stream: Union[str, bytes, TextIO]) -> bool:
        '''
        Returns true if this Serializable class thinks it can/should
        deserialize this stream.
        '''
        # TODO [2020-11-03]: Updated Serializable to work like Encodable does now.
        # # Is it EncodedSimple?
        # if klass._encoded_simply(stream):
        #     # If it's a simple encode and we don't have a decode regex for
        #     # that, then... No; It can't be ours.
        #     decode_rx = klass._get_decode_rx()
        #     if not decode_rx:
        #         return False
        #     # Check if decode_rx likes the data.
        #     return bool(decode_rx.match(stream))

        # Else it's EncodedComplex. See if it has our type field.
        return (klass._type_field() in stream
                and stream[klass._type_field()] == klass.__name__)

    def serialize(self) -> Union[str, bytes, TextIO]:
        '''
        Serialize self to string or bytes or something.
        '''
        ...

    @classmethod
    def deserialize(klass: 'Serializable',
                    stream: Union[str, bytes, TextIO]) -> 'Serializable':
        '''
        Deserialize a string or bytes or something to (basic) values (str, int,
        etc), using it to build an instance of this class.

        Return the instance.
        '''
        ...

    @classmethod
    def error_for_claim(klass: 'Serializable',
                        stream: Union[str, bytes, TextIO]) -> None:
        '''
        Raises an SerializableError if claim() returns false.
        '''
        if not klass.claim(stream):
            raise SerializableError(
                f"Cannot claim for {klass.__name__} for deserializing: "
                f"{stream}",
                None)

    @classmethod
    def error_for_key(klass:  'Serializable',
                      key:    str,
                      stream: Union[str, bytes, TextIO]) -> None:
        '''
        Raises an SerializableError if supplied `key` is not in `stream`.
        '''
        if key not in stream:
            raise SerializableError(
                f"Cannot deserialize to {klass.__name__}: {stream}",
                None)

    @classmethod
    def error_for_value(klass:  'Serializable',
                        key:    str,
                        value:  Any,
                        stream: Union[str, bytes, TextIO]) -> None:
        '''
        Raises an SerializableError if `key` value in `stream` is not equal to
        supplied `value`.

        Assumes `error_for_key()` has been called for the key.
        '''
        if stream[key] != value:
            raise SerializableError(
                f"Cannot deserialize to {klass.__name__}. "
                f"Value of '{key}' is incorrect. "
                f"Expected '{value}'; got '{stream[key]}"
                f": {stream}",
                None)

    @classmethod
    def error_for(klass:  'Serializable',
                  stream: Union[str, Any],
                  keys:   Iterable[str]   = [],
                  values: Union[str, Any] = {}) -> None:
        '''
        Runs:
          - error_for_claim()
          - error_for_key() on all `keys`
          - error_for_value() on all key/value pairs in `values`.
        '''
        klass.error_for_claim(stream)

        for key in keys:
            klass.error_for_key(key, stream)

        for key in values:
            klass.error_for_value(key, values[key], stream)
