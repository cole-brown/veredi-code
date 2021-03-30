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
from veredi.data.registration import codec


# ------------------------------
# Registrees
# ------------------------------
from .base    import Validity, BasePayload
from .bare    import BarePayload
from .logging import LogField, LogReply, LogPayload


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

codec.register(Validity)
codec.register(LogField)
codec.register(LogReply)
codec.register(BarePayload)
codec.register(LogPayload)

codec.ignore(BasePayload)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
