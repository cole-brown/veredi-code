# coding: utf-8

'''
Module initialization for veredi.data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import enum


from veredi.base import yaml, types

from . import background


# -----------------------------------------------------------------------------
# Enum / YAML Set-Up
# -----------------------------------------------------------------------------

def find_all_enums() -> None:
    '''
    Search for enums in background's classes. Register them with yaml.
    '''
    # Expect any/all enums in background to be logged via yaml format logging.
    # So, we need to find and register them.
    for name in background.__all__:
        klass = background.__dict__[name]
        if not types.is_class(klass):
            continue

        # Some top level classes /are/ enums.
        if issubclass(klass, enum.Enum):
            # Figure out an enum representer for this enum.
            yaml.represent(klass,
                           yaml.enum_representer(klass),
                           __file__)

        # Some top level classes /have/ enums.
        else:
            for _, value in klass.__dict__.items():
                if types.is_class(value) and issubclass(value, enum.Enum):
                    # Figure out an enum representer for this enum.
                    yaml.represent(value,
                                   yaml.enum_representer(value),
                                   __file__)


# -----------------------------------------------------------------------------
# Initialization
# -----------------------------------------------------------------------------

find_all_enums()
