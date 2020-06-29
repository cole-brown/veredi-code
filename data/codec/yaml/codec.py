# coding: utf-8

'''
Reader/Loader & Writer/Dumper of YAML Format.
Aka YAML Codec.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Any, TextIO)
if TYPE_CHECKING:
    from veredi.base.context import VerediContext
    from veredi.data.config.context import ConfigContext


import yaml

from veredi.logger import log

from veredi.data import background
from veredi.data.config.registry import register
from veredi.data import exceptions

from ..base import BaseCodec, CodecOutput

# import these so they register with PyYAML.
from . import function
from . import document
from .ecs import general
from .ecs import template
from .ecs import component
from .ecs import system


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'codec', 'yaml')
class YamlCodec(BaseCodec):
    # https://pyyaml.org/wiki/PyYAMLDocumentation

    _DOTTED_NAME = 'veredi.codec.yaml'

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
        self._bg = super()._make_background(self._DOTTED_NAME)

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
        Inject our repository data and our load data into the context.
        In the case of file repositories, include the file path.
        '''
        context[str(background.Name.CODEC)] = {
            'meta': background.data.codec,
        }
        return context

    def decode(self,
               stream: TextIO,
               input_context: 'VerediContext') -> CodecOutput:
        '''Load and decodes data from a single data stream.

        Raises:
          - exceptions.LoadError
            - wrapped yaml.YAMLDecodeError
          Maybes:
            - Other yaml/stream errors?
        '''

        self._context_decode_data(input_context)
        data = self._load(stream, input_context)

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
        '''Load and decodes data from a single data stream.

        Raises:
          - exceptions.LoadError
            - wrapped yaml.YAMLDecodeError
          Maybes:
            - Other yaml/stream errors?
        '''

        self._context_decode_data(input_context)
        data = self._load_all(stream, input_context)
        if not data:
            raise log.exception(
                None,
                exceptions.LoadError,
                "Loading yaml from stream resulted in no data: {}",
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

    def _load(self,
              stream: TextIO,
              input_context: 'VerediContext') -> Any:
        '''Load data from a single data stream.

        Returns:
          Output of yaml.safe_load().
          Mix of:
            - yaml objects
            - our subclasses of yaml objects
            - and python objects

        Raises:
          - exceptions.LoadError
            - wrapped yaml.YAMLDecodeError
          Maybes:
            - Other yaml/stream errors?
        '''

        data = None
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            data = None
            raise log.exception(
                error,
                exceptions.LoadError,
                'YAML failed while loading the data.',
                context=input_context) from error
        return data

    def _load_all(self,
                  stream: TextIO,
                  input_context: 'VerediContext') -> Any:
        '''Load data from a single data stream.

        Returns:
          Output of yaml.safe_load_all().
          Mix of:
            - yaml objects
            - our subclasses of yaml objects
            - and python objects

        Raises:
          - exceptions.LoadError
            - wrapped yaml.YAMLDecodeError
          Maybes:
            - Other yaml/stream errors?
        '''

        data = None
        try:
            data = yaml.safe_load_all(stream)
            # print(f"{self.__class__.__name__}.decode_all: data = {data}")
        except yaml.YAMLError as error:
            data = None
            raise log.exception(
                error,
                exceptions.LoadError,
                'YAML failed while loading all the data. {}',
                context=input_context) from error

        # safe_load_all() returns a generator. We don't want a generator... We
        # need to get the data out of the stream before the stream goes bye
        # bye, so turn it into a list.
        return list(data)
