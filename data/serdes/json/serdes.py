# coding: utf-8

'''
Reader/Loader & Writer/Dumper of JSON Format.
Aka JSON Serdes.
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

from veredi.logger               import log, pretty
from veredi.data                 import background
from veredi.data.config.registry import register
from veredi.data                 import exceptions
from veredi.data.context         import DataAction

from ...codec.encodable          import Encodable
from ..base                      import (BaseSerdes,
                                         DeserializeTypes,
                                         SerializeTypes)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'serdes', 'json')
class JsonSerdes(BaseSerdes):
    _SERDES_NAME   = 'json'

    def __init__(self,
                 context: Optional['ConfigContext'] = None) -> None:
        super().__init__(JsonSerdes._SERDES_NAME,
                         context)

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''Don't need anything from context, currently.'''
        self._make_background()

    # -------------------------------------------------------------------------
    # Background & Context
    # -------------------------------------------------------------------------

    def _make_background(self) -> None:
        self._bg = super()._make_background(self.dotted())

    @property
    def background(self):
        '''
        Data for the Veredi Background context.

        Returns: (data, background.Ownership)
        '''
        return self._bg, background.Ownership.SHARE

    def _context_data(self,
                      context: 'VerediContext',
                      action:  DataAction) -> 'VerediContext':
        '''
        Inject our serdes data into the context.
        '''
        data, _ = self.background
        # Push our context data into our sub-context key.
        context[str(background.Name.SERDES)] = data

        # And add any extra info.
        context['action'] = action

        return context

    # -------------------------------------------------------------------------
    # Deserialize Methods
    # -------------------------------------------------------------------------

    def deserialize(self,
                    stream: Union[TextIO, str],
                    context: 'VerediContext') -> DeserializeTypes:
        '''
        Read and deserializes data from a single data stream.

        Raises:
          - exceptions.ReadError
            - wrapped json.JSONDeserializeError
          Maybes:
            - Other json/stream errors?
        '''
        log.debug("json.deserialize input: {}", type(stream))
        self._context_data(context, DataAction.LOAD)
        data = self._read(stream, context)
        if not data:
            msg = "Reading all json from stream resulted in no data."
            error = exceptions.ReadError(
                msg,
                context=context,
                data={
                    'data': data,
                })
            raise log.exception(error, msg,
                                context=context)

        log.debug("json.deserialize output: {}", type(data))
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
            - wrapped json.JSONDeserializeError
          Maybes:
            - Other json/file errors?
        '''
        data = None
        try:
            if isinstance(stream, str):
                data = json.loads(stream)
            else:
                data = json.load(stream)
        except json.JSONDeserializeError as json_error:
            data = None
            msg = f"Error reading json from stream: {stream}"
            error = exceptions.ReadError(
                msg,
                context=context,
                data={
                    'data': stream,
                    'data_stream.closed': (stream.closed
                                           if stream else
                                           None),
                    'data_stream.readable': (stream.readable()
                                             if stream else
                                             None),
                    'data_stream.pos': (stream.tell()
                                        if stream else
                                        None),
                })
            raise log.exception(error, msg,
                                context=context) from json_error

        return data

    def deserialize_all(self,
                        stream: Union[TextIO, str],
                        context: 'VerediContext') -> DeserializeTypes:
        '''
        Read and deserializes all documents from the data stream. Expects a
        valid/normal json document in the stream, since there isn't a "document
        separator" in the json spec like in other serialized formats.

        Raises:
          - exceptions.ReadError
            - wrapping a library error?
        '''
        log.debug("json.deserialize_all input: {}", type(stream))
        self._context_data(context, DataAction.LOAD)
        data = self._read_all(stream, context)
        if not data:
            msg = "Reading all json from stream resulted in no data."
            error = exceptions.ReadError(
                msg,
                context=context,
                data={
                    'data': data,
                })
            raise log.exception(error, msg,
                                context=context)

        log.debug("json.deserialize_all output: {}", type(data))
        return data

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
        # Just use read since json has no concept of multi-document streams.
        return self._read(stream, context)

    # -------------------------------------------------------------------------
    # Serialize Methods
    # -------------------------------------------------------------------------

    def serialize(self,
                  data: SerializeTypes,
                  context: 'VerediContext') -> StringIO:
        '''
        Write and serializes a single document from the data stream.

        Raises:
          - exceptions.WriteError
            - wrapping a library error?
        '''
        self._context_data(context, DataAction.SAVE)
        to_serialize = self._serialize_prep(data, context)
        stream = self._write(to_serialize, context)
        return stream

    def _serialize_prep(self,
                        data: SerializeTypes,
                        context: 'VerediContext') -> Mapping[str, Any]:
        '''
        Tries to turn the various possibilities for data (list, dict, etc) into
        something ready for json to serialize.
        '''
        serialized = None
        if null_or_none(data):
            return serialized

        # Is it just an Encodable object?
        if isinstance(data, Encodable):
            serialized = data.encode(None)
            return serialized

        # Mapping?
        with contextlib.suppress(AttributeError):
            serialized = {}
            for each in data.keys():
                # TODO [2020-07-29]: Change to non-recursive?
                serialized[str(each)] = self._serialize_prep(data[each],
                                                             context)
            return serialized

        # Iterable
        with contextlib.suppress(AttributeError):
            serialized = []
            for each in data:
                # TODO [2020-07-29]: Change to non-recursive?
                serialized.append(self._serialize_prep(each), context)
            return serialized

        # Falling through to here is bad; raise Exception.
        msg = "Don't know how to process data."
        error = exceptions.WriteError(msg,
                                      context=context,
                                      data={
                                          'data': data,
                                      })
        raise log.exception(error, msg,
                            context=context)

    def _write(self,
               data: SerializeTypes,
               context: 'VerediContext') -> StringIO:
        '''
        Write data to a stream.

        Returns:
          The stream with the serialized data in it.

        Raises:
          - exceptions.WriteError
            - wrapped lib/module errors
        '''
        serialized = StringIO()
        try:
            json.dump(data, serialized)
        except (TypeError, OverflowError, ValueError) as json_error:
            serialized = None
            # data_pretty = pretty.indented(data)
            msg = "Error writing data to stream."
            error = exceptions.WriteError(msg,
                                          context=context,
                                          data={
                                              'data': data,
                                          })
            raise log.exception(error, msg,
                                context=context) from json_error

        return serialized

    def serialize_all(self,
                      data: SerializeTypes,
                      context: 'VerediContext') -> StringIO:
        '''
        Write and serializes all documents from the data stream.

        Returns:
          The stream with the serialized data in it.

        Raises:
          - exceptions.WriteError
            - wrapped lib/module errors
        '''
        self._context_data(context, DataAction.SAVE)
        to_serialize = self._serialize_prep(data, context)
        stream = self._write(to_serialize, context)
        return stream

    def _write_all(self,
                   data: SerializeTypes,
                   context: 'VerediContext') -> StringIO:
        '''
        Write and serializes all documents from the data stream.

        Returns:
          The serialized data in a StringIO buffer.

        Raises:
          - exceptions.WriteError
            - wrapped lib/module errors
        '''
        # Just use _write() since json has no concept of multi-document
        # streams.
        return self._write(data, context)
