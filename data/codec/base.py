# coding: utf-8

'''
Base class for Reader/Loader & Writer/Dumper of ___ Format.
Aka ___ Codec.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, NewType, Any, List, Dict, TextIO)
if TYPE_CHECKING:
    from veredi.base.context        import VerediContext
    from veredi.data.config.context import ConfigContext


from abc import ABC, abstractmethod


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

CodecOutput = NewType('CodecOutput',
                      Union[List[Any], Dict[str, Any], None])


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
               stream: TextIO,
               input_context: 'VerediContext') -> CodecOutput:
        '''Read and decodes a single document from the data stream.

        Raises:
          - exceptions.ReadError
            - wrapping a library error?
        '''
        raise NotImplementedError

    @abstractmethod
    def decode_all(self,
                   stream: TextIO,
                   input_context: 'VerediContext') -> CodecOutput:
        '''Read and decodes all documents from the data stream.

        Raises:
          - exceptions.ReadError
            - wrapping a library error?
        '''
        raise NotImplementedError

    @abstractmethod
    def _read(self,
              stream: TextIO,
              input_context: 'VerediContext') -> Any:
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
                  stream: TextIO,
                  input_context: 'VerediContext') -> Any:
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
               stream: TextIO,
               input_context: 'VerediContext') -> CodecOutput:
        '''Write and encodes a single document from the data stream.

        Raises:
          - exceptions.WriteError
            - wrapping a library error?
        '''
        raise NotImplementedError

    @abstractmethod
    def encode_all(self,
                   stream: TextIO,
                   input_context: 'VerediContext') -> CodecOutput:
        '''Write and encodes all documents from the data stream.

        Raises:
          - exceptions.WriteError
            - wrapping a library error?
        '''
        raise NotImplementedError

    @abstractmethod
    def _write(self,
               stream: TextIO,
               input_context: 'VerediContext') -> Any:
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
                   stream: TextIO,
                   input_context: 'VerediContext') -> Any:
        '''Write data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.WriteError
            - wrapped lib/module errors
        '''
        raise NotImplementedError
