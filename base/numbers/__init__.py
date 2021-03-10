# coding: utf-8

'''
Helpers for numbers.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ------------------------------
# Types
# ------------------------------

# Might as well have Python's Decimal here for simpler imports/usage elsewhere.
from decimal import Decimal

from .const import (NumberTypes, NumberTypesTuple,
                    DecimalTypes, DecimalTypesTuple)

# ------------------------------
# Functions
# ------------------------------

from .utils import (to_str, from_str, is_number, equalish,
                    to_decimal, to_float,
                    serialize_claim, serialize, deserialize)


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
    # Types & Consts
    # ------------------------------
    'Decimal',
    'NumberTypes',
    'NumberTypesTuple',
    'DecimalTypes',
    'DecimalTypesTuple',

    # ------------------------------
    # Namespaced
    # ------------------------------

    # ------------------------------
    # Functions
    # ------------------------------
    'to_str',
    'from_str',
    'is_number',
    'equalish',
    'to_decimal',
    'to_float',
    'serialize_claim',
    'serialize',
    'deserialize',
]
