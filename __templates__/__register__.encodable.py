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
# from .here  import Thing1
# from .there import Thing2, Ignore1


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

# register(Thing1)
# register(Thing1.SubThing)
# register(Thing2)

# ignore(Ignore1)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
