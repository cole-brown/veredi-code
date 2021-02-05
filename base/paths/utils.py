# coding: utf-8

'''
Path/pathlib Helpers
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from ..null import NullNoneOr, is_null

# For letting users of this module have access to Path type without importing
# pathlib themselves.
from pathlib import Path


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
