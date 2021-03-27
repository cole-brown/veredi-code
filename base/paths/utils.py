# coding: utf-8

'''
Path/pathlib Helpers
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, Set, Tuple, List
from ..null import NullNoneOr, is_null

# For letting users of this module have access to Path type without importing
# pathlib themselves.
from pathlib import Path
import os
from queue import SimpleQueue
import re


from . import const


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -------------------------------Just Functions.-------------------------------
# --                            Paths In General                             --
# -----------------------------------------------------------------------------

def cast(*input: const.PathType,
         allow_none: bool = False,
         allow_null: bool = False) -> NullNoneOr[Path]:
    '''
    Ensure that `str_or_path` is a pathlib.Path.

    If `allow_none` or `allow_null` are set, will allow those to be passed in
    (as the /full/ `input`) without a TypeError from `pathlib.Path()`. They
    will instead be returned as-is.
    '''
    # Null or None allowances.
    if allow_none:
        # Input must be none itself (don't see how), or...
        if input is None:
            return input
        # Input must be one element: None.
        if len(input) == 1 and input[0] is None:
            return input[0]
    if allow_null:
        # Input must be Null itself (don't see how), or...
        if is_null(input):
            return input
        # Input must be one element: Null.
        if len(input) == 1 and is_null(input[0]):
            return input[0]

    # Try to cast for real.
    # Could raise TypeError.
    return Path(*input)


def walk_filtered(root:        const.PathType,
                  ignore_dirs: Set[re.Pattern]
                  ) -> Tuple[str, List[str], List[str]]:
    '''
    Call os.walk, check each of its generated values, ignore or yield them as
    indicated by `ignore_dirs` set.
    '''
    root = cast(root)
    for path_rel_str, dirs, files in os.walk(root):
        path = root / path_rel_str
        if path == root:
            # Never ignore the root.
            yield (path_rel_str, dirs, files)
            continue

        ignore = False
        for regex in ignore_dirs:
            # Don't use 'match' - need to find ignorable things in the middle
            # of the relative path too.
            if regex.search(path_rel_str):
                # Found a match for ignoring, so... ignore.
                ignore = True
                break

        if ignore:
            continue

        # Not ignored, so yield it back as a result.
        yield (path_rel_str, dirs, files)


# --------------------------------Predicates?----------------------------------
# --                       They work for `None` too!                         --
# -----------------------------------------------------------------------------

def exists(input: NullNoneOr[const.PathType]) -> bool:
    '''
    Returns either input.exists() or False if input is Null/None.
    '''
    path = cast(input, allow_none=True, allow_null=True)
    if not path:
        return False

    return path.exists()


def is_file(input: NullNoneOr[const.PathType]) -> bool:
    '''
    Returns either input.is_file() or False if input  is Null/None.
    '''
    path = cast(input, allow_none=True, allow_null=True)
    if not path:
        return False

    return path.is_file()


def is_dir(input: NullNoneOr[const.PathType]) -> bool:
    '''
    Returns either input.is_dir() or False if input  is Null/None.
    '''
    path = cast(input, allow_none=True, allow_null=True)
    if not path:
        return False

    return path.is_dir()


# ------------------------------Strings & Things-------------------------------
# --                        Paths to Strings, etc...                         --
# -----------------------------------------------------------------------------

def to_str_list(input: const.PathsInput) -> str:
    '''
    Convert a path or iterable of paths to a list of strings.
    '''
    output = []
    if not input:
        # Could skip Falsy inputs, but... I think it's better to not hide the
        # fact that there is one?
        output.append(None)

    elif isinstance(input, const.PathTypeTuple):
        output.append(_path_to_str(input))

    else:
        for path in input:
            if not path:
                # Could skip Falsy inputs, but... I think it's better to not
                # hide the fact that there is one?
                output.append(path)
            else:
                output.append(_path_to_str(path))

    return output


def to_str(input: const.PathsInput) -> str:
    '''
    Convert a path or iterable of paths to a single string.
    '''
    output = to_str_list(input)

    # Return just the one?
    if len(output) == 1:
        return output[0]

    # More than one - format them all into a string.
    output_str = ', '.join(output)
    return f'[{output_str}]'


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _path_to_str(input: const.PathType) -> str:
    '''
    Convert a single PathType to a string.
    '''
    return str(input)


# -----------------------------------------------------------------------------
# Serialization
# -----------------------------------------------------------------------------

def serialize_claim(input: Any) -> bool:
    '''
    Return True if the input is a path and we can 'serialize' it to a str.
    '''
    return isinstance(input, Path)


def serialize(input: Path) -> str:
    '''
    Serialize a path to a string.
    '''
    return str(input)
