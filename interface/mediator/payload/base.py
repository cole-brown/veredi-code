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

from veredi.logger          import log
from veredi.data.codec.base import Encodable
from veredi.data.exceptions import EncodableError
from veredi.base.identity   import MonotonicId
from veredi.data.identity   import UserId, UserKey


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

    # TODO [2020-08-18]: Move _encode_map, _encode_key, _encode_value to
    # Encodable?
    def _encode_map(self,
                    encode_from: Mapping,
                    encode_to:   Optional[Mapping] = None,
                    # TODO: Better return type - NewType it so it's usable all
                    # over for encodables?
                    ) -> Mapping[str, Union[str, int, float, None]]:
        '''
        If `encode_to` is supplied, use that. Else create an empty `encode_to`
        dictionary. Get values in `encode_from` dict, encode them, and put them
        in `encode_to` under an encoded key.

        Returns `encode_to` instance (either the new one we created or the
        existing updated one).
        '''
        if encode_to is None:
            encode_to = {}

        # log.debug(f"\n\nlogging._encode_map: {encode_from}\n\n")
        for key, value in encode_from.items():
            field = self._encode_key(key)
            node = self._encode_value(value)
            encode_to[field] = node

        # log.debug(f"\n\n   done._encode_map: {encode_to}\n\n")
        return encode_to

    def _encode_key(self, key: Any) -> str:
        '''
        Encode a dict key.
        '''
        # log.debug(f"\n\nlogging._encode_key: {key}\n\n")
        field = None
        if isinstance(key, str):
            field = key
        elif isinstance(key, enum.Enum):
            field = key.value
        else:
            field = str(key)

        # log.debug(f"\n\n   done._encode_key: {field}\n\n")
        return field

    def _encode_value(self, value: Any) -> str:
        '''
        Encode a dict value.

        If value is:
          - dict or encodable: Step in to them for encoding.
          - enum: Use the enum's value.

        Else assume it is already encoded.
        '''
        # log.debug(f"\n\nlogging._encode_value: {value}\n\n")
        node = None
        if isinstance(value, dict):
            node = self._encode_map(value)

        elif isinstance(value, Encodable):
            # Encode via its function.
            node = value.encode()

        elif isinstance(value, (enum.Enum, enum.IntEnum)):
            node = value.value

        else:
            node = value

        # log.debug(f"\n\n   done._encode_value: {node}\n\n")
        return node

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

    # TODO [2020-08-18]: Move _decode_map, _decode_key, _decode_value to
    # Encodable?
    @classmethod
    def _decode_map(klass: 'BasePayload',
                    mapping: Mapping
                    # TODO: Better return type - NewType it so it's usable all
                    # over for encodables?
                    ) -> Mapping[str, Any]:
        '''
        Decode a mapping.
        '''
        # log.debug(f"\n\nlogging._decode_map {type(mapping)}: {mapping}\n\n")

        # ---
        # Decode the Base Level
        # ---
        decoded = {}
        for key, value in mapping.items():
            field = klass._decode_key(key)
            node = klass._decode_value(value)
            decoded[field] = node

        # ---
        # Is It Anything Special?
        # ---
        # Sub-classes could check in about this spot in their override...
        # if AnythingSpecial.claim(decoded):
        #     decoded = AnythingSpecial.decode(decoded)

        # log.debug(f"\n\n   done._decode_map: {decoded}\n\n")
        return decoded

    @classmethod
    def _decode_key(klass: 'BasePayload', key: Any) -> str:
        '''
        Decode a mapping's key.

        BasePayload is pretty stupid. string is only supported type.
        '''
        # log.debug(f"\n\nlogging._decode_key {type(key)}: {key}\n\n")
        field = None
        if isinstance(key, str):
            field = key
        else:
            raise EncodableError(f"Don't know how to decode key: {key}",
                                 None)

        # log.debug(f"\n\n   done._decode_key: {field}\n\n")
        return field

    @classmethod
    def _decode_value(klass: 'BasePayload', value: Any) -> str:
        '''
        Decode a mapping's value.

        BasePayload is pretty stupid. dict and Encodable are further decoded -
        everything else is just assumed to be decoded alreday.
        '''

        # log.debug(f"\n\nlogging._decode_value {type(value)}: {value}\n\n")
        node = None
        if isinstance(value, dict):
            node = klass._decode_map(value)

        elif isinstance(value, Encodable):
            # Decode via its function.
            node = value.decode()

        else:
            # Simple value like int, str? Hopefully?
            node = value

        # log.debug(f"\n\n   done._decode_value: {node}\n\n")
        return node

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
