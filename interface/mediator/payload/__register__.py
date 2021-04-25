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
from veredi.logs import log
from .base       import Validity, BasePayload
from .bare       import BarePayload
from .logging    import LogField, LogReply, LogPayload


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

codec.register_enum(Validity,
                    dotted='veredi.interface.mediator.payload.validity',
                    name_encode='valid',
                    enum_encode_type=codec.enum.FlagEncodeValue)

codec.register_enum(LogField,
                    dotted='veredi.interface.mediator.payload.log.field',
                    name_encode='field',
                    enum_encode_type=codec.enum.EnumEncodeName)

codec.register_enum(log.Level,
                    dotted='veredi.logs.log.level',
                    name_encode='log.level',
                    enum_encode_type=codec.enum.EnumEncodeName)

codec.register_enum(log.Group,
                    dotted='veredi.logs.log.group',
                    name_encode='log.group',
                    enum_encode_type=codec.enum.EnumEncodeName)

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
