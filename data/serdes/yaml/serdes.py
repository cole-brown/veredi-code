# coding: utf-8

'''
Reader/Loader & Writer/Dumper of YAML Format.
Aka YAML Serdes.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, TextIO, Iterable, Mapping)
from veredi.base.null import null_or_none
if TYPE_CHECKING:
    from veredi.base.context import VerediContext
    from veredi.data.config.context import ConfigContext

import yaml
from io import StringIO
import contextlib

from veredi.logger               import log

from veredi.data                 import background
from veredi.data.config.registry import register
from veredi.data                 import exceptions

from ...codec.encodable          import Encodable
from ..base                      import (BaseSerdes,
                                         DeserializeTypes,
                                         SerializeTypes)

from . import adapters


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'serdes', 'yaml')
class YamlSerdes(BaseSerdes):
    # https://pyyaml.org/wiki/PyYAMLDocumentation

    _SANITIZE_KEYCHAIN = ['game', 'repository', 'sanitize']

    _SERDES_NAME   = 'yaml'

    def __init__(self,
                 context: Optional['VerediContext'] = None) -> None:
        super().__init__(YamlSerdes._SERDES_NAME,
                         context)

        adapters.import_and_register()

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''Config from context and elsewhere.'''
        # Set up our background for when it gets pulled in.
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

    def _context_deserialize_data(self,
                             context: 'VerediContext') -> 'VerediContext':
        '''
        Inject our serdes data into the context.
        '''
        meta, _ = self.background
        context[str(background.Name.SERDES)] = {
            'meta': meta,
        }
        return context

    # -------------------------------------------------------------------------
    # Deserialize Methods
    # -------------------------------------------------------------------------

    def deserialize(self,
               stream: Union[TextIO, str],
               context: 'VerediContext') -> DeserializeTypes:
        '''Read and deserializes data from a single data stream.

        Raises:
          - exceptions.ReadError
            - wrapped yaml.YAMLDeserializeError
          Maybes:
            - Other yaml/stream errors?
        '''

        self._context_deserialize_data(context)
        data = self._read(stream, context)

        # TODO: Here is where we'd check metadata for versions and stuff?

        # TODO: Here is where we'd verify data against templates
        # and requirements.

        # Convert YAML output to game data. YAML output is a mix of:
        #   - yaml objects
        #   - our subclasses of yaml objects
        #   - and python objects
        #
        # Game data should just be python: dicts, lists, str, int, etc.
        return self._to_game(data)

    def deserialize_all(self,
                   stream: Union[TextIO, str],
                   context: 'VerediContext') -> DeserializeTypes:
        '''Read and deserializes data from a single data stream.

        Raises:
          - exceptions.ReadError
            - wrapped yaml.YAMLDeserializeError
          Maybes:
            - Other yaml/stream errors?
        '''

        self._context_deserialize_data(context)
        data = self._read_all(stream, context)
        if not data:
            raise log.exception(
                None,
                exceptions.ReadError,
                "Reading yaml from stream resulted in no data: {}",
                stream,
                context=context)

        # TODO: Here is where we'd check metadata for versions and stuff?

        # TODO: Here is where we'd verify data against templates
        # and requirements.

        # Convert YAML output to game data. YAML output is a mix of:
        #   - yaml objects
        #   - our subclasses of yaml objects
        #   - and python objects
        #
        # Game data should just be python: dicts, lists, str, int, etc.
        return self._to_game(data)

    def _to_game(self, yaml_data):
        '''
        Convert yaml data to game data.

        Put yaml docs into proper slots or drop them.
        '''
        data = []
        for doc in yaml_data:
            data.append(doc.decode())
        return data

    def _read(self,
              stream: Union[TextIO, str],
              context: 'VerediContext') -> Any:
        '''Read data from a single data stream.

        Returns:
          Output of yaml.safe_load().
          Mix of:
            - yaml objects
            - our subclasses of yaml objects
            - and python objects

        Raises:
          - exceptions.ReadError
            - wrapped yaml.YAMLDeserializeError
          Maybes:
            - Other yaml/stream errors?
        '''

        data = None
        try:
            data = yaml.safe_load(stream)
            # TODO [2020-07-04]: may need to evaluate this in some way to get
            # it past its lazy loading... I want to catch any yaml exceptions
            # here and not let them infect unrelated code.
        except yaml.YAMLError as error:
            data = None
            raise log.exception(
                error,
                exceptions.ReadError,
                'YAML failed while reading the data.',
                context=context) from error
        return data

    def _read_all(self,
                  stream: Union[TextIO, str],
                  context: 'VerediContext') -> Any:
        '''Read data from a single data stream.

        Returns:
          Output of yaml.safe_load_all().
          Mix of:
            - yaml objects
            - our subclasses of yaml objects
            - and python objects

        Raises:
          - exceptions.ReadError
            - wrapped yaml.YAMLDeserializeError
          Maybes:
            - Other yaml/stream errors?
        '''

        data = None
        try:
            data = yaml.safe_load_all(stream)
            data = self._finish_read(data)
        except yaml.YAMLError as error:
            data = None
            raise log.exception(
                error,
                exceptions.ReadError,
                'YAML failed while reading all the data.',
                context=context) from error

        return data

    def _finish_read(self, data: Any) -> None:
        '''
        safe_load_all() returns a generator. We don't want a generator... We
        need to get the data out of the stream before the stream goes bye
        bye, so turn it into a list.
        '''
        return list(data)

    # -------------------------------------------------------------------------
    # Serialize Methods
    # -------------------------------------------------------------------------

    def _context_serialize_data(self,
                             context: 'VerediContext') -> 'VerediContext':
        '''
        Inject our serdes data into the context.
        '''
        meta, _ = self.background
        context[str(background.Name.SERDES)] = {
            'meta': meta,
        }
        return context

    def _serialize_prep(self,
                     data: SerializeTypes,
                     context: 'VerediContext') -> Mapping[str, Any]:
        '''
        Tries to turn the various possibilities for data (list, dict, etc) into
        something ready for yaml to serialize.
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
                serialized[str(each)] = self._serialize_prepass(data[each], context)
            return serialized

        # Iterable
        with contextlib.suppress(AttributeError):
            serialized = []
            for each in data:
                # TODO [2020-07-29]: Change to non-recursive?
                serialized.append(self._serialize_prepass(each), context)
            return serialized

        msg = "Don't know how to process data."
        raise log.exception(
            ValueError(msg, data),
            exceptions.WriteError,
            msg + f" data: {data}",
            context=context)

    def serialize(self,
               data: SerializeTypes,
               context: 'VerediContext') -> StringIO:
        '''
        Serializes data from a single data object.

        Raises:
          - exceptions.WriteError
            - wrapped yaml.YAMLSerializeError
        '''

        # self._context_serialize_data(context)
        log.debug(f"serialize data: {data}")
        to_serialize = self._serialize_prep(data, context)
        output = self._write(to_serialize, context)
        if not output:
            raise log.exception(
                None,
                exceptions.WriteError,
                "Writing yaml from data resulted in no output: {}",
                output,
                context=context)
        return output

    def serialize_all(self,
                   data: SerializeTypes,
                   context: 'VerediContext') -> StringIO:
        '''
        Serializes data from an iterable of data objects. Each will be a separate
        yaml doc in the output.

        Raises:
          - exceptions.WriteError
            - wrapped yaml.YAMLSerializeError
        '''

        to_serialize = self._serialize_prep(data, context)
        # self._context_serialize_data(context)
        output = self._write_all(to_serialize, context)
        if not output:
            raise log.exception(
                None,
                exceptions.WriteError,
                "Writing yaml from data resulted in no output: {}",
                output,
                context=context)

        # TODO: Here is where we'd check for sanity and stuff?

        return output

    def _write(self,
               data: SerializeTypes,
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
            - wrapped yaml.YAMLSerializeError
          Maybes:
            - Other yaml/stream errors?
        '''

        serialized = StringIO()
        try:
            yaml.safe_dump(data, default_flow_style=None, stream=serialized)
            # TODO [2020-07-04]: may need to evaluate this in some way to get
            # it past its lazy writeing... I want to catch any yaml exceptions
            # here and not let them infect unrelated code.
        except yaml.YAMLError as error:
            serialized = None
            raise log.exception(
                error,
                exceptions.WriteError,
                'YAML failed while writing the data.',
                context=context) from error

        return serialized

    def _write_all(self,
                   data: SerializeTypes,
                   context: 'VerediContext') -> StringIO:
        '''Write data from a single data stream.

        Returns:
          Output of yaml.safe_dump_all().
          Mix of:
            - yaml objects
            - our subclasses of yaml objects
            - and python objects

        Raises:
          - exceptions.WriteError
            - wrapped yaml.YAMLSerializeError
          Maybes:
            - Other yaml/stream errors?
        '''

        # print('Serdes read:', stream.read(None))
        # stream.seek(0)

        serialized = StringIO()
        try:
            yaml.safe_dump_all(data, default_flow_style=None, stream=serialized)
            # print(f"{self.__class__.__name__}.serialize_all: output = {output}")
        except yaml.YAMLError as error:
            serialized = None
            raise log.exception(
                error,
                exceptions.WriteError,
                'YAML failed while writing all the data.',
                context=context) from error

        return serialized
