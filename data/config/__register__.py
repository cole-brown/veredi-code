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

# Registering/ignoring some base/simple things here so we don't have a inverted
# sort of dependency. Base should be... basic stuff. Configuration and
# registration is outside its paygrade, really.

# ------------------------------
# Registrees
# ------------------------------
from veredi.base.paths    import safing
from veredi.base.identity import MonotonicId, SerializableId


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

config.register(safing.to_human_readable,
                'veredi.paths.sanitize.human')
config.register(safing.to_hashed,
                'veredi.paths.sanitize.hashed.sha256')

codec.register(MonotonicId)
codec.register(SerializableId)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
