# coding: utf-8

'''
Constants for Inputs, Commands, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import enum


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Input Type / Language
# -----------------------------------------------------------------------------

@enum.unique
class InputLanguage(enum.Enum):
    '''
    All input should be parsed by something that understands this type of text.
    '''

    INVALID = 0
    '''Do not use this. It is invalid.'''

    NONE = enum.auto()
    '''
    Input has no arguments - is just a command.
    '''

    MATH = enum.auto()
    '''
    Input is a math expression to be parsed/evaluated as a MathTree.

    e.g. "/roll $sneakiness + 4"
    '''

    TEXT = enum.auto()
    '''Input is just text.

    e.g. "/w gm My chararcter wants to back-stab him in the face."
    '''
