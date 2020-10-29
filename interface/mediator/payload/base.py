# coding: utf-8

'''
Message payload base class. For payloads that are a bit more involved than
just a string, dict, etc.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, NewType, Mapping, Tuple

from abc import ABC, abstractmethod
import multiprocessing
import multiprocessing.connection
import asyncio
import enum
import contextlib

from veredi.logger               import log
from veredi.data.codec.encodable import Encodable
from veredi.data.exceptions      import EncodableError
from veredi.base.identity        import MonotonicId
from veredi.data.identity        import UserId, UserKey


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
    dict...) do not need to be encapsulated. They can just be encoded/decoded
    with the mediator's codec.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Define instance vars with type hinting, docstrs, etc.
        '''

        self.data: Optional[Any] = None
        '''
        The actual payload itself. Sub-classes will need to define what type it
        actually is...
        '''

        self.valid: 'Validity' = Validity.INVALID
        '''
        Validity of self.value. An enum so we can tell "don't want to say"
        apart from "error - could not say".
        '''

    def __init__(self,
                 data: Any,
                 valid: 'Validity') -> None:
        self._define_vars()

        # ---
        # Set Our Value
        # ---
        self.data = data
        self.valid = valid

        # ---
        # Check Value's Validity
        # ---
        self._validate()

    def _validate(self) -> None:
        '''
        Subclasses can change up validation here if desired.
        Base class just checks value of self.valid.
        '''
        # If we have a Validity and it is not INVALID, we are valid.
        if isinstance(self.valid, Validity) and self.valid != Validity.INVALID:
            return

        # Otherwise raise an error.
        else:
            raise ValueError(
                f"{self.__class__.__name__} is invalid.",
                self.valid, self.value)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def valid(self) -> 'Validity':
        '''
        Property for getting validity.
        '''
        return self.valid

    @valid.setter
    def valid(self, value: 'Validity') -> None:
        '''
        Property for setting validity.
        '''
        self.valid = value

    @property
    def data(self) -> Any:
        '''
        Property for getting the raw data.
        '''
        return self.data

    @valid.setter
    def valid(self, value: Any) -> None:
        '''
        Property for setting the raw data.
        Calls self._validate() after setting.
        '''
        self.data = value
        self._validate()

    # -------------------------------------------------------------------------
    # Encodable API (Codec Support)
    # -------------------------------------------------------------------------

    def encode(self) -> Mapping[str, Union[str, int]]:
        '''
        Returns a representation of our data as a dictionary.
        '''
        log.debug(f"\n\n{self.__class__.__name__}.encode: {self.data}\n\n")

        # Get started with parent class's encoding.
        encoded = super().encode()
        # Updated with our own.
        encoded = self._encode(encoded)

        # log.debug(f"\n\n   done.encode: {encoded}\n\n")
        return encoded

    def _encode(self,
                encoding: Mapping[str, Union[str, int]]
                ) -> Mapping[str, Union[str, int]]:
        '''
        Sub-classes should override this if any extra encoding needs to happen.

        We will just guess at how to encode if we can.
        '''

        if isinstance(self.data, dict):
            return self._encode_map(self.data, encoding)

        else:
            raise NotImplementedError(
                "BasePayload._encode doesn't know how to handle "
                f"'{type(self.data)}'.",
                type(self.data), self.data, self.valid)

    @classmethod
    def decode(klass: 'BasePayload',
               mapping: Mapping[str, Union[str, int]]) -> 'BasePayload':
        '''
        Turns the `mapping` into a payload instance.
        '''
        # log.debug(f"\n\nlogging.decode {type(mapping)}: {mapping}\n\n")

        # Currently don't have any actual required keys/vaules, so just error
        # on claim fail.
        klass.error_for_claim(mapping)

        decoded = klass._decode_map(mapping)
        ret_val = klass(data=decoded)
        # log.debug(f"\n\n   done.decode: {ret_val}\n\n")
        return ret_val

    # ------------------------------
    # To String
    # ------------------------------

    def __str__(self):
        return (
            f"{self.__class__.__name__}: {self.data}, {self.valid}"
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}({self.data}, {self.valid})"
        )
