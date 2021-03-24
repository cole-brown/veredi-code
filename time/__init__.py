# coding: utf-8

'''
Helpers for getting a game of Veredi running.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------


from .parse  import (
    # Functions
    duration, is_duration,
    to_decimal, to_float,
    serialize_claim, serialize,
    deserialize_claim, deserialize,

    # Types
    DateTypes,
    DateTypesTuple,
    DurationInputTypes,
)

# Namespaced
from . import machine
from . import timer
from . import parse


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
    # Types
    # ------------------------------
    'DateTypes',
    'DateTypesTuple',
    'DurationInputTypes',

    # ------------------------------
    # Functions
    # ------------------------------
    'duration',
    'is_duration',
    'to_decimal',
    'to_float',
    'serialize_claim',
    'serialize',
    'deserialize_claim',
    'deserialize',

    # ------------------------------
    # Namespaced
    # ------------------------------
    'machine',
    'timer',
    'parse',
]
