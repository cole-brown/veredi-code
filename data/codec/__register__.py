# coding: utf-8

'''
Module for auto-magical registration shenanigans.

This will be found and imported by run.registry in order to have whatever
Registries, Registrars, and Registrees this provides available at run-time.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.logs.log import Group

# ------------------------------
# Registries & Registrars
# ------------------------------
from .registry import (registrar,
                       register,
                       ignore,
                       EncodableRegistry)


# ------------------------------
# Registrees
# ------------------------------
from .enum     import (FlagEncodeValueMixin,
                       FlagEncodeNameMixin,
                       EnumEncodeNameMixin)


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

registrar([Group.START_UP, Group.REGISTRATION], None)

ignore(FlagEncodeValueMixin)
ignore(FlagEncodeNameMixin)
ignore(EnumEncodeNameMixin)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
