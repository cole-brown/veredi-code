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

from .event    import Recipient, OutputEvent
from .envelope import Address, Envelope

from .system   import OutputSystem


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

codec.register(Recipient)
codec.register(Address)
codec.register(Envelope)

codec.ignore(OutputEvent)

config.register(OutputSystem)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
