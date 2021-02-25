# coding: utf-8

'''
Constants for dealing with numbers.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, NewType

from decimal import Decimal


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# ------------------------------
# Number Types
# ------------------------------

NumberTypes = NewType('NumberTypes', Union[int, float, Decimal])
NumberTypesTuple = (int, float, Decimal)

DecimalTypes = NewType('DecimalTypes', Union[Decimal, int, float, str])
DecimalTypesTuple = (int, float, Decimal, str)
