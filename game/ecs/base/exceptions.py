# coding: utf-8

'''
All your Exceptions are belong to these classes.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python

# Our Stuff
from veredi.base.exceptions import VerediError


# ------------------------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------------------------

class ComponentError(VerediError):
    def __init__(self, message, cause, context):
        '''With context data.'''
        super().__init__(message, cause, context)

class EntityError(VerediError):
    def __init__(self, message, cause, context):
        '''With context data.'''
        super().__init__(message, cause, context)
