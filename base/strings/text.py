# coding: utf-8

'''
String helper functions?
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, Iterable


from .. import numbers


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


# -----------------------------------------------------------------------------
# Singular/Plural
# -----------------------------------------------------------------------------

def plural(pluralize:     Union[bool, numbers.NumberTypes, Iterable, None],
           word_singular: str,
           suffix_plural: Optional[str] = 's',
           word_plural:   Optional[str] = None) -> str:
    '''
    Given `pluralize`, try to determine if the word/input should be singular
    or plural.

    `pluralize` is interpreted as follows:
      - bool:
        - True: return plural
        - False: return singular
      - Iterable:
        - length of 1: return singular
        - otherwise: return plurar
      - NumberTypes:
        - equal (or nearly equal) to 1: singular
        - otherwise: plural
      - None:
        - plural? Interpreting as 'False' bool right now, basically.

    If it should be singular, returns `word_singular`.

    If it should be plural, prefers to return `word_plural` if provided.
    Otherwise, returns `word_singular` + `suffix_plural`.
    '''

    # ------------------------------
    # First, figure out how to use `pluralize`.
    # ------------------------------
    plural = False

    # Bool/None: Use bool value.
    if pluralize in (None, True, False):
        plural = bool(pluralize)

    # Number type?
    elif isinstance(pluralize, numbers.NumberTypesTuple):
        # Could tweak tolerance in equalish by providing `relative_tolerance`
        # or `absolute_tolerance`. Try default to start with.
        plural = numbers.equalish(1.0, pluralize)

    # Iterable?
    else:
        try:
            plural = (len(pluralize) != 1)
        except TypeError:
            plural = False

    # ------------------------------
    # Create plural or singular.
    # ------------------------------
    if plural:
        if word_plural:
            return word_plural

        # Alright, build the plural ourself.
        word = word_singular + suffix_plural
        return word

    return word_singular
