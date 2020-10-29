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

    @classmethod
    def _type_field(klass: 'Serializable') -> str:
        '''
        A short, unique name for serializing an instance.
        '''
        raise NotImplementedError

    @classmethod
    def claim(klass: 'Serializable',
              stream: Union[str, bytes, TextIO]) -> bool:
        '''
        Returns true if this Serializable class thinks it can/should
        deserialize this stream.
        '''
        return (klass._type_field in stream
                and stream[klass._type_field] == klass.__name__)

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
