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
from .event import Recipient, OutputEvent
from .envelope import Address, Envelope


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

register(Recipient)
register(Address)
register(Envelope)

ignore(OutputEvent)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
