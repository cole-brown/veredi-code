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
from .enum     import (FlagEncodeValueMixin,
                       FlagEncodeNameMixin,
                       EnumEncodeNameMixin)

from .codec    import Codec


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

codec.ignore(FlagEncodeValueMixin)
codec.ignore(FlagEncodeNameMixin)
codec.ignore(EnumEncodeNameMixin)


config.register(Codec)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
