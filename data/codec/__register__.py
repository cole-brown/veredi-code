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
from .registry import EncodableRegistry


# ------------------------------
# Registrees
# ------------------------------


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # ------------------------------
    # File-Local
    # ------------------------------

    # ------------------------------
    # Registries & Registrars
    # ------------------------------
    'EncodableRegistry',

    # ------------------------------
    # Registrees
    # ------------------------------
]
