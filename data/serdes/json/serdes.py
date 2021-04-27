# coding: utf-8

'''
Reader/Loader & Writer/Dumper of JSON Format.
Aka JSON Serdes.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type, Mapping,
                    Dict, List, Tuple, TextIO)
from veredi.base.null import null_or_none
if TYPE_CHECKING:
    from veredi.base.context import VerediContext
    from veredi.data.config.context import ConfigContext


import json
from io import StringIO, TextIOBase
import contextlib


from veredi.logs                 import log
from veredi                      import time
from veredi.base                 import paths, numbers
from veredi.base.strings         import label, text
from veredi.data                 import exceptions
from veredi.data.context         import DataAction
from veredi.data.codec           import Codec, Encodable

from ..base                      import (BaseSerdes,
                                         DeserializeTypes,
                                         DeserializeAllTypes,
                                         _DeserializeMidTypes,
                                         _DeserializeAllMidTypes,
                                         SerializeTypes)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class JsonSerdes(BaseSerdes,
                 name_dotted='veredi.serdes.json',
                 name_string='json'):
    '''
    Uses Python's json library to serialize/deserialize the JSON format.
    '''

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
        super().__init__(context)
        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              "Done with init.")

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''Config from context and elsewhere.'''
        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              f"{self.klass} configure...")

        super()._configure(context)

        # Nothing specific for us to do.
        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              "Done with configuration.")

    # -------------------------------------------------------------------------
    # Deserialize Methods
    # -------------------------------------------------------------------------

    def deserialize(self,
                    stream:  Union[TextIO, str],
                    codec:   Codec,
                    context: 'VerediContext') -> DeserializeTypes:
        '''
        Read and deserializes data from a single data stream.

        Raises:
          - exceptions.ReadError
            - wrapped json.JSONDecodeError
          Maybes:
            - Other json/stream errors?
        '''
        self._log_data_processing(self.dotted,
                                  "Deserializing from '{}'...",
                                  type(stream),
                                  context=context)

        self._context_data(context, DataAction.LOAD, codec)
        data = self._read(stream, codec, context)
        if not data:
            msg = "Reading all json from stream resulted in no data."
            self._log_data_processing(self.dotted,
                                      msg,
                                      context=context,
                                      success=False)
            error = exceptions.ReadError(
                msg,
                context=context,
                data={
                    'data': data,
                })
            raise log.exception(error, msg,
                                context=context)

        self._log_data_processing(self.dotted,
                                  "Deserialized to '{}'!",
                                  type(data),
                                  context=context)
        return self._decode(data, codec)

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
            stamp = time.parse.datetime(value)
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
                   stream:  Union[TextIO, str],
                   context: 'VerediContext') -> _DeserializeMidTypes:
        '''
        Calls `json.load()` or `json.loads()`, as appropriate, with correct
        hook(s), and returns json's result.
        '''
        data = None
        if isinstance(stream, str):
            self._log_data_processing(self.dotted,
                                      "Deserializing JSON string...",
                                      context=context)
            data = json.loads(stream,
                              object_pairs_hook=self._json_hookup_obj_pairs)
        else:
            self._log_data_processing(self.dotted,
                                      "Deserializing JSON stream/file...",
                                      context=context)
            data = json.load(stream,
                             object_pairs_hook=self._json_hookup_obj_pairs)

        self._log_data_processing(self.dotted,
                                  "Deserialized data from JSON.",
                                  context=context,
                                  success=True)
        return data

    def _read(self,
              stream:  Union[TextIO, str],
              codec:   Codec,
              context: 'VerediContext') -> _DeserializeMidTypes:
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
        self._log_data_processing(self.dotted,
                                  "Reading from '{}'...",
                                  type(stream),
                                  context=context)
        if isinstance(stream, TextIOBase):
            self._log_data_processing(self.dotted,
                                      "Seek to beginning first.",
                                      context=context)
            # Assume we are supposed to read the entire stream.
            stream.seek(0)

        data = None
        try:
            data = self._json_load(stream, context)

        except json.JSONDecodeError as json_error:
            data = None
            error_info = {
                'data': stream,
            }
            error_info = self._stream_data(stream, error_info)
            msg = f"Error reading json from stream: {stream}"
            self._log_data_processing(self.dotted,
                                      msg,
                                      context=context,
                                      success=False)
            # TODO v://future/2021-03-14T12:27:54 - log 'data' field for
            # error_info.
            error = exceptions.ReadError(
                msg,
                context=context,
                data=error_info)
            raise log.exception(error, msg,
                                context=context) from json_error

        self._log_data_processing(self.dotted,
                                  "Read JSON from '{}'!",
                                  type(stream),
                                  context=context,
                                  success=True)
        return data

    def deserialize_all(self,
                        stream:  Union[TextIO, str],
                        codec:   Codec,
                        context: 'VerediContext') -> DeserializeTypes:
        '''
        Read and deserializes all documents from the data stream. Expects a
        valid/normal json document in the stream, since there isn't a "document
        separator" in the json spec like in other serialized formats.

        Raises:
          - exceptions.ReadError
            - wrapping a library error?
        '''
        self._log_data_processing(self.dotted,
                                  "Deserializing all from '{}'...",
                                  type(stream),
                                  context=context)
        self._context_data(context, DataAction.LOAD, codec)
        error_info = {
            'data': stream,
        }
        data = self._read_all(stream, codec, context)
        if not data:
            msg = "Deserializing all JSON from {} resulted in no data."
            error_info = self._stream_data(stream, error_info)
            self._log_data_processing(self.dotted,
                                      msg,
                                      type(stream),
                                      context=context,
                                      success=False)
            # TODO v://future/2021-03-14T12:27:54 - log 'data' field for
            # error_info.
            error = exceptions.ReadError(
                msg,
                type(stream),
                context=context,
                data=error_info)
            raise log.exception(error, msg,
                                context=context)

        self._log_data_processing(self.dotted,
                                  "Deserialized all from '{}'!",
                                  type(stream),
                                  context=context,
                                  success=True)
        return self._decode_all(data, codec)

    def _read_all(self,
                  stream:  Union[TextIO, str],
                  codec:   Codec,
                  context: 'VerediContext') -> _DeserializeAllMidTypes:
        '''
        Read data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.ReadError
            - wrapped lib/module errors
        '''
        self._log_data_processing(self.dotted,
                                  "Reading all from '{}'...",
                                  type(stream),
                                  context=context)
        # Just use read since json has no concept of multi-document streams.
        return self._read(stream, codec, context)

    # -------------------------------------------------------------------------
    # Serialize Methods
    # -------------------------------------------------------------------------

    def serialize(self,
                  data:    SerializeTypes,
                  codec:   Codec,
                  context: 'VerediContext') -> StringIO:
        '''
        Write and serializes a single document from the data stream.

        Raises:
          - exceptions.WriteError
            - wrapping a library error?
        '''
        self._log_data_processing(self.dotted,
                                  "Serializing from '{}'...",
                                  type(data),
                                  context=context)

        self._context_data(context, DataAction.SAVE, codec)
        to_serialize = self._serialize_prep(data, codec, context)
        stream = self._write(to_serialize, codec, context)

        self._log_data_processing(self.dotted,
                                  "Serialized from '{}'!",
                                  type(data),
                                  context=context,
                                  success=True)
        return stream

    def _json_dump(self,
                   dump_to: SerializeTypes,
                   stream:  Union[TextIO, str],
                   context: 'VerediContext') -> None:
        '''
        Calls `json.dump()` or `json.dumps()`, as appropriate, with correct
        hook(s), and returns json's result.

        `dump_to` is the stream or string or instance of whatever you want JSON
        dumped to. It will be serialzed to `dump_to` (unless it's immutable (str));
        `dump_to` is also returned.

        `stream` is the data to be dumped.
        '''
        if isinstance(stream, str):
            self._log_data_processing(self.dotted,
                                      "Serializing data to JSON string...",
                                      context=context)
            dump_to = json.dumps(dump_to,
                                 stream,
                                 cls=self._json_encoder)
        else:
            self._log_data_processing(self.dotted,
                                      "Serializing data to JSON stream/file...",
                                      context=context)
            dump_to = json.dump(dump_to,
                                stream,
                                cls=self._json_encoder)

        self._log_data_processing(self.dotted,
                                  "Serialized data to JSON.",
                                  context=context,
                                  success=True)
        return dump_to

    def _serialize_prep(self,
                        data:    SerializeTypes,
                        codec:   Codec,
                        context: 'VerediContext') -> Mapping[str, Any]:
        '''
        Tries to turn the various possibilities for data (list, dict, etc) into
        something ready for json to serialize.
        '''
        self._log_data_processing(self.dotted,
                                  "Serialize preparation...",
                                  context=context)
        serialized = None
        if null_or_none(data):
            self._log_data_processing(self.dotted,
                                      "No data to prep.",
                                      context=context)
            return serialized

        # Is it just an Encodable object?
        if isinstance(data, Encodable):
            self._log_data_processing(self.dotted,
                                      "Encoding `Encodable` data "
                                      "for serialization.",
                                      context=context)
            serialized = codec.encode(data)
            return serialized

        # Is it a simple type?
        if text.serialize_claim(data) or time.serialize_claim(data):
            # Let json handle it.
            serialized = data
            return serialized
        if paths.serialize_claim(data):
            serialized = paths.serialize(data)
            return serialized
        if numbers.serialize_claim(data):
            serialized = numbers.serialize(data)
            return serialized

        # Mapping?
        with contextlib.suppress(AttributeError, TypeError):
            # Do the thing that spawns the exception before
            # we log about doing the thing...
            keys = data.keys()
            self._log_data_processing(self.dotted,
                                      "Prepping `Mapping` of data "
                                      "for serialization.",
                                      context=context)
            serialized = {}
            for each in keys:
                # TODO [2020-07-29]: Change to non-recursive?
                serialized[str(each)] = self._serialize_prep(data[each],
                                                             codec,
                                                             context)
            return serialized

        # Iterable
        with contextlib.suppress(AttributeError, TypeError):
            # Do the thing that spawns the exception before
            # we log about doing the thing...
            iterable = iter(data)
            self._log_data_processing(self.dotted,
                                      "Prepping `Iterable` of data "
                                      "for serialization.",
                                      context=context)
            serialized = []
            for each in iterable:
                # TODO [2020-07-29]: Change to non-recursive?
                serialized.append(self._serialize_prep(each, codec, context))
            return serialized

        # Falling through to here is bad; raise Exception.
        msg = f"Don't know how to process '{type(data)}' data."
        self._log_data_processing(self.dotted,
                                  msg,
                                  context=context,
                                  success=False)
        error = exceptions.WriteError(msg,
                                      context=context,
                                      data={
                                          'data': data,
                                      })
        raise log.exception(error, msg,
                            context=context)

    def _write(self,
               data:    SerializeTypes,
               codec:   Codec,
               context: 'VerediContext') -> StringIO:
        '''
        Write data to a stream.

        Returns:
          The stream with the serialized data in it.

        Raises:
          - exceptions.WriteError
            - wrapped lib/module errors
        '''
        self._log_data_processing(self.dotted,
                                  "Writing '{}' to stream...",
                                  type(data),
                                  context=context)
        serialized = StringIO()
        try:
            self._json_dump(data, serialized, context)
        except (TypeError, OverflowError, ValueError) as json_error:
            serialized = None
            # data_pretty = pretty.indented(data)
            msg = f"Error writing data '{type(data)}' to stream."
            self._log_data_processing(self.dotted,
                                      msg,
                                      context=context,
                                      success=False)
            error = exceptions.WriteError(msg,
                                          context=context,
                                          data={
                                              'data': data,
                                          })
            raise log.exception(error, msg,
                                context=context) from json_error

        self._log_data_processing(self.dotted,
                                  "Wrote '{}' to JSON!",
                                  type(data),
                                  context=context,
                                  success=True)
        return serialized

    def serialize_all(self,
                      data:    SerializeTypes,
                      codec:   Codec,
                      context: 'VerediContext') -> StringIO:
        '''
        Write and serializes all documents from the data stream.

        Returns:
          The stream with the serialized data in it.

        Raises:
          - exceptions.WriteError
            - wrapped lib/module errors
        '''
        self._log_data_processing(self.dotted,
                                  "Serializing all from '{}'...",
                                  type(data),
                                  context=context)

        self._context_data(context, DataAction.SAVE, codec)
        to_serialize = self._serialize_prep(data, codec, context)
        stream = self._write(to_serialize, codec, context)

        self._log_data_processing(self.dotted,
                                  "Serialized all from '{}'!",
                                  type(data),
                                  context=context)
        return stream

    def _write_all(self,
                   data:    SerializeTypes,
                   codec:   Codec,
                   context: 'VerediContext') -> StringIO:
        '''
        Write and serializes all documents from the data stream.

        Returns:
          The serialized data in a StringIO buffer.

        Raises:
          - exceptions.WriteError
            - wrapped lib/module errors
        '''
        self._log_data_processing(self.dotted,
                                  "Writing all '{}' to stream...",
                                  type(data),
                                  context=context)
        # Just use _write() since json has no concept of multi-document
        # streams.
        return self._write(data, codec, context)


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
