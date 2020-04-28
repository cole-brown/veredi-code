# coding: utf-8

'''
All your Exceptions are belong to these classes.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python

# Our Stuff
from bases.exceptions import VerediError

# ------------------------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------------------------

class LoadError(VerediError):
    def __init__(self):
        '''No-args ctor.'''
        pass

    def __init__(self, message, cause, user):
        '''With user context data.'''
        context = { 'user-load': user }
        super().__init__(message, cause, context)
