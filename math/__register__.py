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

from .parser import NodeType, MathTree
from .event  import MathOutputEvent

from .system import MathSystem


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

# ------------------------------
# EncodableRegistry
# ------------------------------

codec.register_enum(NodeType,
                    dotted='veredi.math.parser.type',
                    name_encode='node.type',
                    enum_encode_type=codec.enum.FlagEncodeName)

codec.register(MathOutputEvent)

codec.ignore(MathTree)


# ------------------------------
# ConfigRegistry
# ------------------------------
config.register(MathSystem)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
