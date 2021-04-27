# coding: utf-8

'''
Message payload base class. For payloads that are a bit more involved than
just a string, dict, etc.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Mapping)
if TYPE_CHECKING:
    from veredi.data.codec import Codec

import enum

from veredi.logs            import log
from veredi.data.codec      import (Encodable,
                                    EncodedSimple,
                                    EncodedComplex)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

@enum.unique
class Validity(enum.Enum):
    '''
    Validity of field so we can tell "actually 'None'" from
    "'None' because I don't want to say", for example.
    '''
    INVALID    = enum.auto()
    '''
    A Bad, Invalid value that should not be accepted.
    '''

    NO_COMMENT = enum.auto()
    '''
    Value provider purposefully refused to supply a valid value.

    E.g. a user wants privacy and turns off all logging/metrics while a metrics
    request is on the wire.
    '''

    VALID      = enum.auto()
    '''
    A good value.
    '''


# -----------------------------------------------------------------------------
# Payload Basics
# -----------------------------------------------------------------------------

class BasePayload(Encodable):
    '''
    Base class for message payloads. Simple payloads (like a string, list,
    dict...) should use BarePayload. Complex payloads should create/use a
    specific payload class.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Define instance vars with type hinting, docstrs, etc.
        '''

        self._data: Optional[Any] = None
        '''
        The actual payload itself. Sub-classes will need to define what type it
        actually is...
        '''

        self._valid: 'Validity' = Validity.INVALID
        '''
        Validity of self.value. An enum so we can tell "don't want to say"
        apart from "error - could not say".
        '''

    def __init__(self,
                 data:            Any,
                 valid:           'Validity',
                 skip_validation: bool = False) -> None:
        self._define_vars()

        # ---
        # Set Our Value
        # ---
        self._data = data
        self._valid = valid

        # ---
        # Check Value's Validity?
        # ---
        if not skip_validation:
            self._validate()

    def _validate(self) -> None:
        '''
        Subclasses can change up validation here if desired.
        Base class just checks value of self.valid.
        '''
        # If we have a Validity and it is not INVALID, we are valid.
        if (isinstance(self.valid, Validity)
                and self.valid != Validity.INVALID):
            return

        # Otherwise raise an error.
        else:
            raise ValueError(
                f"{self.klass} is invalid.",
                self.valid, self.value)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def valid(self) -> 'Validity':
        '''
        Property for getting validity.
        '''
        return self._valid

    @valid.setter
    def valid(self, value: 'Validity') -> None:
        '''
        Property for setting validity.
        '''
        self._valid = value

    @property
    def data(self) -> Any:
        '''
        Property for getting the raw data. Creates a dict if `self._data`
        is None.
        '''
        if self._data is None:
            self._data = {}
        return self._data

    @data.setter
    def data(self, value: Any) -> None:
        '''
        Property for setting the raw data.
        Calls self._validate() after setting.
        '''
        self._data = value
        self._validate()

    # -------------------------------------------------------------------------
    # Encodable API (Codec Support)
    # -------------------------------------------------------------------------

    def encode_simple(self, codec: 'Codec') -> EncodedSimple:
        '''
        Don't support simple for Payloads.
        '''
        msg = (f"{self.klass} doesn't support encoding to a "
               "simple string.")
        raise NotImplementedError(msg)

    @classmethod
    def decode_simple(klass: 'BasePayload',
                      data:  EncodedSimple,
                      codec: 'Codec') -> 'BasePayload':
        '''
        Don't support simple by default.
        '''
        msg = (f"{klass.__name__} doesn't support decoding from a "
               "simple string.")
        raise NotImplementedError(msg)

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        # self.data is "Any", so... Try to decode it. It may already be
        # decoded - this function should handle those cases.
        data = codec.encode(self._data)

        # Build our representation to return.
        return {
            'valid': codec.encode(self.valid),
            'data': data,
        }

    @classmethod
    def decode_complex(klass: 'BasePayload',
                       data:   EncodedComplex,
                       codec: 'Codec',
                       instance: Optional['BasePayload'] = None
                       ) -> 'BasePayload':
        '''
        Decode ourself from an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        klass.error_for(data, keys=['valid', 'data'])

        # build valid from value saved in encode_complex
        valid = codec.decode(Validity, data['valid'])

        # Our data is of type 'Any', so... try to decode that?
        data = codec.decode(None, data['data'])

        # Make class with decoded data, skip_validation because this exists and
        # we're just decoding it, not creating a new one.
        payload = klass(data, valid,
                        skip_validation=True)
        return payload

    # ------------------------------
    # To String
    # ------------------------------

    def __str__(self):
        return (
            f"{self.klass}: {self.data}, {self.valid}"
        )

    def __repr__(self):
        return (
            f"{self.klass}({self.data}, {self.valid})"
        )
