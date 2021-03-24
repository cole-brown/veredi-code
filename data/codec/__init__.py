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
from .enum      import (FlagEncodeValueMixin,
                        FlagEncodeNameMixin,
                        EnumEncodeNameMixin)
from .codec     import Codec
from .encodable import Encodable
from .registry  import (EncodableRegistry,
                        register, ignore)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # ------------------------------
    # Functions
    # ------------------------------
    'register',
    'ignore',

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

    'EnumEncodeNameMixin',
    'FlagEncodeNameMixin',
    'FlagEncodeValueMixin',

    # # ------------------------------
    # # Protocol / Interface
    # # ------------------------------
    # 'Encoder',
    # 'Decoder',
]


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
