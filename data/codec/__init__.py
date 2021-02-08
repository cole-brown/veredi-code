# coding: utf-8

'''
The Codec is for allowing Veredi objects to know how to decode/encode
themselves in preparation for serialization or after deserialization.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Protocol, Any)
if TYPE_CHECKING:
    from .encodable import Encodable


# -----------------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------------

from .const import EncodedComplex, EncodedSimple, EncodedEither


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
#         self._encode_simple_only().
#
#         If self._encode_simple_only(), encodes to a string..
#
#         If not self._encode_simple_only():
#           - If `encode_in_progress` is provided, encodes this to a sub-field
#             under self._type_field().
#           - Else encodes this to a dict and provides self._type_field() as the
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


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # ------------------------------
    # Types
    # ------------------------------
    'EncodedComplex',
    'EncodedSimple',
    'EncodedEither',

    # # ------------------------------
    # # Protocol / Interface
    # # ------------------------------
    # 'Encoder',
    # 'Decoder',
]
