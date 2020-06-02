# coding: utf-8

'''
Base class for Reader/Loader & Writer/Dumper of ___ Format.
Aka ___ Codec.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Iterable, NewType, List, Dict, TextIO, Any
from abc import ABC, abstractmethod
import enum

from veredi.data import exceptions
from veredi.base.context import VerediContext, PersistentContext
from veredi.data.config.context import ConfigContext


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
                 codec_name:   str,
                 self_context_name: str,
                 self_context_key:  str,
                 config_context:    Optional[VerediContext] = None) -> None:
        '''
        `codec_name` should be short and will be lowercased. It should probably
        be like a filename extension, e.g. 'yaml', 'json'.

        `self_context_name` and `self_context_key` are for /my/ context  -
        used for Event and Error contexts.

        `config_context` is the context being used to set us up.
        '''
        self._context = PersistentContext(self_context_name, self_context_key)
        self._name = codec_name.lower()

        self._configure(config_context)

    # --------------------------------------------------------------------------
    # Codec Properties/Methods
    # --------------------------------------------------------------------------

    @property
    def name(self) -> str:
        '''
        Should be lowercase and short. Probably like the filename extension.
        E.g.: 'yaml', 'json'
        '''
        return self._name

    # --------------------------------------------------------------------------
    # Context Properties/Methods
    # --------------------------------------------------------------------------

    @property
    def context(self) -> VerediContext:
        '''
        Will be the context dict for e.g. Events, Errors.
        '''
        return self._context

    # --------------------------------------------------------------------------
    # Abstract Methods
    # --------------------------------------------------------------------------

    @abstractmethod
    def _configure(self,
                   context: Optional[ConfigContext]) -> None:
        '''
        Allows codecs to grab anything from the config data that they need to
        set up themselves.
        '''
        raise NotImplementedError

    @abstractmethod
    def decode(self,
               stream: TextIO,
               input_context: VerediContext) -> CodecOutput:
        '''Load and decodes a single document from the data stream.

        Raises:
          - exceptions.LoadError
            - wrapping a library error?
        '''
        raise NotImplementedError

    @abstractmethod
    def decode_all(self,
                   stream: TextIO,
                   input_context: VerediContext) -> CodecOutput:
        '''Load and decodes all documents from the data stream.

        Raises:
          - exceptions.LoadError
            - wrapping a library error?
        '''
        raise NotImplementedError

    @abstractmethod
    def _load(self,
              stream: TextIO,
              input_context: VerediContext) -> Any:
        '''Load data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.LoadError
            - wrapped lib/module errors
        '''
        raise NotImplementedError

    @abstractmethod
    def _load_all(self,
                  stream: TextIO,
                  input_context: VerediContext) -> Any:
        '''Load data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.LoadError
            - wrapped lib/module errors
        '''
        raise NotImplementedError
