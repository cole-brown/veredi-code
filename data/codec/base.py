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
                    NewType, Any, Iterable, Mapping, List, Dict, TextIO)
if TYPE_CHECKING:
    from veredi.base.context        import VerediContext
    from veredi.data.config.context import ConfigContext


from abc import ABC, abstractmethod
from io import StringIO


from .encodable import Encodable


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# TODO [2020-08-22]: Rename; CodecInput and CodecOutput are both
# inputs/outputs to codec because codec is coder/decoder so this name makes me
# sad that I came up with it...
# EncodeTypes/DecodeTypes?
CodecOutput = NewType('CodecOutput',
                      Union[List[Any], Dict[str, Any], None])


# TODO [2020-08-22]: Rename; CodecInput and CodecOutput are both
# inputs/outputs to codec because codec is coder/decoder so this name makes me
# sad that I came up with it...
# EncodeTypes/DecodeTypes?
CodecInput = NewType('CodecInput',
                     Union[Encodable, Iterable[Any], Mapping[str, Any], None])

# TODO [2020-08-22]: YAML Codec should use the renamed CodecInput/Output.


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
        raise NotImplementedError(f"{self.__class__.__name__}.background() "
                                  "is not implemented.")

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
        raise NotImplementedError(f"{self.__class__.__name__}._configure() "
                                  "is not implemented.")

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
        raise NotImplementedError(f"{self.__class__.__name__}.decode() "
                                  "is not implemented.")

    @abstractmethod
    def decode_all(self,
                   stream: Union[TextIO, str],
                   context: 'VerediContext') -> CodecOutput:
        '''Read and decodes all documents from the data stream.

        Raises:
          - exceptions.ReadError
            - wrapping a library error?
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.decode_all() "
                                  "is not implemented.")

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
        raise NotImplementedError(f"{self.__class__.__name__}._read() "
                                  "is not implemented.")

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
        raise NotImplementedError(f"{self.__class__.__name__}._read_all() "
                                  "is not implemented.")

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
        raise NotImplementedError(f"{self.__class__.__name__}.encode() "
                                  "is not implemented.")

    @abstractmethod
    def encode_all(self,
                   data: Mapping[str, Any],
                   context: 'VerediContext') -> StringIO:
        '''Write and encodes all documents from the data stream.

        Raises:
          - exceptions.WriteError
            - wrapping a library error?
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.encode_all() "
                                  "is not implemented.")

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
        raise NotImplementedError(f"{self.__class__.__name__}._write() "
                                  "is not implemented.")

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
        raise NotImplementedError(f"{self.__class__.__name__}._write_all() "
                                  "is not implemented.")
