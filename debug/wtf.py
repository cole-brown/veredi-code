# coding: utf-8

'''
Hi; sorry you're having a bad day.

Swear all you want.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
from typing import Any


import inspect


# -----------------------------------------------------------------------------
# Constants & Variables
# -----------------------------------------------------------------------------

_FUCKERS_COUNT = {}
'''
Functions we don't fuckin' like today, and a count of how many times you've
called `count()` on the fucks.
'''


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def count(*curse_words: Any) -> None:
    '''
    Prints out a fucking number.
    '''
    # Get the fuckin' function name.
    fucker = inspect.stack()[1][3]

    # Increment our curse counter.
    fuck_yous = _FUCKERS_COUNT.setdefault(fucker, 0)
    fuck_yous += 1
    _FUCKERS_COUNT[fucker] = fuck_yous

    # Curse.
    if curse_words:
        print(f"wtf?!::{fucker} #{fuck_yous:04d}:", *curse_words)
    else:
        print(f"wtf?!::{fucker} #{fuck_yous:04d}")
