# coding: utf-8

'''
All your Exceptions are belong to these classes.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from yaml import YAMLError


# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------

# TODO [2020-08-20]: Use these error in constructor/representer functions.
# TODO [2020-08-20]: Use these error in stuff derived from YAMLObject.

class VerediYamlSerializeError(YAMLError):
    '''
    Error 'inside' YAML during encoding.
    '''
    ...


class VerediYamlDeserializeError(YAMLError):
    '''
    Error 'inside' YAML during decoding.
    '''
    ...
