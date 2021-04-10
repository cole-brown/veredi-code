# coding: utf-8

'''
Custom YAML Formatter for Logging.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional

import logging
import yaml as py_yaml

from veredi.base import yaml
from ...         import const as const_l

# ------------------------------
# YAML Formatted Logging
# ------------------------------

from . import record
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
# Functions
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


# -----------------------------------------------------------------------------
# Module Initialization
# -----------------------------------------------------------------------------

# We have the record tag, but for now just say to deserialize it as a
# dictionary.
yaml.construct(record.LogRecordYaml.yaml_tag(),
               py_yaml.SafeLoader.construct_mapping,
               __file__)

# Let YAML know how we want our log enums serialized. Use an enum value
# that is the correct type (e.g. SuccessType - don't use IGNORE).
yaml.represent(const_l.Group,
               yaml.enum_representer(const_l.Group),
               __file__)
yaml.represent(const_l.SuccessType,
               # Use to-string to get the SuccessType formatting.
               yaml.enum_to_string_representer,
               __file__)
