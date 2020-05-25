# coding: utf-8

'''
Base class for Reader/Loader & Writer/Dumper of ___ Format.
Aka ___ Codec.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Dict, Optional
from abc import ABC, abstractmethod

from veredi.data import exceptions
from veredi.base.context import VerediContext

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# Subclasses, register like this:
# @register('veredi', 'codec', 'CodecSubclass')
class BaseCodec(ABC):
    def __init__(self,
                 codec_name: str,
                 context_name: str,
                 context_key: str) -> None:
        '''
        `codec_name` should be short and will be lowercased. It should probably
        be like a filename extension, e.g. 'yaml', 'json'.

        `context_name` and `context_key` are used for Event and Error context.
        '''
        self._context = VerediContext(context_name, context_key)
        self._name = codec_name.lower()

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
    def context(self):
        '''
        Will be the context dict for e.g. Events, Errors.
        '''
        return self._context

    # --------------------------------------------------------------------------
    # Abstract Methods
    # --------------------------------------------------------------------------

    @abstractmethod
    def decode(self, stream, error_context):
        '''Load and decodes a single document from the data stream.

        Raises:
          - exceptions.LoadError
            - wrapping a library error?
        '''
        raise NotImplementedError

    @abstractmethod
    def decode_all(self, stream, error_context):
        '''Load and decodes all documents from the data stream.

        Raises:
          - exceptions.LoadError
            - wrapping a library error?
        '''
        raise NotImplementedError

    @abstractmethod
    def _load(self, stream, error_context):
        '''Load data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.LoadError
            - wrapped lib/module errors
        '''
        raise NotImplementedError

    @abstractmethod
    def _load_all(self, stream, error_context):
        '''Load data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.LoadError
            - wrapped lib/module errors
        '''
        raise NotImplementedError
