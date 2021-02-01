# coding: utf-8

'''
Types and Constants for paths.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, NewType, Iterable

import pathlib


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

PathType = NewType('PathType', Union[str, pathlib.Path])
'''Path or string type.'''

PathTypeTuple = (str, pathlib.Path)
'''Tuple for 'PathType' checking.'''

PathsInput = NewType('PathsInput',
                     Union[PathType, Iterable[PathType]])
'''One or more PathType inputs.'''
