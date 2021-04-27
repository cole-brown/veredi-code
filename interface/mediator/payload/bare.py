# coding: utf-8

'''
Message payload class for bears.

Er. For bare payloads. E.g. dictionaries to be transmitted as-is.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, NewType, Mapping, Iterable

import enum


from veredi.logs         import log
from veredi.base.strings import labeler
from veredi.base         import numbers
from veredi.data.codec   import (Codec,
                                 Encodable,
                                 EncodedComplex,
                                 EncodedSimple)

from .base               import BasePayload, Validity


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

BareDataType = NewType('BareDataType',
                       Union[str, numbers.NumberTypes])
'''
Data types allow in BarePayload.
'''

BarePayloadType = NewType('BarePayloadType',
                          Union[BareDataType,
                                Iterable[BareDataType],
                                Mapping[BareDataType, BareDataType]])
'''
Full type of data allow in BarePayloads:
  - Just a BareDataType.
  - List of BareDataTypes.
  - Map of BareDataTypes to BareDataTypes.

Basically: numbers, strings, or lists/dicts of numbers/strings.
'''


# -----------------------------------------------------------------------------
# Do Not Feed the Bares
# -----------------------------------------------------------------------------

class BarePayload(BasePayload,
                  name_dotted='veredi.interface.mediator.payload.bare',
                  name_string='payload.bare'):
    '''
    Payload class for a bare payload.

    Bit odd, but helps to make it explicitly an encodable.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 data: BarePayloadType = None) -> None:
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
        raise NotImplementedError(f"{self.klass}.valid() setter "
                                  "property is not implemented.")

    @property
    def data(self) -> BarePayloadType:
        '''
        Property for getting the actual bare payload data.
        Just returns `self._data` as-is.
        '''
        return self._data

    @data.setter
    def data(self, value: BarePayloadType) -> None:
        '''
        Property for setting the raw data.
        Does /not/ self._validate() after setting, unlike BasePayload.
        '''
        self._data = value

    # -------------------------------------------------------------------------
    # Encodable API (Codec Support)
    # -------------------------------------------------------------------------

    # Simple:  BasePayload's are good.

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
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
    def decode_complex(klass: 'BarePayload',
                       data:   EncodedComplex,
                       codec: 'Codec',
                       instance: Optional['BarePayload'] = None
                       ) -> 'BarePayload':
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
            f"{self.klass}: {self.data}"
        )

    def __repr__(self):
        return (
            f"{self.klass}(data={self.data})"
        )
