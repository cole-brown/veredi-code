# coding: utf-8

'''
Base class for Reader/Loader & Writer/Dumper of ___ Format.
Aka ___ Codec.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.data import exceptions

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# Subclasses, register like this:
# @register('veredi', 'codec', 'CodecSubclass')
class BaseCodec:
    # This should be lowercase and short. Probably like the filename extension.
    # E.g.: 'yaml', 'json'
    _NAME = None

    # https://pyyaml.org/wiki/PyYAMLDocumentation

    def name(self):
        return self._NAME

    def context(self):
        return {
            'name' : self.name(),
        }

    def load(self, stream, error_context):
        '''Load and decodes a single document from the data stream.

        Raises:
          - exceptions.LoadError
            - wrapping a library error?
        '''
        raise NotImplementedError

    def load_all(self, stream, error_context):
        '''Load and decodes all documents from the data stream.

        Raises:
          - exceptions.LoadError
            - wrapping a library error?
        '''
        raise NotImplementedError
