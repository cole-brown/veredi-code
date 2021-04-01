# coding: utf-8

'''
Module for auto-magical registration shenanigans.

This will be found and imported by run.registry in order to have whatever
Registries and Registrars this provides available at run-time.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.logs.log import Group


# ------------------------------
# Registries & Registrars
# ------------------------------
from . import codec, config


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

codec.create([Group.START_UP, Group.REGISTRATION], None)
config.create([Group.START_UP, Group.REGISTRATION], None)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
