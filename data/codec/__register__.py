# coding: utf-8

'''
Module for auto-magical registration shenanigans.

This will be found and imported by run.registry in order to have whatever
Registries, Registrars, and Registrees this provides available at run-time.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.data.registration import config, codec


# -----------------------------------------------------------------------------
# Imports: Registration
# -----------------------------------------------------------------------------

# ------------------------------
# Registrees
# ------------------------------
from .enum     import (EnumWrap,
                       FlagEncodeValue,
                       FlagEncodeName,
                       EnumEncodeName)

from .codec    import Codec


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

codec.ignore(EnumWrap)
codec.ignore(FlagEncodeValue)
codec.ignore(FlagEncodeName)
codec.ignore(EnumEncodeName)


config.register(Codec)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
