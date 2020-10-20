# coding: utf-8

'''
Helpers for names.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, List, Tuple
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

_VEREDI_PREFIX = 'veredi.'
'''
The expected start for all dotted strings under the official veredi banner.
'''


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def is_veredi(dotted: str) -> bool:
    '''
    Returns true if the `dotted` string is formatted correctly to be considered
    an 'official' veredi dotted string.
    '''
    return dotted.startswith(_VEREDI_PREFIX)


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


def to_path(*args: str) -> Nullable[pathlib.Path]:
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


def from_path(path: Union[str, pathlib.Path, Null]) -> Optional[str]:
    '''
    Builds a dotted string from the path. If something in the path ends with
    '.py', strip that out.

    Builds dotted output back-to-front, stopping at first 'veredi' it
    encounters in the path.

    So '/srv/veredi/veredi/jeff/system.py' becomes:
      'veredi.jeff.system'

    `file` can be __file__ for some auto-magic-ish-ness.
    '''
    if not path:
        return None

    # Make sure we have a full path...
    path = pathlib.Path(path).resolve()
    # Split into the dirs and file...
    path_components = path.parts
    # Process parts in reverse order. We want from the last 'veredi' to the
    # end, since the Docker container has veredi in '/srv/veredi/veredi'.
    dotted_parts = []
    for part in reversed(path_components):
        # Drop '.py' ending.
        if part.endswith('.py'):
            dotted_parts.append(part[:-3])
        else:
            dotted_parts.append(part)
        # Done once we hid a 'veredi'.
        if part == 'veredi':
            break

    return join(*list(reversed(dotted_parts)))


def this(find: str,
         milieu: str) -> Tuple[Nullable[List[Union[str, List[str]]]], bool]:
    '''
    Looks for 'this' in `find` string, then uses `milieu` to replace it. Milieu
    will be split, so if a 'this' was found, you'll get a list of strings
    and/or lists.

    E.g.:
      this('this.score',
           'strength.modifier')
        -> [['strength', 'modifier'], 'score']

    Basically, 'this' means (currently) 'go down a level'. From, in that case,
    'strength.modifier' (the milieu in which we found the 'this') down to
    'strength'. Which we can then use to replace the 'this' in 'this.score' and
    return 'strength.score'.

    ...I would have called it 'context' but that's already in heavy use, so
    'milieu'.
      "The physical or social setting in which something occurs
      or develops."
    Close enough?

    Returns tuple of: (<split name list>, <'this' was found>)
    '''
    found_this = False

    if not find:
        return Null(), found_this
    if not milieu:
        # Just return what we got, but I guess split to obey return value?
        return split(find), found_this

    result = []
    for name in split(find):
        if name != 'this':
            result.append(name)
            continue

        # Have a 'this'. Replace it.
        found_this = True

        # 1) Replace it with... what?
        these = split(milieu)

        # 2) Replace `this` with `these`, let caller figure out what to
        #    reduce down to.
        result.append(these)

        # # 2) Split replacement, and use all but leaf name, if possible.
        # if len(these) > 1:
        #     these = these[:-1]
        #
        # # 3) Append replacement to result instead of 'this'.
        # result.extend(these)

    return result, found_this
