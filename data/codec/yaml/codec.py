# coding: utf-8

'''
Reader/Loader & Writer/Dumper of YAML Format.
Aka YAML Codec.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Any, TextIO, Iterable)
if TYPE_CHECKING:
    from veredi.base.context import VerediContext
    from veredi.data.config.context import ConfigContext

import yaml

from veredi.logger               import log

from veredi.data                 import background
from veredi.data.config.registry import register
from veredi.data                 import exceptions

from ..base                      import BaseCodec, CodecOutput

# import these so they register with PyYAML.
from .                           import (function,
                                         document)
from .ecs                        import (general,
                                         template,
                                         component,
                                         system)
from .interface.output           import event


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'codec', 'yaml')
class YamlCodec(BaseCodec):
    # https://pyyaml.org/wiki/PyYAMLDocumentation

    _SANITIZE_KEYCHAIN = ['game', 'repository', 'sanitize']

    _CODEC_NAME   = 'yaml'

    def __init__(self,
                 context: Optional['VerediContext'] = None) -> None:
        super().__init__(YamlCodec._CODEC_NAME,
                         context)

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''Config from context and elsewhere.'''
        # Set up our background for when it gets pulled in.
        self._make_background()

    def _make_background(self) -> None:
        self._bg = super()._make_background(self.dotted)

    @property
    def background(self):
        '''
        Data for the Veredi Background context.

        Returns: (data, background.Ownership)
        '''
        return self._bg, background.Ownership.SHARE

    # -------------------------------------------------------------------------
    # Decode Methods
    # -------------------------------------------------------------------------

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

    def decode(self,
               stream: TextIO,
               input_context: 'VerediContext') -> CodecOutput:
        '''Read and decodes data from a single data stream.

        Raises:
          - exceptions.ReadError
            - wrapped yaml.YAMLDecodeError
          Maybes:
            - Other yaml/stream errors?
        '''

        self._context_decode_data(input_context)
        data = self._read(stream, input_context)

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

    def decode_all(self,
                   stream: TextIO,
                   input_context: 'VerediContext') -> CodecOutput:
        '''Read and decodes data from a single data stream.

        Raises:
          - exceptions.ReadError
            - wrapped yaml.YAMLDecodeError
          Maybes:
            - Other yaml/stream errors?
        '''

        self._context_decode_data(input_context)
        data = self._read_all(stream, input_context)
        if not data:
            raise log.exception(
                None,
                exceptions.ReadError,
                "Reading yaml from stream resulted in no data: {}",
                stream,
                context=input_context)

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
              stream: TextIO,
              input_context: 'VerediContext') -> Any:
        '''Read data from a single data stream.

        Returns:
          Output of yaml.safe_load().
          Mix of:
            - yaml objects
            - our subclasses of yaml objects
            - and python objects

        Raises:
          - exceptions.ReadError
            - wrapped yaml.YAMLDecodeError
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
                context=input_context) from error
        return data

    def _read_all(self,
                  stream: TextIO,
                  input_context: 'VerediContext') -> Any:
        '''Read data from a single data stream.

        Returns:
          Output of yaml.safe_load_all().
          Mix of:
            - yaml objects
            - our subclasses of yaml objects
            - and python objects

        Raises:
          - exceptions.ReadError
            - wrapped yaml.YAMLDecodeError
          Maybes:
            - Other yaml/stream errors?
        '''

        # print('Codec read:', stream.read(None))
        # log.critical("\n\nstream at: {} {}", str(type(stream.tell())), str(stream.tell()))
        # stream.seek(0)

        data = None
        try:
            data = yaml.safe_load_all(stream)
            data = self._finish_read(data)
            # if not data:
            #     log.critical("DED STREAM!!!")
            # import pprint
            # print(f"\n\n{self.__class__.__name__}.decode_all:\n  context: \n{pprint.pformat(input_context)}\n\n   data = \n{pprint.pformat(data)}\n\n")
        except yaml.YAMLError as error:
            data = None
            raise log.exception(
                error,
                exceptions.ReadError,
                'YAML failed while reading all the data.',
                context=input_context) from error

        return data

    def _finish_read(self, data: Any) -> None:
        '''
        safe_load_all() returns a generator. We don't want a generator... We
        need to get the data out of the stream before the stream goes bye
        bye, so turn it into a list.
        '''
        return list(data)

    # -------------------------------------------------------------------------
    # Encode Methods
    # -------------------------------------------------------------------------

    def encode(self,
               data: Any,
               context: 'VerediContext') -> str:
        '''
        Encodes data from a single data object.

        Raises:
          - exceptions.WriteError
            - wrapped yaml.YAMLEncodeError
        '''

        # self._context_encode_data(input_context)
        output = self._write(data, context)
        if not output:
            raise log.exception(
                None,
                exceptions.WriteError,
                "Writing yaml from data resulted in no output: {}",
                output,
                context=context)

        # TODO: Here is where we'd check for sanity and stuff?

        return output

    def encode_all(self,
                   data: Iterable[Any],
                   context: 'VerediContext') -> str:
        '''
        Encodes data from an iterable of data objects. Each will be a separate
        yaml doc in the output.

        Raises:
          - exceptions.WriteError
            - wrapped yaml.YAMLEncodeError
        '''

        # self._context_encode_data(context)
        output = self._write_all(data, context)
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
               data: Any,
               context: 'VerediContext') -> str:
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
            - wrapped yaml.YAMLEncodeError
          Maybes:
            - Other yaml/stream errors?
        '''

        output = None
        try:
            output = yaml.safe_dump(data, default_flow_style=None)
            # TODO [2020-07-04]: may need to evaluate this in some way to get
            # it past its lazy writeing... I want to catch any yaml exceptions
            # here and not let them infect unrelated code.
        except yaml.YAMLError as error:
            output = None
            raise log.exception(
                error,
                exceptions.WriteError,
                'YAML failed while writing the data.',
                context=context) from error

        return output

    def _write_all(self,
                   data: Any,
                   context: 'VerediContext') -> str:
        '''Write data from a single data stream.

        Returns:
          Output of yaml.safe_dump_all().
          Mix of:
            - yaml objects
            - our subclasses of yaml objects
            - and python objects

        Raises:
          - exceptions.WriteError
            - wrapped yaml.YAMLEncodeError
          Maybes:
            - Other yaml/stream errors?
        '''

        # print('Codec read:', stream.read(None))
        # stream.seek(0)

        output = None
        try:
            output = yaml.safe_dump_all(data, default_flow_style=None)
            # print(f"{self.__class__.__name__}.encode_all: output = {output}")
        except yaml.YAMLError as error:
            output = None
            raise log.exception(
                error,
                exceptions.WriteError,
                'YAML failed while writing all the data.',
                context=context) from error

        return output
