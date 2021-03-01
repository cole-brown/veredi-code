# coding: utf-8

'''
Custom YAML Formatter for Logging.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional

import logging


# ------------------------------
# YAML Formatted Logging
# ------------------------------

# from . import record
# from . import factory
from .format import FormatYaml


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # ------------------------------
    # File-Local
    # ------------------------------
    'init',

    # ------------------------------
    # Types & Consts
    # ------------------------------

    # ------------------------------
    # Classes
    # ------------------------------
    'FormatYaml',
]


# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def init(fmt:      str  = None,
         datefmt:  str  = None,
         validate: bool = True) -> FormatYaml:
    '''
    Initialize a YAML formatter and return it.

    Recommend leaving all params defaulted.
    '''
    return FormatYaml(fmt=fmt,
                      datefmt=datefmt,
                      validate=validate)
