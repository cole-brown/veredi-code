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

from .game import D20RulesGame


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

config.register(D20RulesGame)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
