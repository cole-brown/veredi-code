# coding: utf-8

'''
Helpers for names.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import List
from .null import Nullable, Null

import pathlib


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

PROPERTY = 'dotted'
'''
Try to call your attribute/property 'dotted', for consistency.

If you use 'register', your class will get a 'dotted' property for free.
'''

ATTRIBUTE_PRIVATE = '_DOTTED'
'''
Try to call your attribute/property 'dotted', for consistency.

If you use 'register', your class will get a 'dotted' property for free.
'''


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def join(*names: str) -> str:
    '''
    Turns iterable of `names` strings into one dotted string.

    e.g.:
      dotted('veredi', 'jeff', 'system') -> 'veredi.jeff.system'
    '''
    return '.'.join(names)


def split(dotted: str) -> List[str]:
    '''
    Turns iterable of `names` strings into one dotted string.

    e.g.:
      'veredi.jeff.system' -> ['veredi', 'jeff', 'system']
    '''
    return dotted.split('.')


def path(*args: str) -> Nullable[pathlib.Path]:
    '''
    Takes either iterable of strings or dotted string.
    Converts to iterable of strings if needed via dotted().
    Returns a path of the args.

    e.g.:
      'veredi.jeff.system'         -> pathlib.Path('veredi/jeff/system')
      ['veredi', 'jeff', 'system'] -> pathlib.Path('veredi/jeff/system')
    '''
    if not args:
        return Null()

    if len(args) == 1:
        args = split(args[0])

    return pathlib.Path(*args)


def this(find: str, milieu: str) -> Nullable[List[str]]:
    '''
    Looks for 'this' in `find` string, then uses `milieu` to replace it.
    E.g.:
      this('this.score',
           'strength.modifier')
        -> 'strength.score'

    Basically, 'this' means (currently) 'go down a level'. From, in that case,
    'strength.modifier' (the milieu in which we found the 'this') down to
    'strength'. Which we can then use to replace the 'this' in 'this.score' and
    return 'strength.score'.

    ...I would have called it 'context' but that's already in heavy use, so
    'milieu'.
      "The physical or social setting in which something occurs
      or develops."
    Close enough?

    Returns split name list.
    '''
    if not find:
        return Null()
    if not milieu:
        # Just return what we got, but I guess split to obey return value?
        return split(find)

    result = []
    for name in split(find):
        if name != 'this':
            result.append(name)
            continue

        # Have a 'this'. Replace it.
        # 1) Replace it with... what?
        these = split(milieu)

        # 2) Split replacement, and use all but leaf name, if possible.
        if len(these) > 1:
            these = these[:-1]

        # 3) Append replacement to result instead of 'this'.
        result.extend(these)

    return result
