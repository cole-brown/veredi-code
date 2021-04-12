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
from .action  import Action
from .subject import Subject
from .context import Context
from .object  import Object


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

codec.register_enum(Action,
                    dotted='veredi.security.abac.attributes.action',
                    name_encode='attributes.action',
                    enum_encode_type=codec.enum.FlagEncodeName)

codec.register_enum(Subject,
                    dotted='veredi.security.abac.attributes.subject',
                    name_encode='attributes.subject',
                    enum_encode_type=codec.enum.FlagEncodeName)

codec.register_enum(Context,
                    dotted='veredi.security.abac.attributes.context',
                    name_encode='attributes.context',
                    enum_encode_type=codec.enum.FlagEncodeName)

codec.register_enum(Object,
                    dotted='veredi.security.abac.attributes.object',
                    name_encode='attributes.object',
                    enum_encode_type=codec.enum.FlagEncodeName)

# ignore(Here3)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
