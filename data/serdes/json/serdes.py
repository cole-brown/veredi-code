# coding: utf-8

'''
Reader/Loader & Writer/Dumper of JSON Format.
Aka JSON Serdes.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Mapping, List, Tuple, TextIO)
from veredi.base.null import null_or_none
if TYPE_CHECKING:
    from veredi.base.context import VerediContext
    from veredi.data.config.context import ConfigContext


import json
from io import StringIO, TextIOBase
import contextlib


from veredi.logger               import log
from veredi                      import time
from veredi.base                 import paths, numbers
from veredi.base.strings         import text
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
    '''
    Uses Python's json library to serialize/deserialize the JSON format.
    '''

    _SERDES_NAME   = 'json'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        super()._define_vars()

        self._json_encoder: Type[json.JSONEncoder] = JsonEncoder
        '''Custom encoder to handle more types.'''

    def __init__(self,
                 context: Optional['ConfigContext'] = None) -> None:
        super().__init__(JsonSerdes._SERDES_NAME,
                         context)

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''Config from context and elsewhere.'''
        super()._configure(context)

        # Nothing specific for us to do.

    # -------------------------------------------------------------------------
    # Background & Context
    # -------------------------------------------------------------------------

    # None to add/override.

    # -------------------------------------------------------------------------
    # Deserialize Methods
    # -------------------------------------------------------------------------

    def deserialize(self,
                    stream:  Union[TextIO, str],
                    context: 'VerediContext') -> DeserializeTypes:
        '''
        Read and deserializes data from a single data stream.

        Raises:
          - exceptions.ReadError
            - wrapped json.JSONDecodeError
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

    def _json_hookup_obj_pairs(self, pairs: List[Tuple[Any, Any]]) -> Any:
        '''
        Hook for `json.load()` function's `object_pairs_hook` parameter.

        Translates key/value pairs into something else, if needed.
        '''
        # ------------------------------
        # Start with an empty dict, and fill it in with each pair.
        # ------------------------------
        result = {}
        for key, value in pairs:
            # ------------------------------
            # Don't care about numbers and such.
            # ------------------------------
            if not isinstance(value, str):
                result[key] = value
                continue

            # ------------------------------
            # Check strings to see if we need to make them something else.
            # ------------------------------

            # ---
            # Dates & Times:
            # ---

            # Check for date ("2020-02-02") before datetime
            # ("2020-02-02T20:20:02.02") since datetime will happily parse a
            # date as being at 00:00:00.
            stamp = time.parse.date(value)
            if stamp:
                result[key] = stamp
                # Found a value; done.
                continue

            # Now do datetime.
            stamp =  time.parse.datetime(value)
            if stamp:
                result[key] = stamp
                # Found a value; done.
                continue

            # ---
            # Insert other stuff here as needed.
            # ---

            # ---
            # Ok. It's just a string apparently.
            # ---
            result[key] = value

        # ------------------------------
        # Finally, return the filled out dict.
        # ------------------------------
        return result

    def _json_load(self,
                   stream: Union[TextIO, str]) -> DeserializeTypes:
        '''
        Calls `json.load()` or `json.loads()`, as appropriate, with correct
        hook(s), and returns json's result.
        '''
        data = None
        if isinstance(stream, str):
            data = json.loads(stream,
                              object_pairs_hook=self._json_hookup_obj_pairs)
        else:
            data = json.load(stream,
                             object_pairs_hook=self._json_hookup_obj_pairs)

        return data

    def _read(self,
              stream:  Union[TextIO, str],
              context: 'VerediContext') -> DeserializeTypes:
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
        if isinstance(stream, TextIOBase):
            # Assume we are supposed to read the entire stream.
            stream.seek(0)

        data = None
        try:
            data = self._json_load(stream)
        except json.JSONDecodeError as json_error:
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
                        stream:  Union[TextIO, str],
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
                  stream:  Union[TextIO, str],
                  context: 'VerediContext') -> DeserializeTypes:
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
                  data:    SerializeTypes,
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

    def _json_dump(self,
                   data:   SerializeTypes,
                   stream: Union[TextIO, str]) -> None:
        '''
        Calls `json.dump()` or `json.dumps()`, as appropriate, with correct
        hook(s), and returns json's result.
        '''
        if isinstance(stream, str):
            data = json.dumps(data,
                              stream,
                              cls=self._json_encoder)
        else:
            data = json.dump(data,
                             stream,
                             cls=self._json_encoder)

        return data

    def _serialize_prep(self,
                        data:    SerializeTypes,
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

        # Is it a simple type?
        if (text.serialize_claim(data)
                or numbers.serialize_claim(data)
                or paths.serialize_claim(data)
                or time.serialize_claim(data)):
            # Let json handle it.
            serialized = data
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
                serialized.append(self._serialize_prep(each, context))
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
               data:    SerializeTypes,
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
            self._json_dump(data, serialized)
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
                      data:    SerializeTypes,
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
                   data:    SerializeTypes,
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


# -----------------------------------------------------------------------------
# Custom Json Encoder
# -----------------------------------------------------------------------------

class JsonEncoder(json.JSONEncoder):
    '''
    Have to customize the encoder as well, to support dates and such.
    '''

    def default(self, obj: Any) -> Any:
        '''
        Add support for encoding more object types (e.g. date, datetime).

        As of 3.8, the base class supports these:
          - dict -> object
          - list, tuple -> array
          - str -> string
          - int, float, int- & float-derived Enums -> number
          - True -> true
          - False -> false
          - None -> null
        '''
        # ------------------------------
        # Check for object types we can do something about.
        # ------------------------------

        # ---
        # Numbers & Strings:
        # ---

        # Let parent handle them.

        # ---
        # Dates & Times:
        # ---
        if time.parse.serialize_claim(obj):
            return time.parse.serialize(obj)

        # ---
        # Paths:
        # ---
        if paths.serialize_claim(obj):
            return paths.serialize(obj)

        # ---
        # Insert other stuff here as needed.
        # ---

        # ---
        # Else do the (parent's) default.
        # ---
        return super().default(obj)
