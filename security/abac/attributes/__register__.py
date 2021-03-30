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
from veredi.config.registration import codec


# ------------------------------
# Registrees
# ------------------------------
from .action  import Action
from .subject import Subject
from .context import Context
from .object  import Object


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

codec.register(Action)
codec.register(Subject)
codec.register(Context)
codec.register(Object)

# ignore(Here3)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
