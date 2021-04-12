# coding: utf-8

'''
Helper functions for dealing with numbers.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, NewType

import math
import decimal
from decimal import Decimal


# Cannot import log - base must be usable by log.
# from veredi.logs import log

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


_DEFAULT_CLOSENESS_TOLERANCE_REL = 1e-5
'''Default (relative) tolerance for `closeish()`'''



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


def equalish(a: NumberTypes,
             b: NumberTypes,
             relative_tolerance: Union[float, Decimal, None] = None,
             absolute_tolerance: Union[float, Decimal, None] = None) -> bool:
    '''
    Returns true if `a` and `b` are "close enough" to equal.

    If both `a` and `b` are ints, this is "==".

    For floats and Decimals, this is `math.isclose()`.
      - In this case, it will use `relative_tolerance` and/or
        `absolute_tolerance` if provided, or use a default value.
    '''
    if isinstance(a, int) and isinstance(b, int):
        return a == b

    # If both are None, use our default.
    if relative_tolerance is None and absolute_tolerance is None:
        relative_tolerance = _DEFAULT_CLOSENESS_TOLERANCE_REL

    # These are the default values to `math.isclose()`. It doesn't take kindly
    # to being passed None, so reset to these if we have a default param.
    #  rel_tol=1e-09
    #  abs_tol=0.0
    #  https://docs.python.org/3/library/math.html#math.isclose
    if relative_tolerance is None:
        relative_tolerance = 1e-09
    if absolute_tolerance is None:
        absolute_tolerance = 0.0

    return math.isclose(a, b,
                        rel_tol=relative_tolerance,
                        abs_tol=absolute_tolerance)


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
    raise error


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


def serialize(input: DecimalTypes) -> Union[str, float, int]:
    '''
    Returns a string (if decimal), float, or int of the input.
    '''
    if isinstance(input, Decimal):
        return str(input)
    return input


def deserialize(input: Any) -> Optional[NumberTypes]:
    '''
    Tries to parse input into a number type. Returns number or none.

    Any inputs that are not float/int are parsed through Decimal and returned
    as Decimal.

    If it cannot be parsed into a number type, returns None.
    '''
    if isinstance(input, (float, int)):
        return input

    try:
        parsed = Decimal(input)
        return parsed
    except decimal.InvalidOperation:
        # Failed to parse into a decimal, so it's not anything decimal knows
        # about.
        pass

    return None
