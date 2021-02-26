# coding: utf-8

'''
Message payload class for bears.

Er. For bare payloads. E.g. dictionaries to be transmitted as-is.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, NewType, Mapping

import enum


from veredi.logs                 import log
from veredi.base.enum            import EnumEncodeNameMixin
from veredi.data.codec.encodable import (Encodable,
                                         EncodedComplex,
                                         EncodedSimple)

from .base                       import BasePayload, Validity


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Do Not Feed the Bares
# -----------------------------------------------------------------------------

class BarePayload(BasePayload,
                  dotted='veredi.interface.mediator.payload.bare'):
    '''
    Payload class for a bare payload.

    Bit odd, but helps to make it explicitly an encodable.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # ------------------------------
    # Constants: Encodable
    # ------------------------------

    _ENCODE_NAME: str = 'payload.bare'
    '''Name for this class when encoding/decoding.'''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 data: Mapping[str, Union[str, int]] = None) -> None:
        # Ignore validity always... (valid property is hardcoded too).
        super().__init__(data, Validity.VALID)

    # -------------------------------------------------------------------------
    # Data Structure
    # -------------------------------------------------------------------------

    @property
    def valid(self) -> 'Validity':
        '''
        Property for getting validity.
        '''
        return Validity.VALID

    @valid.setter
    def valid(self, value: 'Validity') -> None:
        '''
        Disallow setting.
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.valid() setter "
                                  "property is not implemented.")

    @property
    def data(self) -> Any:
        '''
        Property for getting the actual bare payload data.
        Just returns `self._data` as-is.
        '''
        return self._data

    @data.setter
    def data(self, value: Any) -> None:
        '''
        Property for setting the raw data.
        Does /not/ self._validate() after setting, unlike BasePayload.
        '''
        self._data = value

    # -------------------------------------------------------------------------
    # Encodable API (Codec Support)
    # -------------------------------------------------------------------------

    @classmethod
    def _type_field(klass: 'BarePayload') -> str:
        return klass._ENCODE_NAME

    # Simple:  BasePayload's are good.

    def _encode_complex(self) -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        # Our data is either a value (str, numbers) or a collection (dict,
        # list). So to 'encode', we just... return the data. Message should be
        # encoding us with registry.
        #
        # Don't care about `valid` at all.
        return {
            'data': self.data,
        }

    @classmethod
    def _decode_complex(klass: 'BasePayload',
                        data:  EncodedComplex) -> 'BasePayload':
        '''
        Decode ourself from an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        klass.error_for(data, keys=['data'])

        # Whatever the data['data'] is, we will use it as-is for our data.
        return klass(data['data'])

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self):
        return (
            f"{self.__class__.__name__}: {self.data}"
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(data={self.data})"
        )
