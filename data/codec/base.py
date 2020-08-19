# coding: utf-8

'''
Base class for Reader/Loader & Writer/Dumper of ___ Format.
Aka ___ Codec.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union,
                    NewType, Protocol,
                    Any, Iterable, Mapping, List, Dict, TextIO)
if TYPE_CHECKING:
    from veredi.base.context        import VerediContext
    from veredi.data.config.context import ConfigContext


from abc import ABC, abstractmethod
from io import StringIO

from ..exceptions import EncodableError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

class Encodable:
    '''
    Mixin for classes that want to support encoding/decoding themselves.

    The class should convert its data to/from a mapping of strings to basic
    value-types (str, int, etc). If anything it (directly) contains also needs
    encoding/decoding, the class should ask it to during the encode/decode.
    '''

    _TYPE_FIELD = '_encodable'

    def encode(self) -> Mapping[str, Any]:
        '''
        Encode self as a Mapping of strings to (basic) values (str, int, etc).
        '''
        return {
            self._TYPE_FIELD: self.__class__.__name__,
        }

    @classmethod
    def claim(klass: 'Encodable', mapping: Mapping[str, Any]) -> bool:
        '''
        Returns true if this Encodable class thinks it can/should decode this
        mapping.
        '''
        return (klass._TYPE_FIELD in mapping
                and mapping[klass._TYPE_FIELD] == klass.__name__)

    @classmethod
    def decode(klass: 'Encodable', mapping: Mapping[str, Any]) -> 'Encodable':
        '''
        Decode a Mapping of strings to (basic) values (str, int, etc), using it
        to build an instance of this class.

        Return the instance.
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


CodecOutput = NewType('CodecOutput',
                      Union[List[Any], Dict[str, Any], None])


CodecInput = NewType('CodecInput',
                     Union[Encodable, Iterable[Any], Mapping[str, Any], None])


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# Subclasses, register like this:
# @register('veredi', 'codec', 'CodecSubclass')
class BaseCodec(ABC):
    def __init__(self,
                 codec_name:     str,
                 config_context: Optional['VerediContext'] = None) -> None:
        '''
        `codec_name` should be short and will be lowercased. It should probably
        be like a filename extension, e.g. 'yaml', 'json'.

        `config_context` is the context being used to set us up.
        '''
        self._name = codec_name.lower()

        self._configure(config_context)

    # -------------------------------------------------------------------------
    # Codec Properties/Methods
    # -------------------------------------------------------------------------

    @property
    def name(self) -> str:
        '''
        Should be lowercase and short. Probably like the filename extension.
        E.g.: 'yaml', 'json'
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
        '''
        return {
            'dotted': dotted_name,
            'type': self.name,
        }

    def make_context_data(self) -> Mapping[str, str]:
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
        Allows codecs to grab anything from the config data that they need to
        set up themselves.
        '''
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Abstract: Decode Methods
    # -------------------------------------------------------------------------

    @abstractmethod
    def decode(self,
               stream: Union[TextIO, str],
               context: 'VerediContext') -> CodecOutput:
        '''Read and decodes a single document from the data stream.

        Raises:
          - exceptions.ReadError
            - wrapping a library error?
        '''
        raise NotImplementedError

    @abstractmethod
    def decode_all(self,
                   stream: Union[TextIO, str],
                   context: 'VerediContext') -> CodecOutput:
        '''Read and decodes all documents from the data stream.

        Raises:
          - exceptions.ReadError
            - wrapping a library error?
        '''
        raise NotImplementedError

    @abstractmethod
    def _read(self,
              stream: Union[TextIO, str],
              context: 'VerediContext') -> Any:
        '''Read data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.ReadError
            - wrapped lib/module errors
        '''
        raise NotImplementedError

    @abstractmethod
    def _read_all(self,
                  stream: Union[TextIO, str],
                  context: 'VerediContext') -> Any:
        '''Read data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.ReadError
            - wrapped lib/module errors
        '''
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Abstract: Encode Methods
    # -------------------------------------------------------------------------

    @abstractmethod
    def encode(self,
               data: Mapping[str, Any],
               context: 'VerediContext') -> StringIO:
        '''Write and encodes a single document from the data stream.

        Raises:
          - exceptions.WriteError
            - wrapping a library error?
        '''
        raise NotImplementedError

    @abstractmethod
    def encode_all(self,
                   data: Mapping[str, Any],
                   context: 'VerediContext') -> StringIO:
        '''Write and encodes all documents from the data stream.

        Raises:
          - exceptions.WriteError
            - wrapping a library error?
        '''
        raise NotImplementedError

    @abstractmethod
    def _write(self,
               data: Mapping[str, Any],
               context: 'VerediContext') -> Any:
        '''Write data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.WriteError
            - wrapped lib/module errors
        '''
        raise NotImplementedError

    @abstractmethod
    def _write_all(self,
                   data: Mapping[str, Any],
                   context: 'VerediContext') -> Any:
        '''Write data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.WriteError
            - wrapped lib/module errors
        '''
        raise NotImplementedError
