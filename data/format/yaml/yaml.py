# coding: utf-8

'''
YAML Format Reader / Writer
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import yaml

from veredi.logger import log
from veredi.data.config.registry import register
from veredi.data import exceptions

from . import function
from . import document

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'format', 'yaml')
class YamlFormat:
    _EXTENSION = 'yaml'

    # https://pyyaml.org/wiki/PyYAMLDocumentation

    # TODO: ABC's abstract method
    def ext(self):
        return self._EXTENSION

    def load(self, file_obj, error_context):
        '''Load and decodes data from a single data file.

        Raises:
          - exceptions.LoadError
            - wrapped yaml.YAMLDecodeError
          Maybes:
            - Other yaml/file errors?
        '''

        # §-TODO-§ [2020-05-06]: Read type and version, verify them?

        data = None
        try:
            data = yaml.safe_load(file_obj)
        except yaml.YAMLError as error:
            log.error('YAML failed while loading the file. {} {}',
                      error.__class__.__qualname__,
                      error_context)
            data = None
            raise exceptions.LoadError("Error loading yaml file:",
                                       error,
                                       error_context) from error
        return data

    def load_all(self, file_obj, error_context):
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
            data = yaml.safe_load_all(file_obj)
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
