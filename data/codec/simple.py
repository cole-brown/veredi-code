# coding: utf-8

'''
An Encodable which is just a pass-through.

Used for data which is not encoded (e.g. an integer), but needs an Encodable
type for some reason internally...
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, Optional, Any
if TYPE_CHECKING:
    from .codec      import Codec


from veredi.logs import log

from .const      import EncodedComplex, EncodedSimple, Encoding
from .encodable  import Encodable


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Encodable Interface / Mixin
# -----------------------------------------------------------------------------

class EncodableShim(Encodable):
    '''
    A class for indicating that some data should just be left as-is for
    encode/decode.
    '''

    # -------------------------------------------------------------------------
    # Connstants
    # -------------------------------------------------------------------------

    _ENCODE_NAME: str = 'shim'
    '''Name for this class when encoding/decoding.'''

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    @classmethod
    def encoding(klass: 'EncodableShim') -> Encoding:
        '''
        Returns True if this class only encodes/decodes to EncodedSimple.
        '''
        return Encoding.SIMPLE

    @classmethod
    def type_field(klass: 'EncodableShim') -> str:
        return 'shim'

    def encode_simple(self, codec: 'Codec') -> Any:
        '''
        We are just a shim for simple data - we should not be called to encode
        it.
        '''
        msg = (f"{self.__class__.__name__} is a type helper for simple, as-is "
               "data. It should not be encoded itself.")
        raise TypeError(msg)

    @classmethod
    def decode_simple(klass: 'EncodableShim',
                      data:  EncodedSimple,
                      codec: 'Codec') -> 'EncodableShim':
        '''
        We are just a shim for simple data - we should not be called to decode
        it.
        Don't support simple by default.
        '''
        msg = (f"{klass.__name__} is a type helper for simple, as-is "
               "data. It should not be encoded itself.")
        raise TypeError(msg)

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        Only simple.
        '''
        raise NotImplementedError(f"{self.__class__.__name__} cannot shim "
                                  "for complex data.")

    @classmethod
    def decode_complex(klass: 'EncodableShim',
                       data:  EncodedComplex,
                       codec: 'Codec',
                       instance: Optional['EncodableShim'] = None
                       ) -> 'EncodableShim':
        '''
        Only simple.
        '''
        raise NotImplementedError(f"{klass.__name__} cannot shim "
                                  "for complex data.")
