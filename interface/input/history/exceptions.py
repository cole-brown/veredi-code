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

# ---
# Base
# ---

class HistoryError(VerediError):
    '''
    Base exception type for all errors of historical note.
    '''
    ...


# ---
# Specifics
# ---

class HistoryIdError(HistoryError):
    '''
    Insufficient data for creating an ID from input.
    '''
    ...
