# coding: utf-8

'''
Path/pathlib Helpers
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, NewType


# import pathlib

# For letting users of this module have access to Path type without importing
# pathlib themselves.
from pathlib import Path


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

PathType = NewType('PathType', Union[str, Path])


# -------------------------------Just Functions.-------------------------------
# --                            Paths In General                             --
# -----------------------------------------------------------------------------

def cast(*input: PathType) -> Path:
    '''
    Ensure that `str_or_path` is a pathlib.Path.
    '''
    return Path(*input)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
