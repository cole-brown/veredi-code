# coding: utf-8

'''
JSON Format reader/writer.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
import json

# Framework

# Our Stuff
from veredi.data.config.registry import register


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'format', 'json')
class JsonFormat:
    _EXTENSION = 'json'

    # TODO: ABC's abstract method
    def ext(self):
        return self._EXTENSION

    def load(self, file_obj, error_context):
        '''Load and decodes data from a single data file.

        Raises:
          - exceptions.LoadError
            - wrapped json.JSONDecodeError
          Maybes:
            - Other json/file errors?
        '''
        data = None
        try:
            data = json.load(file_obj)
        except json.JSONDecodeError as error:
            data = None
            raise exceptions.LoadError(f"Error loading json file: {path}",
                                       error,
                                       error_context) from error
        return data
