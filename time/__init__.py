# coding: utf-8

'''
Helpers for getting a game of Veredi running.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------


# Functions
from .parse  import duration, is_duration, to_decimal, to_float

# Namespaced
from . import machine
from . import timer


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # ------------------------------
    # File-Local
    # ------------------------------

    # ------------------------------
    # Functions
    # ------------------------------
    'duration',
    'is_duration',
    'to_decimal',
    'to_float',

    # ------------------------------
    # Namespaced
    # ------------------------------
    'machine',
    'timer',
]
