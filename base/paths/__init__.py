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


# ------------------------------
# For the Registration!
# ------------------------------

# TODO: v://future/registering/2021-02-01T10:34:57-0800 - register different?
from .       import safing


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
    # Namespaced
    # ------------------------------
    'safing',

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
