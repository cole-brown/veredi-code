# coding: utf-8

'''
YAML Format Reader / Writer
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import yaml


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class YamlFormat:
    _EXTENSION = "yaml"

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
        data = None
        try:
            data = yaml.safe_load(file_obj)
        except yaml.YAMLError as error:
            data = None
            raise exceptions.LoadError(f"Error loading yaml file: {path}",
                                       error,
                                       error_context) from error
        return data
