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


# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------

class TickError(VerediError):
    '''
    Error ticking?
    '''
    ...


class EventError(VerediError):
    '''
    Some sort of basic eventing error.
    '''
    ...
