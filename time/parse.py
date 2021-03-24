# coding: utf-8

'''
Parse strings into timestamps or durations, and possibly vice versa.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, NewType

import re
from decimal       import Decimal

import datetime as py_dt


from veredi.base   import numbers
from veredi.logs   import log


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


DateTypes = NewType('DateTypes', Union[py_dt.date, py_dt.datetime])
'''
The date/time related types we know about/can deal with.
'''


DateTypesTuple = (py_dt.date, py_dt.datetime)
'''
The date/time related types we know about/can deal with.
'''


DurationInputTypes = NewType(
    'DurationInputTypes',
    Union[str, py_dt.timedelta, numbers.NumberTypes])
'''
The time-duration related types we know about/can deal with.
'''


# -----------------------------------------------------------------------------
# Parsing
# -----------------------------------------------------------------------------

def duration(duration_str: str) -> Optional[py_dt.timedelta]:
    '''
    Parse a human-friendly time duration `duration_str` into a
    py_dt.timedelta.

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

    return py_dt.timedelta(**duration_params)


def date(date_str: str) -> Optional[py_dt.date]:
    '''
    Tries to parse a str into a date object. Returns None if it cannot.
    '''
    timestamp = None
    try:
        timestamp = py_dt.date.fromisoformat(date_str)
    except ValueError:
        timestamp = None
    return timestamp


def datetime(datetime_str: str) -> Optional[py_dt.datetime]:
    '''
    Tries to parse a str into a datetime object. Returns None if it cannot.
    '''
    timestamp = None
    try:
        timestamp = py_dt.datetime.fromisoformat(datetime_str)
    except ValueError:
        timestamp = None
    return timestamp


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def is_duration(check: Any) -> bool:
    '''
    Returns True if `check` is a type usable for durations:
      - py_dt.timedelta
      - numbers.NumberTypesTuple
      - Something `duration()` can parse.
    '''
    if isinstance(check, py_dt.timedelta):
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

    if isinstance(input, py_dt.timedelta):
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

    if isinstance(input, py_dt.timedelta):
        # Get the input as fractional seconds (already a float)...
        return input.total_seconds()

    # Else just try to cast.
    return float(input)


# -----------------------------------------------------------------------------
# Serialization
# -----------------------------------------------------------------------------

def serialize_claim(input: Any) -> bool:
    '''
    Return True if the input is a time and we can 'serialize' it to a str.
    '''
    # Others? py_dt.timedelta?
    return isinstance(input, DateTypesTuple)


def serialize(input: DateTypes) -> str:
    '''
    'Serialize' input by making sure it's a string.
    '''
    return input.isoformat()


def deserialize_claim(input: Any) -> bool:
    '''
    Return True if the input is a date, datetime, etc and we can 'deserialize'
    it to... probably just itself, but something.
    '''
    # Others? py_dt.timedelta?
    return isinstance(input, DateTypesTuple)


def deserialize(input: Any) -> Optional[DateTypes]:
    '''
    'Deserialize' a date type to... just itself.

    Returns None if not a DateTypes.
    '''
    if deserialize_claim(input):
        return input
    return None
