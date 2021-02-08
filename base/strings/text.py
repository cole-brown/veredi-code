# coding: utf-8

'''
String helper functions?
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def normalize(input: Any) -> str:
    '''
    Converts `input` to a string (via `str()`), does some normalization things
    (lowercases string, trims...), and returns it.
    '''
    string = str(input)
    normalize = string.strip()
    normalize = normalize.lower()
    return normalize


# -----------------------------------------------------------------------------
# Serialization
# -----------------------------------------------------------------------------

def serialize_claim(input: Any) -> bool:
    '''
    Return True if the input is a string and we can 'serialize' it.
    '''
    return isinstance(input, str)
