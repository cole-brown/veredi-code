# coding: utf-8

'''
Parse strings into timestamps or durations, and possibly vice versa.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any

import re
from decimal       import Decimal

from datetime      import timedelta


from veredi.base   import numbers
from veredi.logger import log


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_TIME_DURATION_FLAGS = re.IGNORECASE
'''
Don't care about case in time durations.
'''

_TIME_DURATION_REGEX_STR = (
    r'^'

    # ---
    # (Optional) Hours
    # ---
    # A number plus: h, hr, hrs, hour, hours...
    r'((?P<hours>\d+?)\s?h(?:ou)?r?s?)?'

    r'(,?\s*)?'

    # ---
    # (Optional) Minutes
    # ---
    # A number plus: m, min, mins, minute, minutes...
    r'((?P<minutes>\d+?)\s?m(?:in|ins|inute|inutes)?)?'

    r'(,?\s*)?'
    # ---
    # (Optional) Seconds
    # ---
    # A number plus: s, sec, secs, second, seconds...
    r'((?P<seconds>\d+?)\s?s(?:ec|ecs|econd|econds)?)?'

    r'$')
'''
Regex for parsing human time duration strings.
'''

_TIME_DURATION_REGEX = re.compile(_TIME_DURATION_REGEX_STR,
                                  _TIME_DURATION_FLAGS)
'''
Regex for parsing durations.
'''


# -----------------------------------------------------------------------------
# Parsing
# -----------------------------------------------------------------------------

def duration(duration_str: str) -> Optional[timedelta]:
    '''
    Parse a human-friendly time duration `duration_str` into a timedelta.

    '5 seconds'
    '1 hour 5 seconds'
    '1h5s'
    etc.
    '''
    if not duration_str or not isinstance(duration_str, str):
        return None
    parts = _TIME_DURATION_REGEX.match(duration_str)
    if not parts:
        return None

    parts = parts.groupdict()
    duration_params = {}
    for (name, param) in parts.items():
        if param:
            duration_params[name] = int(param)

    return timedelta(**duration_params)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def is_duration(check: Any) -> bool:
    '''
    Returns True if `check` is a type usable for durations:
      - timedelta
      - numbers.NumberTypesTuple
      - Something `duration()` can parse.
    '''
    if isinstance(check, timedelta):
        return True
    elif isinstance(check, numbers.NumberTypesTuple):
        return True
    elif isinstance(check, str):
        try:
            duration(check)
            return True
        except:
            return False

    # What even is it?
    log.warning(f"time.parse.is_duration(): Unknown type {type} for: {check}")
    return False


def to_decimal(input: Any) -> Decimal:
    '''
    Converts the input to a Decimal of seconds and returns it.
    '''
    if isinstance(input, str):
        input = duration(input)

    if isinstance(input, timedelta):
        # Get the input as fractional seconds...
        return numbers.to_decimal(input.total_seconds())

    # Else just try to cast.
    return numbers.to_decimal(input)


def to_float(input: Any) -> float:
    '''
    Converts the input to a float of seconds and returns it.
    '''
    if isinstance(input, str):
        input = duration(input)

    if isinstance(input, timedelta):
        # Get the input as fractional seconds (already a float)...
        return input.total_seconds()

    # Else just try to cast.
    return float(input)
