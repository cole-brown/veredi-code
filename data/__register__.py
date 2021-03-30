# coding: utf-8

'''
Module for auto-magical registration shenanigans.

This will be found and imported by run.registry in order to have whatever
Registries, Registrars, and Registrees this provides available at run-time.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------


# ------------------------------
# Registries & Registrars
# ------------------------------
from .registration import codec


# ------------------------------
# Registrees
# ------------------------------
from .identity import UserId, UserKey


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

codec.register(UserId)
codec.register(UserKey)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
