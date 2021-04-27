# coding: utf-8

'''
Reader/Loader & Writer/Dumper of YAML Format.
Aka YAML Serdes.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, TextIO, Mapping, Iterable,
                    Dict, List)
from veredi.base.null import null_or_none
if TYPE_CHECKING:
    from veredi.base.context        import VerediContext
    from veredi.data.config.context import ConfigContext

from io import StringIO, TextIOBase
import contextlib

from veredi.logs                 import log

from veredi                      import time
from veredi.base                 import paths, numbers
from veredi.base                 import yaml
from veredi.base.strings         import label, text

from veredi.data                 import background
from veredi.data                 import exceptions
from veredi.data.context         import DataAction
from veredi.data.codec           import Codec, Encodable

from ..base                      import (BaseSerdes,
                                         DeserializeTypes,
                                         DeserializeAllTypes,
                                         _DeserializeMidTypes,
                                         _DeserializeAllMidTypes,
                                         SerializeTypes)

from .                           import adapters
from .adapters.base              import VerediYamlDocument, VerediYamlObject


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class YamlSerdes(BaseSerdes,
                 name_dotted='veredi.serdes.yaml',
                 name_string='yaml'):
    '''
    Uses PyYAML to serialize/deserialize the YAML format.
    '''
    # https://pyyaml.org/wiki/PyYAMLDocumentation

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 context: Optional['VerediContext'] = None) -> None:
        super().__init__(context)

        # TODO: register differenter?
        adapters.import_and_register()

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

    def _decode(self,
                data:  _DeserializeMidTypes,
                codec: Codec) -> DeserializeTypes:
        '''
        Deserialize one YAMLObject.
        '''
        # Have our yaml.YAMLObject sub-classes do anything they want to first.
        # They should return a dict which can then be decoded.
        deserialized = data
        if isinstance(data, (VerediYamlDocument, VerediYamlObject)):
            deserialized = data.deserialize()

        return super()._decode(deserialized, codec)

    def deserialize(self,
                    stream:  Union[TextIO, str],
                    codec:   Codec,
                    context: 'VerediContext') -> DeserializeTypes:
        '''
        Read and deserializes data from a single data stream.

        Raises:
          - exceptions.ReadError
          Maybes:
            - Other yaml/stream errors?
        '''
        self._log_data_processing(self.dotted,
                                  "Deserializing from '{}'...",
                                  type(stream),
                                  context=context)

        self._context_data(context, DataAction.LOAD, codec)
        data = self._read(stream, codec, context)
        if not data:
            msg = "Reading yaml from stream resulted in no data."
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
            raise log.exception(error, msg, context=context)

        # TODO: Here is where we'd check metadata for versions and stuff?

        # TODO: Here is where we'd verify data against templates
        # and requirements.

        # Convert YAML output to game data. YAML output is a mix of:
        #   - yaml objects
        #   - our subclasses of yaml objects
        #   - and python objects
        #
        # Game data should just be python: dicts, lists, str, int, etc.
        self._log_data_processing(self.dotted,
                                  "Deserialized to '{}'!",
                                  type(data),
                                  context=context)
        return self._decode(data, codec)

    def deserialize_all(self,
                        stream:  Union[TextIO, str],
                        codec:   Codec,
                        context: 'VerediContext') -> DeserializeAllTypes:
        '''
        Read and deserializes data from a single data stream.

        Raises:
          - exceptions.ReadError
          Maybes:
            - Other yaml/stream errors?
        '''
        self._log_data_processing(self.dotted,
                                  "Deserializing all from '{}'...",
                                  type(stream),
                                  context=context)
        self._context_data(context, DataAction.LOAD, codec)
        data = self._read_all(stream, codec, context)
        if not data:
            msg = "Reading all yaml from stream resulted in no data."
            self._log_data_processing(self.dotted,
                                      msg,
                                      type(stream),
                                      context=context,
                                      success=False)
            error = exceptions.ReadError(
                msg,
                context=context,
                data={
                    'data': data,
                })
            raise log.exception(error, msg, context=context)

        # TODO: Here is where we'd check metadata for versions and stuff?

        # TODO: Here is where we'd verify data against templates
        # and requirements.

        # Convert YAML output to game data. YAML output is a mix of:
        #   - yaml objects
        #   - our subclasses of yaml objects
        #   - and python objects
        #
        # Game data should just be python: dicts, lists, str, int, etc.
        self._log_data_processing(self.dotted,
                                  "Deserialized all from '{}'!",
                                  type(stream),
                                  context=context,
                                  success=True)
        return self._decode_all(data, codec)

    def _read(self,
              stream:  Union[TextIO, str],
              codec:   Codec,
              context: 'VerediContext') -> _DeserializeMidTypes:
        '''
        Read data from a single data stream.

        Returns:
          Output of yaml.safe_load().
          Mix of:
            - yaml objects
            - our subclasses of yaml objects
            - and python objects

        Raises:
          - exceptions.ReadError
          Maybes:
            - Other yaml/stream errors?
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
            data = yaml.safe_load(stream)
            # TODO [2020-07-04]: may need to evaluate this in some way to get
            # it past its lazy loading... I want to catch any yaml exceptions
            # here and not let them infect unrelated code.
        except yaml.YAMLError as yaml_error:
            data = None
            error_info = {
                'data': stream,
            }
            error_info = self._stream_data(stream, error_info)
            msg = 'YAML failed while reading the data.'
            self._log_data_processing(self.dotted,
                                      msg,
                                      context=context,
                                      success=False)
            error = exceptions.ReadError(
                msg,
                context=context,
                data=error_info)
            raise log.exception(error, msg, context=context) from yaml_error

        self._log_data_processing(self.dotted,
                                  "Read YAML from '{}'!",
                                  type(stream),
                                  context=context,
                                  success=True)
        return data

    def _read_all(self,
                  stream:  Union[TextIO, str],
                  codec:   Codec,
                  context: 'VerediContext') -> _DeserializeAllMidTypes:
        '''
        Read data from a single data stream.

        Returns:
          Output of yaml.safe_load_all().
          Mix of:
            - yaml objects
            - our subclasses of yaml objects
            - and python objects

        Raises:
          - exceptions.ReadError
          Maybes:
            - Other yaml/stream errors?
        '''
        self._log_data_processing(self.dotted,
                                  "Reading all from '{}'...",
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
            data = yaml.safe_load_all(stream)
            data = self._finish_read(data)
        except yaml.YAMLError as yaml_error:
            data = None
            msg = 'YAML failed while reading all the data.'
            error_info = {
                'data': stream,
            }
            error_info = self._stream_data(stream, error_info)
            self._log_data_processing(self.dotted,
                                      msg,
                                      context=context,
                                      success=False)
            error = exceptions.ReadError(
                msg,
                context=context,
                data=error_info)
            raise log.exception(error, msg, context=context) from yaml_error

        self._log_data_processing(self.dotted,
                                  "Read all YAML from '{}'!",
                                  type(stream),
                                  context=context,
                                  success=True)
        return data

    def _finish_read(self, data: Any) -> List[_DeserializeAllMidTypes]:
        '''
        safe_load_all() returns a generator. We don't want a generator... We
        need to get the data out of the stream before the stream goes bye
        bye, so turn it into a list.
        '''
        return list(data)

    # -------------------------------------------------------------------------
    # Serialize Methods
    # -------------------------------------------------------------------------

    def _serialize_prep(self,
                        data:    SerializeTypes,
                        codec:   Codec,
                        context: 'VerediContext') -> Mapping[str, Any]:
        '''
        Tries to turn the various possibilities for data (list, dict, etc) into
        something ready for yaml to serialize.
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

        # Iterable?
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

        msg = "Don't know how to process data"
        self._log_data_processing(self.dotted,
                                  msg,
                                  context=context,
                                  success=False)
        error = exceptions.WriteError(msg,
                                      context=context,
                                      data={
                                          'errored-on': data,
                                      })
        raise log.exception(error,
                            msg,  # + f" data: {data}",
                            context=context)

    def serialize(self,
                  data:    SerializeTypes,
                  codec:   Codec,
                  context: 'VerediContext') -> StringIO:
        '''
        Serializes data from a single data object.

        Raises:
          - exceptions.WriteError
        '''
        self._log_data_processing(self.dotted,
                                  "Serializing from '{}'...",
                                  type(data),
                                  context=context)

        self._context_data(context, DataAction.SAVE, codec)
        to_serialize = self._serialize_prep(data, codec, context)
        output = self._write(to_serialize, codec, context)
        if not output:
            msg = f"Serializing yaml from data resulted in no output: {output}"
            self._log_data_processing(self.dotted,
                                      msg,
                                      context=context,
                                      success=False)
            error = exceptions.WriteError(msg,
                                          context=context,
                                          data={
                                              'data': data,
                                          })
            raise log.exception(error, msg, context=context)

        self._log_data_processing(self.dotted,
                                  "Serialized from '{}'!",
                                  type(data),
                                  context=context,
                                  success=True)
        return output

    def serialize_all(self,
                      data:    SerializeTypes,
                      codec:   Codec,
                      context: 'VerediContext') -> StringIO:
        '''
        Serializes data from an iterable of data objects. Each will be a
        separate yaml doc in the output.

        Raises:
          - exceptions.WriteError
        '''
        self._log_data_processing(self.dotted,
                                  "Serializing all from '{}'...",
                                  type(data),
                                  context=context)

        to_serialize = self._serialize_prep(data, codec, context)
        self._context_data(context, DataAction.SAVE, codec)
        output = self._write_all(to_serialize, codec, context)
        if not output:
            msg = (f"Serializing all yaml from data "
                   "resulted in no output: {output}")
            self._log_data_processing(self.dotted,
                                      msg,
                                      context=context,
                                      success=False)
            error = exceptions.WriteError(msg,
                                          context=context,
                                          data={
                                              'data': data,
                                          })
            raise log.exception(error, msg, context=context)

        # TODO: Here is where we'd check for sanity and stuff?

        self._log_data_processing(self.dotted,
                                  "Serialized all from '{}'!",
                                  type(data),
                                  context=context,
                                  success=True)
        return output

    def _write(self,
               data:    SerializeTypes,
               codec:   Codec,
               context: 'VerediContext') -> StringIO:
        '''
        Write data from a single data stream.

        Returns:
          Output of yaml.safe_dump().
          Mix of:
            - yaml objects
            - our subclasses of yaml objects
            - and python objects

        Raises:
          - exceptions.WriteError
          Maybes:
            - Other yaml/stream errors?
        '''
        self._log_data_processing(self.dotted,
                                  "Writing '{}' to stream...",
                                  type(data),
                                  context=context)
        serialized = StringIO()
        try:
            yaml.safe_dump(data,
                           default_sequence=yaml.SequenceStyle.DEFAULT,
                           stream=serialized)
            # TODO [2020-07-04]: may need to evaluate this in some way to get
            # it past its lazy writing... I want to catch any yaml exceptions
            # here and not let them infect unrelated code.

        except yaml.YAMLError as yaml_error:
            serialized = None
            msg = 'YAML failed while writing the data.'
            self._log_data_processing(self.dotted,
                                      msg,
                                      context=context,
                                      success=False)
            error = exceptions.WriteError(msg,
                                          context=context,
                                          data={
                                              'data': data,
                                          })
            raise log.exception(error, msg, context=context) from yaml_error

        # Apparently yaml doesn't give us the spot in the stream it started
        # writing, so rewind.
        serialized.seek(0)

        self._log_data_processing(self.dotted,
                                  "Wrote '{}' to YAML!",
                                  type(data),
                                  context=context,
                                  success=True)
        return serialized

    def _write_all(self,
                   data:    SerializeTypes,
                   codec:   Codec,
                   context: 'VerediContext') -> StringIO:
        '''
        Write data from a single data stream.

        Returns:
          Output of yaml.safe_dump_all().
          Mix of:
            - yaml objects
            - our subclasses of yaml objects
            - and python objects

        Raises:
          - exceptions.WriteError
          Maybes:
            - Other yaml/stream errors?
        '''

        self._log_data_processing(self.dotted,
                                  "Writing all '{}' to stream...",
                                  type(data),
                                  context=context)

        serialized = StringIO()
        try:
            yaml.safe_dump_all(data,
                               default_sequence=yaml.SequenceStyle.DEFAULT,
                               stream=serialized)

        except yaml.YAMLError as yaml_error:
            serialized = None
            msg = 'YAML failed while writing all the data.'
            self._log_data_processing(self.dotted,
                                      msg,
                                      context=context,
                                      success=False)
            error = exceptions.WriteError(msg,
                                          context=context,
                                          data={
                                              'data': data,
                                          })
            raise log.exception(error, msg, context=context) from yaml_error

        # Apparently yaml doesn't give us the spot in the stream it started
        # writing, so rewind.
        serialized.seek(0)

        self._log_data_processing(self.dotted,
                                  "Wrote '{}' to YAML!",
                                  type(data),
                                  context=context,
                                  success=True)
        return serialized
