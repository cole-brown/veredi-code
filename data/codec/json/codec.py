# coding: utf-8

'''
Reader/Loader & Writer/Dumper of JSON Format.
Aka JSON Codec.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Iterable, NewType, List, Dict, TextIO
import json

from veredi.logger import log
from veredi.data.config.registry import register
from veredi.data.config.config import Configuration, ConfigKeys
from veredi.data import exceptions

from ..base import BaseCodec, CodecOutput


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'codec', 'json')
class JsonCodec(BaseCodec):
    _CODEC_NAME   = 'json'
    _CONTEXT_NAME = 'json'
    _CONTEXT_KEY  = 'codec'

    def __init__(self,
                 context:      Optional[VerediContext]        = None,
                 config:       Optional[Configuration]        = None,
                 config_keys:  Optional[Iterable[ConfigKeys]] = None) -> None:
        super().__init__(JsonCodec._CODEC_NAME,
                         JsonCodec._CONTEXT_NAME,
                         JsonCodec._CONTEXT_KEY,
                         context,
                         config,
                         config_keys)

    def _configure(self,
                   config:      Optional[Configuration],
                   config_keys: Optional[Iterable[ConfigKeys]]) -> None:
        pass

    def decode(self,
               stream: TextIO,
               input_context: VerediContext) -> CodecOutput:
        '''Load and decodes data from a single data stream.

        Raises:
          - exceptions.LoadError
            - wrapped json.JSONDecodeError
          Maybes:
            - Other json/stream errors?
        '''
        data = self._load(stream, input_context)
        try:
            data = json.load(stream)
        except json.JSONDecodeError as error:
            data = None
            raise exceptions.LoadError(
                f"Error loading json from stream: {path}",
                error,
                self.context.merge(input_context)) from error
        return data

    def _load(self,
              stream: TextIO,
              input_context: VerediContext) -> Any:
        '''Load data from a single data stream.

        Returns:
          Output of json.load().
          Mix of:
            - json objects
            - our subclasses of json objects
            - and python objects

        Raises:
          - exceptions.LoadError
            - wrapped json.JSONDecodeError
          Maybes:
            - Other json/file errors?
        '''
        data = None
        try:
            data = json.load(stream)
        except json.JSONDecodeError as error:
            data = None
            raise exceptions.LoadError(
                f"Error loading json from stream: {path}",
                error,
                self.context.merge(input_context)) from error
        return data

    def decode_all(self,
                   stream: TextIO,
                   input_context: VerediContext) -> CodecOutput:
        '''Load and decodes all documents from the data stream.

        Raises:
          - exceptions.LoadError
            - wrapping a library error?
        '''
        # §-TODO-§ [2020-05-22]: decode_all
        raise NotImplementedError("TODO: this")

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
        # §-TODO-§ [2020-05-22]: load_all
        raise NotImplementedError("TODO: this")
