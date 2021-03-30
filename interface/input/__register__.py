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


# ----------------------------------------------------------------------------
# Imports: Registration
# ----------------------------------------------------------------------------

from .identity import InputId

from .system   import InputSystem
from .command  import commander
from .history  import history


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

codec.register(InputId)

config.register(InputSystem)
config.register(commander.Commander)
config.register(history.Historian)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
