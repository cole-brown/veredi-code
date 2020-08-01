# coding: utf-8

'''
Reader/Loader & Writer/Dumper of JSON Format.
Aka JSON Codec.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Mapping, Dict, List, TextIO)
from veredi.base.null import null_or_none
if TYPE_CHECKING:
    from veredi.base.context import VerediContext
    from veredi.data.config.context import ConfigContext


import json
from io import StringIO
import contextlib

from veredi.logger import log
from veredi.data import background
from veredi.data.config.registry import register
from veredi.data import exceptions

from ..base import BaseCodec, CodecOutput, CodecInput


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

    # -------------------------------------------------------------------------
    # Background & Context
    # -------------------------------------------------------------------------

    def _make_background(self) -> None:
        self._bg = super()._make_background(self.dotted)

    @property
    def background(self):
        '''
        Data for the Veredi Background context.

        Returns: (data, background.Ownership)
        '''
        return self._bg, background.Ownership.SHARE

    def _context_decode_data(self,
                             context: 'VerediContext') -> 'VerediContext':
        '''
        Inject our codec data into the context.
        '''
        meta, _ = self.background
        context[str(background.Name.CODEC)] = {
            'meta': meta,
        }
        return context

    # -------------------------------------------------------------------------
    # Decode Methods
    # -------------------------------------------------------------------------

    def decode(self,
               stream: Union[TextIO, str],
               context: 'VerediContext') -> CodecOutput:
        '''
        Read and decodes data from a single data stream.

        Raises:
          - exceptions.ReadError
            - wrapped json.JSONDecodeError
          Maybes:
            - Other json/stream errors?
        '''
        self._context_decode_data(context)
        data = self._read(stream, context)
        return data

    def _read(self,
              stream: Union[TextIO, str],
              context: 'VerediContext') -> Any:
        '''
        Read data from a single data stream.

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
            if isinstance(stream, str):
                data = json.loads(stream)
            else:
                data = json.load(stream)
        except json.JSONDecodeError as error:
            data = None
            raise log.exception(
                error,
                exceptions.ReadError,
                f"Error reading json from stream: {stream}",
                context=context) from error

        return data

    def decode_all(self,
                   stream: Union[TextIO, str],
                   context: 'VerediContext') -> CodecOutput:
        '''
        Read and decodes all documents from the data stream.

        Raises:
          - exceptions.ReadError
            - wrapping a library error?
        '''
        self._context_decode_data(context)
        # TODO [2020-05-22]: decode_all
        raise NotImplementedError("TODO: this")

    def _read_all(self,
                  stream: Union[TextIO, str],
                  context: 'VerediContext') -> Any:
        '''
        Read data from a single data stream.

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

    def _context_encode_data(self,
                             context: 'VerediContext') -> 'VerediContext':
        '''
        Inject our codec data into the context.
        '''
        meta, _ = self.background
        context[str(background.Name.CODEC)] = {
            'meta': meta,
        }
        return context

    def encode(self,
               data: CodecInput,
               context: 'VerediContext') -> StringIO:
        '''
        Write and encodes a single document from the data stream.

        Raises:
          - exceptions.WriteError
            - wrapping a library error?
        '''
        self._context_encode_data(context)
        to_encode = self._encode_prep(data, context)
        stream = self._write(to_encode, context)
        return stream

    def _encode_prep(self,
                     data: CodecInput,
                     context: 'VerediContext') -> Mapping[str, Any]:
        '''
        Tries to turn the various possibilities for data (list, dict, etc) into
        something ready for json to encode.
        '''
        encoded = None
        if null_or_none(data):
            return encoded

        # Is it just an Encodable object?
        with contextlib.suppress(AttributeError):
            encoded = data.encode()
            return encoded

        # Mapping?
        with contextlib.suppress(AttributeError):
            encoded = {}
            for each in data.keys():
                # TODO [2020-07-29]: Change to non-recursive?
                encoded[str(each)] = self._encode_prepass(data[each], context)
            return encoded

        # Iterable
        with contextlib.suppress(AttributeError):
            encoded = []
            for each in data:
                # TODO [2020-07-29]: Change to non-recursive?
                encoded.append(self._encode_prepass(each), context)
            return encoded

        msg = "Don't know how to process data."
        raise log.exception(
            ValueError(msg, data),
            exceptions.WriteError,
            msg + f" data: {data}",
            context=context)

    def _write(self,
               data: Union[Dict[str, Any], List[Any], None],
               context: 'VerediContext') -> StringIO:
        '''
        Write data to a stream.

        Returns:
          The stream with the encoded data in it.

        Raises:
          - exceptions.WriteError
            - wrapped lib/module errors
        '''
        encoded = StringIO()
        try:
            json.dump(data, encoded)
        except (TypeError, OverflowError, ValueError) as error:
            encoded = None
            raise log.exception(
                error,
                exceptions.WriteError,
                "Error writing data to stream: "
                f"data: {data}, stream: {encoded}",
                context=context) from error

        return encoded

    def encode_all(self,
                   data: Mapping[str, Any],
                   context: 'VerediContext') -> StringIO:
        '''
        Write and encodes all documents from the data stream.

        Returns:
          The stream with the encoded data in it.

        Raises:
          - exceptions.WriteError
            - wrapped lib/module errors
        '''
        # TODO [2020-05-22]: write_all
        raise NotImplementedError("TODO: this")

    def _write_all(self,
                   data: Mapping[str, Any],
                   context: 'VerediContext') -> StringIO:
        '''
        Write data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.WriteError
            - wrapped lib/module errors
        '''
        # TODO [2020-05-22]: write_all
        raise NotImplementedError("TODO: this")
