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
from veredi.data.codec import register, ignore


# ------------------------------
# Registrees
# ------------------------------
from .zest_tree import MockNode


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

# Should be registered if unit-testing, ignored if not.
register(MockNode, unit_test_only=True)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
