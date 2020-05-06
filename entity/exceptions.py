# coding: utf-8

'''
All your Exceptions are belong to these classes.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python

# Our Stuff
from veredi.bases.exceptions import VerediError

# ------------------------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------------------------

class KeyError(VerediError):
    def __init__(self):
        '''No-args ctor.'''
        pass

    def __init__(self, message, cause, context):
        '''With context data.'''
        super().__init__(message, cause, context)
