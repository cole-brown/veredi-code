# coding: utf-8

'''
Helpers for names.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (Optional, Union, Any, NewType,
                    Mapping, Iterable, List, Tuple)
from ..null import Nullable, Null

import pathlib
import re

# CANNOT IMPORT LOG. Circular import.
# from veredi.logs import log

from .. import lists


# -----------------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------------

LabelInput  = NewType('LabelInput', Union[str, List[str]])
'''
A label of some type - use normalize() to get a Dotted or regularize() to get
a DotList.

Examples:
  - "jeff.rules.x.y.z"
  - ["jeff", "rules", "x", "y", "z"]
  - ["jeff.rules", "x", "y.z"]
'''

LabelLaxInput = NewType('LabelLaxInput',
                        Union[str, pathlib.Path, Null, None])
'''
Label functions that want to be ULTRA MAX helpful may take/handle all these
types of input.
'''

LabelLaxInputIter = NewType('LabelLaxInputIter', Iterable[LabelLaxInput])
'''
Iterable of LabelLaxInput types.
'''

DotStr = NewType('DotStr', str)
'''
A dotted label as a string.

E.g.: "jeff.rules.x.y.z"
'''

DotList = NewType('DotList', List[str])
'''
A dotted label as a list of strings, split on the dots.

E.g.: ["jeff", "rules", "x", "y", "z"]
'''


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

DOTTED_NAME = 'dotted'
'''
Try to call your attribute/property 'dotted', for consistency.

If you use 'register', your class will get a 'dotted' property for free.
'''

_VEREDI_PREFIX = 'veredi.'
'''
The expected start for all dotted strings under the official veredi banner.
'''


# ------------------------------
# Regexes
# ------------------------------

_DIR_OR_DOT_RX = re.compile(r'[./\\]')
'''
Split on a dot or either slash.

Could instead try determining if it's a path, then using pathlib or `_split()`
if this doesn't pan out.
'''

_PATH_PYTHON_TRIM_RX = re.compile(r'(?P<name>.*)(?P<extension>[.]py\w?)')
'''
Looks for a ".py", ".pyc", ".pyw", etc extension to strip off.
'''

_PATH_PYTHON_TRIM_NAME = 'name'
_PATH_PYTHON_TRIM_EXT = 'extension'


# -----------------------------------------------------------------------------
# Predicates
# -----------------------------------------------------------------------------

def is_veredi(dotted: DotStr) -> bool:
    '''
    Returns true if the `dotted` string is formatted correctly to be considered
    an 'official' veredi dotted string ('official' meaning does it starts with
    the 'veredi' namespace).
    '''
    return dotted.startswith(_VEREDI_PREFIX)


def is_dotstr(input: Any) -> bool:
    '''
    Returns true if the `dotted` string is formatted correctly to be considered
    a Veredi Label Dotted String (aka label.DotStr).
    '''
    # Must exist.
    if not input:
        return False
    # Must be a string.
    if not isinstance(input, str):
        return False
    # Must have at least one dot.
    if '.' not in input:
        return False

    return True


def is_labelinput(*input: Any) -> bool:
    '''
    Returns True if all of `input` is valid as LabelInput.
    '''
    if not input:
        return False

    # `input` parameter is *args, so it is definitely an iterable.
    # So check each one, and return result ASAP.
    for entry in input:
        if not is_labelinput_entry(entry):
            return False
    return True


def is_labelinput_entry(input: Any) -> bool:
    '''
    Returns True if this one `input` is valid as LabelInput.
    '''
    # ------------------------------
    # LabelInput is: Union[str, List[str]]
    #   1) Check for str.
    #   2) Check for list of strs.
    # ------------------------------

    # ---
    # 1) String?
    # ---
    if isinstance(input, str):
        return True

    # ---
    # 2) Iterable of Strings?
    # ---
    # Be strict and require only list, or be Pythonic and just iterate?
    try:
        for entry in input:
            if not isinstance(entry, str):
                return False
    except TypeError:
        # Not iterable so not a LabelInput.
        return False

    # ---
    # 3) Success.
    # ---
    # Didn't return early with a failure, so we must have succeeded.
    return True

# -----------------------------------------------------------------------------
# Label Helper Functions
# -----------------------------------------------------------------------------

def _join(*names: str) -> DotStr:
    '''
    Turns iterable of `names` strings into one dotted string.

    !! NOTE: A bit fragile - use normalize() for a robust `_join()` !!

    e.g.:
      dotted(    'veredi', 'jeff', 'system') -> 'veredi.jeff.system'
      dotted(   ('veredi', 'jeff'))          -> __!!!__ERROR__!!!__
      normalize( 'veredi', 'jeff', 'system') -> 'veredi.jeff.system'
      normalize(('veredi', 'jeff'))          -> 'veredi.jeff.system'
    '''
    return '.'.join(names)


def _split(dotted: str) -> DotList:
    '''
    Splits `names` strings up on '.' and retuns a list of the split strings.

    !! NOTE: A bit fragile - use regularize() for a robust `_split()` !!

    e.g.:
      'veredi.jeff.system' -> ['veredi', 'jeff', 'system']
    '''
    return dotted.split('.')

def _split_path_or_dot(input: LabelLaxInput) -> DotList:
    '''
    Splits `names` strings up on '.' and retuns a list of the split strings.

    !! NOTE: A bit fragile - use from_path() and/or regularlize() for a robust
    !!   version!

    e.g.:
      'veredi.jeff.system' -> ['veredi', 'jeff', 'system']
      'C:\\veredi\\jeff\\system' -> ['veredi', 'jeff', 'system']
    Mixed too:
      '/veredi/jeff.system' -> ['veredi', 'jeff', 'system']
    '''
    if not input:
        return ()

    # Get rid of ".py" if it's easy-ish.
    if isinstance(input, pathlib.Path):
        parts = list(input.parts)
        parts[-1] = _scrub_for_path(parts[-1])
        return parts
    parts = _DIR_OR_DOT_RX.split(str(input))
    return parts


def regularize(*dotted: LabelInput, empty_ok: bool = False) -> DotList:
    '''
    ??? -> [str, str, ...]

    Normalize input `dotted` strings and/or lists of strings into one list of
    (non-dotted) strings.
    Examples:
      regularize('jeff.rules', 'system', 'etc')
        -> ['jeff', 'rules', 'system', 'etc']
      regularize('jeff.rules.system.etc')
        -> ['jeff', 'rules', 'system', 'etc']

    If `empty_ok` is True, will return `[]` for empty `dotted` input.
    '''
    if empty_ok and not is_labelinput(*dotted):
        return []
    # Flatten (and split) our input string(s) into one list of one string each.
    return lists.flatten(*dotted,
                         function=_split)


def normalize(*dotted: LabelInput, empty_ok: bool = False) -> Optional[DotStr]:
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

    If `empty_ok` is True, will return `None` for empty `dotted` input.
    '''
    if empty_ok and not is_labelinput(*dotted):
        return None

    # Easy - regularize and join it.
    return _join(*regularize(dotted, empty_ok=empty_ok))


def to_path(*args: LabelInput) -> Nullable[pathlib.Path]:
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


def _scrub_for_path(input: str) -> str:
    '''
    Check `input` for path things to scrub out. Mainly '.py?' will get trimmed
    off.
    '''
    match = _PATH_PYTHON_TRIM_RX.match(input)
    result = input
    if match:
        result = match.group(_PATH_PYTHON_TRIM_NAME)
    return result


def from_path(path:     Union[str, pathlib.Path, Null],
              root_dir: str = 'veredi') -> Optional[DotStr]:
    '''
    Builds a dotted string from the `path`, using `root_dir` name as the
    starting point of the dotted str. If something in the path ends with '.py',
    strip that out.

    Will use the /last/ occurance of `root_dir` as the starting point.

    So '/srv/veredi/veredi/jeff/system.py' becomes (for `root_dir`=='veredi'):
      'veredi.jeff.system'

    Or '/path/to/jeff/veredi-extensions/something/system.py' becomes
    (for `root_dir`=='jeff'):
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
        # Drop '.py' endings.
        dotted_parts.append(_scrub_for_path(part))

        # Done once we hit a 'veredi'.
        if part == 'veredi':
            break

    return _join(*list(reversed(dotted_parts)))


def from_something(*input:   LabelLaxInput,
                   root_str: str = 'veredi') -> Optional[DotStr]:
    '''
    Builds a dotted string from the `input`, using `root_str` name as the
    starting point of the dotted str. If one of the split entries in the dotted
    string ends with '.py', strip that out.

    Will use the /last/ occurance of `root_dir` as the starting point.

    '/srv/veredi/veredi/jeff/system.py' becomes (for `root_str`=='veredi'):
      'veredi.jeff.system'
    'srv.this.at\\veredi/veredi/jeff/system.py' becomes (for `root_str`=='veredi'):
      'veredi.jeff.system'

    Or '/path/to/jeff.py/veredi-extensions/something/system.py' becomes
    (for `root_str`=='jeff' or `roto_str`=='jeff.py'):
      'jeff.veredi-extensions.something.system'

    `file` can be __file__ for some auto-magic-ish-ness.
    '''
    # Flatten (and split) our input string(s) into one list of one string each.
    dot_list = lists.flatten(input,
                             function=_split_path_or_dot)
    # Clean up root too.
    root_str = _scrub_for_path(root_str)
    parts = []  # Output accum.
    for part in dot_list:
        clean = _scrub_for_path(part)
        # No root? Just push everything to the valid parts list.
        if not root_str:
            parts.append(clean)
            continue

        # Else we have a root to worry about.
        if not parts:
            # Searching for root...
            if clean == root_str:
                # Found a possible root - start gathering parts.
                parts.append(clean)

        else:
            # Found a more recent root? Reset and start gathering again.
            if clean == root_str:
                parts.clear()
                parts.append(clean)

            # Else keep adding to current valid parts.
            else:
                parts.append(clean)

    # Now we should have the full output ready. Join into a DotStr for
    # returning.
    output = normalize(*parts)
    return output

def this(find: str,
         milieu: str) -> Tuple[Nullable[DotList], bool]:
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
        return _split(find), found_this

    result = []
    for name in _split(find):
        if name != 'this':
            result.append(name)
            continue

        # Have a 'this'. Replace it.
        found_this = True

        # 1) Replace it with... what?
        these = _split(milieu)

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


def munge_to_short(dotted: DotStr) -> str:
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
    names = _split(dotted)
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


def from_map(mapping:       Union[str, Mapping[str, Any]],
             error_squelch: bool = False) -> Optional[DotStr]:
    '''
    If `mapping` is just a string, depends on what `error_squelch` is set to:
      - True:  Returns None.
      - False: Raises ValueError.

    If `mapping` has a key matching PROPERTY ('dotted'), return that field's
    value.

    Else, return None.
    '''
    if isinstance(mapping, str):
        if error_squelch:
            return None
        msg = ("dotted.from_map() does not support strings - needs a Mapping "
               f"type like dict. Got: {type(mapping)}.")
        error = ValueError(msg, mapping)
        raise error

    # Don't raise an exception; just return None if we can't find it.
    try:
        return mapping.get(DOTTED_NAME, None)
    except (ValueError, AttributeError, KeyError):
        pass

    return None
