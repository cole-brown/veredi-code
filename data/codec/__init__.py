# coding: utf-8

'''
The Codec is for allowing Veredi objects to know how to decode/encode
themselves in preparation for serialization or after deserialization.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Protocol, Any


from veredi.logs import log
from veredi.base.strings import label


# -----------------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------------

from .const     import (EncodeNull, EncodeAsIs,
                        EncodedComplex, EncodedSimple, EncodedEither,
                        Encoding)
from .codec     import Codec
from .encodable import Encodable
from .registry  import EncodableRegistry


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # ------------------------------
    # File-Local
    # ------------------------------
    'register',


    # ------------------------------
    # Types
    # ------------------------------
    'Codec',

    'EncodeNull',
    'EncodeAsIs',
    'EncodedComplex',
    'EncodedSimple',
    'EncodedEither',
    'Encoding',

    'Encodable',
    'EncodableRegistry',


    # # ------------------------------
    # # Protocol / Interface
    # # ------------------------------
    # 'Encoder',
    # 'Decoder',
]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def register(klass:  'Encodable',
             dotted: Optional[label.LabelInput] = None) -> None:
    '''
    Register the `klass` with the `dotted` string to our registry.
    '''
    dotted_str = label.normalize(dotted)
    log.registration(dotted,
                     f"Encodable: Checking '{dotted_str}' "
                     f"for registration of '{klass.__name__}'...")

    # ---
    # Sanity
    # ---
    if not dotted:
        # No dotted string is an error.
        msg = ("Encodable sub-classes must be registered with a `dotted` "
               f"parameter. Got: '{dotted_str}'")
        error = ValueError(msg, klass, dotted)
        log.registration(dotted, msg)
        raise log.exception(error, msg)

    elif dotted == klass._DO_NOT_REGISTER:
        # A 'do not register' dotted string probably means a base class is
        # encodable but shouldn't exist on its own; subclasses should
        # register themselves.
        log.registration(dotted,
                         f"Ignoring '{klass}'. "
                         "It is marked as 'do not register'.")
        return

    # ---
    # Register
    # ---
    log.registration(dotted,
                     f"Encodable: Registering '{dotted_str}' "
                     f"to '{klass.__name__}'...")

    dotted_args = label.regularize(dotted)
    EncodableRegistry.register(klass, *dotted_args)

    log.registration(dotted,
                     f"Encodable: Registered '{dotted_str}' "
                     f"to '{klass.__name__}'.")


# -----------------------------------------------------------------------------
# Protocols for Type Hinting
# -----------------------------------------------------------------------------


# Don't need these right now...
# TODO: Keep?


# class Encoder(Protocol):
#     '''
#     Encoder supports encoding.
#     '''
#
#     def encode(self,
#                <get an up-to-date params list from Codec.encode()>,
#                ) -> EncodedEither:
#         '''
#         <get an up-to-date docstr from Codec.encode()>
#         '''
#         ...
#
#
# class Decoder(Protocol):
#     '''
#     Decoder supports decoding.
#     '''
#
#     @classmethod
#     def decode(klass:    'Encodable',
#                data:     EncodedComplex,
#                <get an up-to-date params list from Codec.decode()>,
#                ) -> Optional['Encodable']:
#         '''
#         <get an up-to-date docstr from Codec.decode()>
#         '''
#         ...
