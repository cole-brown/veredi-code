# coding: utf-8

'''
Helpers for names.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (Optional, Union, Any, Type, NewType, Callable,
                    Mapping, List, Tuple)
from .null import Nullable, Null

import collections

import pathlib

# CANNOT IMPORT LOG. Circular import.
# from veredi.logger import log

from . import lists


# -----------------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------------

Dotted = NewType('Dotted', str)
'''
A dotted label string.

E.g.: "jeff.rules.x.y.z"
'''

Label  = NewType('Label', Union[str, List[str]])
'''
A label of some type - use normalize() to get a Dotted.

Examples:
  - "jeff.rules.x.y.z"
  - ["jeff", "rules", "x", "y", "z"]
  - ["jeff.rules", "x", "y.z"]
'''


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_DOTTED_NAME = 'dotted'
'''
Try to call your attribute/property 'dotted', for consistency.

If you use 'register', your class will get a 'dotted' property for free.
'''

_VEREDI_PREFIX = 'veredi.'
'''
The expected start for all dotted strings under the official veredi banner.
'''


# -----------------------------------------------------------------------------
# Label Helper Functions
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


def regularize(*dotted: Union[str, List[str]]) -> List[str]:
    '''
    ??? -> [str, str, ...]

    Normalize input `dotted` strings and/or lists of strings into one list of
    (non-dotted) strings.
    Examples:
      regularize('jeff.rules', 'system', 'etc')
        -> ['jeff', 'rules', 'system', 'etc']
      regularize('jeff.rules.system.etc')
        -> ['jeff', 'rules', 'system', 'etc']
    '''
    # Flatten (and split) our input string(s) into one list of one string each.
    return lists.flatten(*dotted,
                         function=split)


def normalize(*dotted: Union[str, List[str]]) -> Union[str, List[str]]:
    '''
    Normalize input `dotted` strings and/or lists of strings into one list of
    strings (or one dotted string if `to_str` is True).

    ??? -> 'str.str.<...>'

    Normalize input `dotted` strings and/or lists of strings into one list of
    (non-dotted) strings.
    Examples:
      normalize('jeff.rules', 'system', 'etc')
        -> 'jeff.rules.system.etc'
      normalize(['jeff', 'rules', 'system', 'etc'])
        -> 'jeff.rules.system.etc'
    '''
    # Easy - regularize and join it.
    return join(*regularize(dotted))


def to_path(*args: Union[str, List[str]]) -> Nullable[pathlib.Path]:
    '''
    Takes `args` (either iterable of strings or dotted string), `regularize()`
    it/them, and returns a pathlib.Path made from them.

    e.g.:
      'veredi.jeff.system'         -> pathlib.Path('veredi/jeff/system')
      ['veredi', 'jeff', 'system'] -> pathlib.Path('veredi/jeff/system')
      ['veredi', 'jeff.system']    -> pathlib.Path('veredi/jeff/system')

    Returns Path or Null()
    '''
    if not args:
        return Null()

    # Regularize the args to split whatever they are into a list of strings,
    # then build a Path to return from that.
    norm = regularize(*args)
    if not norm:
        # Turns out args weren't anything?
        return Null()
    return pathlib.Path(*norm)


def from_path(path:    Union[str, pathlib.Path, Null],
              stop_at: str = 'veredi') -> Optional[str]:
    '''
    Builds a dotted string from the path. If something in the path ends with
    '.py', strip that out.

    Builds dotted output back-to-front, stopping at first `stop_at` string it
    encounters in the path (default: 'veredi').

    So '/srv/veredi/veredi/jeff/system.py' becomes (for default):
      'veredi.jeff.system'

    Or '/path/to/jeff/veredi-extensions/something/system.py' becomes
    (for 'jeff'):
      'jeff.veredi-extensions.something.system'

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


def auto(obj: Any) -> str:
    '''
    Tries its best to automatically create a dotted string from the object
    given. Returns a lowercased dotted string.

    This will likely be the fully qualified module name. e.g.
      from xml.etree.ElementTree import ElementTree
      et = ElementTree()
      print(dotted.auto(et))
        -> 'xml.etree.elementtree'

    If `short` is True, this will try to create a short identifying string.
    '''
    # Try to add object's class name to end if we can.
    name = ''
    try:
        name = '.' + obj.__class__.__name__
    except ValueError:
        try:
            name = '.' + obj.__name__
        except ValueError:
            pass

    # Lowercase and return.
    return (obj.__module__ + name).lower()


def munge_to_short(dotted: str) -> str:
    '''
    Munges `dotted` string down into something short by taking the first letter
    of everything in the dotted path.

    Uses 'v.' instead of just 'v' for shortening 'veredi' in the first
    position.

    Returns lowercased munged string.
    '''
    # ---
    # Sanity
    # ---
    names = split(dotted)
    if not names:
        msg = (f"Cannot munge nothing. Got empty dotted list {names} "
               f"from input '{dotted}'.")
        error = ValueError(msg, dotted, names)
        raise error

    # ---
    # Munging
    # ---

    # 1) "veredi" -> "v."
    #    Check first element. If it's veredi, do our special case and delete it
    #    before proceeding to normal case stuff.
    munged = ''
    if names[0] == 'veredi':
        munged = 'v.'
        names.pop(0)

    # 2) "Xyzzy" -> "X"
    for name in names:
        munged += name[0]

    # 3) Lowercase it.
    return munged.lower()


def from_map(mapping:      Union[str, Mapping[str, Any]],
             squelch_error: bool = False) -> Optional[str]:
    '''
    If `mapping` is just a string, depends on what `squelch_error` is set to:
      - True:  Returns None.
      - False: Raises ValueError.

    If `mapping` has a key matching PROPERTY ('dotted'), return that field's
    value.

    Else, return None.
    '''
    if isinstance(mapping, str):
        if squelch_error:
            return None
        msg = ("dotted.from_map() does not support strings - needs a Mapping "
               f"type like dict. Got: {type(mapping)}.")
        error = ValueError(msg, mapping)
        raise error

    # Don't raise an exception; just return None if we can't find it.
    try:
        return mapping.get(_DOTTED_NAME, None)
    except (ValueError, AttributeError, KeyError):
        pass

    return None
