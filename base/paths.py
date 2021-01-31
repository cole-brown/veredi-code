# coding: utf-8

'''
Path/pathlib Helpers
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, NewType, Iterable
from types import StringTypes

# import pathlib

# For letting users of this module have access to Path type without importing
# pathlib themselves.
from pathlib import Path


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

PathType = NewType('PathType', Union[str, Path])
'''Path or string type.'''

PathTypeTuple = (str, Path)
'''Tuple for 'PathType' checking.'''

PathsInput = NewType('PathsInput',
                     Union[PathType, Iterable[PathType]])
'''One or more PathType inputs.'''


# -------------------------------Just Functions.-------------------------------
# --                            Paths In General                             --
# -----------------------------------------------------------------------------

def cast(*input: PathType) -> Path:
    '''
    Ensure that `str_or_path` is a pathlib.Path.
    '''
    return Path(*input)


def to_str_list(input: PathsInput) -> str:
    '''
    Convert a path or iterable of paths to a list of strings.
    '''
    output = []
    if isinstance(input, (StringTypes, PathTypeTuple)):
        output.append(_path_to_str(input))

    else:
        for path in input:
            output.append(_path_to_str(path))

    return output


def to_str(input: PathsInput) -> str:
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

def _path_to_str(input: PathType) -> str:
    '''
    Convert a single PathType to a string.
    '''
    return str(input)
