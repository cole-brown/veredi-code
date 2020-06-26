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


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def dotted(*names: str) -> str:
    '''
    Turns iterable of `names` strings into one dotted string.

    e.g.:
      dotted('veredi', 'input', 'system') -> 'veredi.input.system'
    '''
    return '.'.join(*names)


def split(dotted: str) -> List[str]:
    '''
    Turns iterable of `names` strings into one dotted string.

    e.g.:
      'veredi.input.system' -> ['veredi', 'input', 'system']
    '''
    return dotted.split('.')


def path(*args: str) -> Nullable[pathlib.Path]:
    '''
    Takes either iterable of strings or dotted string.
    Converts to iterable of strings if needed via dotted().
    Returns a path of the args.

    e.g.:
      'veredi.input.system'         -> pathlib.Path('veredi/input/system')
      ['veredi', 'input', 'system'] -> pathlib.Path('veredi/input/system')
    '''
    if not args:
        return Null()

    if len(args) == 1:
        args = split(args[0])

    return pathlib.Path(*args)
