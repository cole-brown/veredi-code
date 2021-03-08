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

from .const import EncodedComplex, EncodedSimple, EncodedEither, Encoding

from .encodable import Encodable
from .registry import EncodableRegistry


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
#                encode_in_progress: Optional[EncodedComplex]) -> EncodedEither:
#         '''
#         Encode self as a simple or complex encoding, depending on
#         self.encoding().
#
#         If self.encoding() is SIMPLE, encodes to a string.
#
#         Otherwise:
#           - If `encode_in_progress` is provided, encodes this to a sub-field
#             under self.type_field().
#           - Else encodes this to a dict and provides self.type_field() as the
#             value of self._TYPE_FIELD_NAME.
#         '''
#         ...
#
#     @classmethod
#     def encode_or_none(klass: 'Encodable',
#                        encodable: Optional['Encodable'],
#                        encode_in_progress: Optional[EncodedComplex] = None
#                        ) -> EncodedEither:
#         '''
#         If `encodable` is None or Null, returns None.
#         Otherwise, returns `encodable.encode(encode_in_progress)`.
#
#         The equivalent function for decoding is just `decode()`.
#         '''
#         ...
#
#     def encode_with_registry(self) -> EncodedComplex:
#         '''
#         Creates an output dict with keys: _ENCODABLE_REG_FIELD
#         and _ENCODABLE_PAYLOAD_FIELD.
#
#         Returns the output dict:
#           output[_ENCODABLE_REG_FIELD]: result of `self.dotted()`
#           output[_ENCODABLE_PAYLOAD_FIELD]: result of `self.encode()`
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
#     def decode(klass: 'Encodable',
#                data: EncodedEither) -> Optional['Encodable']:
#         '''
#         Decode simple or complex `data` input, using it to build an
#         instance of this class.
#
#         Return a new `klass` instance.
#         '''
#         ...
#
#     @classmethod
#     def decode_with_registry(klass:    'Encodable',
#                              data:     EncodedComplex,
#                              **kwargs: Any) -> Optional['Encodable']:
#         '''
#         Input `data` must have keys:
#           - Encodable._ENCODABLE_REG_FIELD
#           - Encodable._ENCODABLE_PAYLOAD_FIELD
#         Raises KeyError if not present.
#
#         Takes EncodedComplex `data` input, and uses
#         `Encodable._ENCODABLE_REG_FIELD` key to find registered Encodable to
#         decode `data[Encodable._ENCODABLE_PAYLOAD_FIELD]`.
#
#         Any kwargs supplied (except 'dotted' - will be ignored) are forwarded
#         to EncodableRegistry.decode() (e.g. 'fallback').
#
#         Return a new `klass` instance.
#         '''
#         ...
