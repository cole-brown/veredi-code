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

# Registering/ignoring some base/simple things here so we don't have a inverted
# sort of dependency. Base should be... basic stuff. Configuration and
# registration is outside its paygrade, really.

# ------------------------------
# Registrees
# ------------------------------

from .json.serdes import JsonSerdes
from .yaml.serdes import YamlSerdes


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

config.register(JsonSerdes)
config.register(YamlSerdes)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
