# coding: utf-8

'''
Base class for Serializing/Deserializing.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, NewType, Any, Iterable, TextIO)
if TYPE_CHECKING:
    from veredi.base.context        import VerediContext
    from veredi.data.config.context import ConfigContext


from abc import ABC, abstractmethod

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

    _TYPE_FIELD = '_serializable'

    @classmethod
    def claim(klass: 'Serializable',
              stream: Union[str, bytes, TextIO]) -> bool:
        '''
        Returns true if this Serializable class thinks it can/should
        deserialize this stream.
        '''
        return (klass._TYPE_FIELD in stream
                and stream[klass._TYPE_FIELD] == klass.__name__)

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


SerializeTypes = NewType('SerializeTypes',
                         Union[str, bytes, TextIO, None])


DeserializeTypes = NewType('DeserializeTypes',
                           Union[Serializable, Iterable[Serializable],
                                 str, None])


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# Subclasses, register like this:
# @register('veredi', 'serdes', 'SerdesSubclass')
class BaseSerdes(ABC):
    def __init__(self,
                 serdes_name:     str,
                 config_context: Optional['VerediContext'] = None) -> None:
        '''
        `serdes_name` should be short and will be lowercased.
        'string', 'file', 'IDK'?

        `config_context` is the context being used to set us up.
        '''
        self._name = serdes_name.lower()

        self._configure(config_context)

    # -------------------------------------------------------------------------
    # Serdes Properties/Methods
    # -------------------------------------------------------------------------

    @property
    def name(self) -> str:
        '''
        Should be lowercase and short.
        '''
        return self._name

    # -------------------------------------------------------------------------
    # Context Properties/Methods
    # -------------------------------------------------------------------------

    @property
    @abstractmethod
    def background(self):
        '''
        Data for the Veredi Background context.
        '''
        raise NotImplementedError

    def _make_background(self, dotted_name):
        '''
        Start of the background data.

        `dotted_name` should be the dotted version of your @register() string.
        e.g. for:
          @register('veredi', 'repository', 'file-bare')
        `dotted_name` is:
          'veredi.repository.file-bare'

        @register will give you the self._DOTTED string, and probably the
        self.dotted property to use as the argument.
        '''
        return {
            'dotted': dotted_name,
            'type': self.name,
        }

    def make_context_data(self) -> Union[str, str]:
        '''
        Returns context data for inserting into someone else's context.
        '''
        return {
            'dotted': self.dotted,
            'type': self.name,
        }

    # -------------------------------------------------------------------------
    # Abstract Methods
    # -------------------------------------------------------------------------

    @abstractmethod
    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''
        Allows serdes to grab anything from the config data that they need to
        set up themselves.
        '''
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Abstract: Deserialize Methods
    # -------------------------------------------------------------------------

    @abstractmethod
    def deserialize(self,
                    stream:  SerializeTypes,
                    context: 'VerediContext') -> DeserializeTypes:
        '''
        Read and deserializes a single document from the data stream.

        Raises:
          - exceptions.ReadError
            - wrapping a library error?
        '''
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Abstract: Serialize Methods
    # -------------------------------------------------------------------------

    @abstractmethod
    def serialize(self,
                  data: DeserializeTypes,
                  context: 'VerediContext') -> SerializeTypes:
        '''
        Write and serializes a single document from the data stream.

        Raises:
          - exceptions.WriteError
            - wrapping a library error?
        '''
        raise NotImplementedError
