# coding: utf-8

'''
Module for auto-magical registration shenanigans.

This will be found and imported by run.registry in order to have whatever
Registries, Registrars, and Registrees this provides available at run-time.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.data.registration import codec, config


# -----------------------------------------------------------------------------
# Imports: Registration
# -----------------------------------------------------------------------------
from .identity import ComponentId, EntityId, SystemId

from .system import System


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

codec.register(ComponentId)
codec.register(EntityId)
codec.register(SystemId)

config.ignore(System)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
