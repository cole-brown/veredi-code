# coding: utf-8

'''
Reader/Loader & Writer/Dumper of JSON Format.
Aka JSON Codec.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Any, TextIO)
if TYPE_CHECKING:
    from veredi.base.context import VerediContext
    from veredi.data.config.context import ConfigContext


import json

from veredi.data.background import Ownership as BgOwner
from veredi.data.config.registry import register
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

    def __init__(self,
                 context: Optional['ConfigContext'] = None) -> None:
        super().__init__(JsonCodec._CODEC_NAME,
                         context)

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''Don't need anything from context, currently.'''
        self._make_background()

    def _make_background(self) -> None:
        self._bg = super()._make_background(self.dotted)

    @property
    def background(self):
        '''
        Data for the Veredi Background context.

        Returns: (data, background.Ownership)
        '''
        return self._bg, BgOwner.SHARE

    # -------------------------------------------------------------------------
    # Decode Methods
    # -------------------------------------------------------------------------

    def decode(self,
               stream: TextIO,
               input_context: 'VerediContext') -> CodecOutput:
        '''Read and decodes data from a single data stream.

        Raises:
          - exceptions.ReadError
            - wrapped json.JSONDecodeError
          Maybes:
            - Other json/stream errors?
        '''
        data = self._read(stream, input_context)
        try:
            data = json.load(stream)
        except json.JSONDecodeError as error:
            data = None
            raise exceptions.ReadError(
                f"Error reading json from stream: {stream}",
                error,
                input_context) from error
        return data

    def _read(self,
              stream: TextIO,
              input_context: 'VerediContext') -> Any:
        '''Read data from a single data stream.

        Returns:
          Output of json.load().
          Mix of:
            - json objects
            - our subclasses of json objects
            - and python objects

        Raises:
          - exceptions.ReadError
            - wrapped json.JSONDecodeError
          Maybes:
            - Other json/file errors?
        '''
        data = None
        try:
            data = json.load(stream)
        except json.JSONDecodeError as error:
            data = None
            raise exceptions.ReadError(
                f"Error reading json from stream: {stream}",
                error,
                input_context) from error
        return data

    def decode_all(self,
                   stream: TextIO,
                   input_context: 'VerediContext') -> CodecOutput:
        '''Read and decodes all documents from the data stream.

        Raises:
          - exceptions.ReadError
            - wrapping a library error?
        '''
        # TODO [2020-05-22]: decode_all
        raise NotImplementedError("TODO: this")

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
        # TODO [2020-05-22]: read_all
        raise NotImplementedError("TODO: this")

    # -------------------------------------------------------------------------
    # Encode Methods
    # -------------------------------------------------------------------------

    def encode(self,
               stream: TextIO,
               input_context: 'VerediContext') -> CodecOutput:
        '''Write and encodes a single document from the data stream.

        Raises:
          - exceptions.WriteError
            - wrapping a library error?
        '''
        # TODO [2020-05-22]: write_all
        raise NotImplementedError("TODO: this")

    def encode_all(self,
                   stream: TextIO,
                   input_context: 'VerediContext') -> CodecOutput:
        '''Write and encodes all documents from the data stream.

        Raises:
          - exceptions.WriteError
            - wrapping a library error?
        '''
        # TODO [2020-05-22]: write_all
        raise NotImplementedError("TODO: this")

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
        # TODO [2020-05-22]: write_all
        raise NotImplementedError("TODO: this")

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
        # TODO [2020-05-22]: write_all
        raise NotImplementedError("TODO: this")
