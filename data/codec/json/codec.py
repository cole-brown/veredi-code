# coding: utf-8

'''
Reader/Loader & Writer/Dumper of JSON Format.
Aka JSON Codec.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import json

from veredi.logger import log
from veredi.data.config.registry import register
from veredi.data import exceptions

from ..base import BaseCodec


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'codec', 'json')
class JsonCodec(BaseCodec):
    _NAME = 'json'

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

    # §-TODO-§ [2020-05-22]: load_all
