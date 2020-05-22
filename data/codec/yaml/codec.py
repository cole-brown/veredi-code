# coding: utf-8

'''
Reader/Loader & Writer/Dumper of YAML Format.
Aka YAML Codec.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import yaml

from veredi.logger import log
from veredi.data.config.registry import register
from veredi.data import exceptions

from ..base import BaseCodec

from . import function
from . import document
from . import component


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'codec', 'yaml')
class YamlCodec(BaseCodec):
    _NAME = 'yaml'

    # https://pyyaml.org/wiki/PyYAMLDocumentation

    def load(self, stream, error_context):
        '''Load and decodes data from a single data file.

        Raises:
          - exceptions.LoadError
            - wrapped yaml.YAMLDecodeError
          Maybes:
            - Other yaml/file errors?
        '''

        # §-TODO-§ [2020-05-06]: Read Metadata (type, version, etc),
        # verify them?

        data = None
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            log.error('YAML failed while loading the file. {} {}',
                      error.__class__.__qualname__,
                      error_context)
            data = None
            raise exceptions.LoadError("Error loading yaml file:",
                                       error,
                                       error_context) from error
        return data

    def load_all(self, stream, error_context):
        '''Load and decodes data from a single data file.

        Raises:
          - exceptions.LoadError
            - wrapped yaml.YAMLDecodeError
          Maybes:
            - Other yaml/file errors?
        '''

        # §-TODO-§ [2020-05-06]: Read type and version, verify them?
        # Only one per file?

        data = None
        try:
            data = yaml.safe_load_all(stream)
            # print(f"{self.__class__.__name__}.load_all: data = {data}")
        except yaml.YAMLError as error:
            log.error('YAML failed while loading the file. {} {}',
                      error.__class__.__qualname__,
                      error_context)
            data = None
            raise exceptions.LoadError("Error loading yaml file:",
                                       error,
                                       error_context) from error
        return data
