# coding: utf-8

'''
Helper functions for dealing with numbers.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, Any, NewType

import decimal
from decimal import Decimal


from veredi import log

from .const import (NumberTypes, NumberTypesTuple,
                    DecimalTypes, DecimalTypesTuple)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# ------------------------------
# Decimal Stuff
# ------------------------------

_DEFAULT_ROUNDING = Decimal(10) ** -6
'''
Default to rounding Decimals and floats to this many decimal places.
'''

_DECIMAL_CONTEXT = decimal.ExtendedContext.copy()
'''
Use ExtendedContext for decimal operations for more forgiveness and less
erroring...

We'll get a copy of it for our own use.
'''


# -----------------------------------------------------------------------------
# Numbers in General
# -----------------------------------------------------------------------------

def to_str(number: NumberTypes) -> str:
    '''
    Converts a NumberTypes instance into a string.
    '''
    # Convert float to decimal for easier rounding and such.
    if isinstance(number, float):
        with decimal.localcontext(ctx=_DECIMAL_CONTEXT):
            number = Decimal(number).quantize(_DEFAULT_ROUNDING)

    # int or decimal -> str
    return str(number)


def from_str(string: str) -> NumberTypes:
    '''
    Converts a string into either an int or a Decimal.
    '''
    number = to_decimal(string)

    # Try to make it an int...
    with decimal.localcontext(ctx=_DECIMAL_CONTEXT) as ctx:
        int_val = number.to_intergal_exact(context=ctx)
        if decimal.Inexact not in ctx.flags:
            # Only return int_val if it was an exact conversion.
            return int_val

    return number


def is_number(input: Any) -> bool:
    '''
    Checks type of input. Returns
    '''
    return isinstance(input, NumberTypesTuple)


# -----------------------------------------------------------------------------
# Decimals
# -----------------------------------------------------------------------------

def to_decimal(input: DecimalTypes) -> Decimal:
    '''
    Converts the input to a Decimal and returns it.
    '''
    with decimal.localcontext(ctx=_DECIMAL_CONTEXT):
        number = Decimal(input).quantize(_DEFAULT_ROUNDING)
        return number

    msg = f"Could not convert input to Decimal: {type(input)} '{input}'"
    error = ValueError(msg, input)
    raise log.exception(error, msg)


# -----------------------------------------------------------------------------
# Floats
# -----------------------------------------------------------------------------

def to_float(input: DecimalTypes) -> float:
    '''
    Converts the input to a Float and returns it.
    '''
    return float(input)


# -----------------------------------------------------------------------------
# Serialization
# -----------------------------------------------------------------------------

def serialize_claim(input: Any) -> bool:
    '''
    Return True if the input is a number and we can 'serialize' it.
    '''
    return is_number(input)
