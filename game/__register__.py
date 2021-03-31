# coding: utf-8

'''
Module for auto-magical registration shenanigans.

This will be found and imported by run.registry in order to have whatever
Registries, Registrars, and Registrees this provides available at run-time.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.data.registration import config


# -----------------------------------------------------------------------------
# Imports: Registration
# -----------------------------------------------------------------------------

from .data.identity.component import IdentityComponent
from .data.identity.manager import IdentityManager
from .data.component import DataComponent
from .data.manager import DataManager
from .time.tick.base import TickBase
from .time.tick.round import TickRounds

# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

config.ignore(TickBase)

config.register(IdentityComponent)
config.register(IdentityManager)
config.register(DataComponent)
config.register(DataManager)
config.register(TickRounds)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
