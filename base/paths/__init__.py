# coding: utf-8

'''
Helpers for paths.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ------------------------------
# Types
# ------------------------------

# Might as well have Python's type here for simpler imports/usage elsewhere.
from pathlib import Path

from .const  import PathType, PathTypeTuple, PathsInput


# ------------------------------
# Functions
# ------------------------------

from .utils  import (cast, exists,
                     is_file, is_dir,
                     to_str_list, to_str,
                     serialize_claim, serialize)


# NOTE: Do NOT import safing! We need to keep the paths module usable by
# logging... safing uses `register()` which uses logging.


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # ------------------------------
    # File-Local
    # ------------------------------

    # ------------------------------
    # Types & Consts
    # ------------------------------
    'Path',
    'PathType',
    'PathTypeTuple',
    'PathsInput',

    # ------------------------------
    # Functions
    # ------------------------------
    'cast',
    'exists',
    'is_file',
    'is_dir',
    'to_str_list',
    'to_str',
    'serialize_claim',
    'serialize',
]
