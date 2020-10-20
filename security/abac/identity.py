# coding: utf-8

'''
Identity Class for the Attribute-Based Access Control.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Type, Any, Mapping

import uuid
import re

from veredi.logger        import log
from veredi.base.identity import SerializableId
import veredi.time.machine


# -----------------------------------------------------------------------------
# PolicyId
# -----------------------------------------------------------------------------

class PolicyIdGenerator:
    '''
    Class that generates serializable UUIDs.
    '''

    def __init__(self,
                 id_class: Type['PolicyId']) -> None:
        self._id_class = id_class

    def next(self, policy: str) -> 'PolicyId':
        seed = veredi.time.machine.unique()
        next_id = self._id_class(seed, policy)
        return next_id


class PolicyId(SerializableId):
    '''
    Serializable PolicyId class.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # ------------------------------
    # Static UUIDs
    # ------------------------------

    _UUID_NAMESPACE = uuid.UUID('5aac710d-8f35-5a25-9425-df41c4a9d214')
    '''
    The 'namespace' for our UUIDs will be static so we can
    reproducably/reliably generate a UUID. Generate by:
      uuid.uuid5(uuid.UUID(int=0), 'veredi.security.abac.identity.PolicyId')
    '''

    # ------------------------------
    # Static/Class UUIDs
    # ------------------------------

    _INVALID_VALUE = None
    '''
    Invalid value for this class is 'None'.
    '''

    _INVALID = None
    '''
    An instance of an InputId with 'None' as its value.
    '''

    # ------------------------------
    # Misc
    # ------------------------------

    _ENCODE_FIELD_NAME = 'abac.pid'
    '''Short abbreviation for PolicyId.'''

    _ENCODE_FORMAT = (
        '{type_str}'
        ':'
        '{uuid_str}'
    )

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    @classmethod
    def _init_invalid_(klass: Type['PolicyId']) -> None:
        '''
        Creates our invalid instance that can be gotten from read-only class
        property INVALID.
        '''
        if not klass._INVALID:
            # Make our invalid singleton instance.
            klass._INVALID = klass(klass._INVALID_VALUE, klass._INVALID_VALUE)

    def __init__(self, seed: str, name: str,
                 decoding:      bool          = False,
                 decoded_value: Optional[int] = None) -> None:
        '''
        Initialize our ID value. ID is based on:
          current time string, name string, and _UUID_NAMESPACE.

        If `decoding`, just use `decode_value'.
        '''
        # log.debug(f"PolicyId.__!!INIT!!__: seed: {seed}, name: {name}, "
        #           f"decoding: {decoding}, "
        #           f"dec_val: {decoded_value}")

        # Decoding into a valid PolicyId?
        if (decoding                                  # Decode mode is a go.
                and not seed and not name             # Normal mode is a no.
                and isinstance(decoded_value, int)):  # Something decode.
            self._value = uuid.UUID(int=decoded_value)
            # log.debug("PolicyId.__init__: decoded to: "
            #           f"{self._value}, {str(self)}")

            # Don't forget to return now. >.<
            return

        # Constructing _INVALID instance?
        if not seed or not name:
            self._value = self._INVALID_VALUE
            return

        # Generate a valid PolicyId.
        self._value = uuid.uuid5(self._UUID_NAMESPACE, seed + name)

    # -------------------------------------------------------------------------
    # Properties / Getters
    # -------------------------------------------------------------------------

    # We get this from our metaclass (InvalidProvider):
    # @property
    # @classmethod
    # def INVALID(klass: Type['PolicyId']) -> 'PolicyId':
    #     '''
    #     Returns a constant value which is considered invalid by whatever
    #     provides these PolicyIds.
    #     '''
    #     return klass._INVALID

    # -------------------------------------------------------------------------
    # Encodable API (Codec Support)
    # -------------------------------------------------------------------------

    def encode(self) -> Mapping[str, Any]:
        '''
        We only encode/decode to simple str.
        '''
        # TODO: let encode be redirected to 'encode a mapping'
        # or 'encode a str'.
        raise NotImplementedError

    @classmethod
    def decode(klass: 'PolicyId',
               mapping: Mapping[str, int]) -> 'PolicyId':
        '''
        We only encode/decode to simple str.
        '''
        # TODO: let decode be redirected to 'decode a mapping'
        # or 'decode a str'.
        raise NotImplementedError

    def encode_str(self) -> str:
        '''
        Returns a string suitable for decode_str().
        '''
        return self._ENCODE_FORMAT.format({
            'type_str': self._short_name_,
            'uuid_str': self._format_,
        })

    # -------------------------------------------------------------------------
    # Generator
    # -------------------------------------------------------------------------

    @classmethod
    def generator(klass: Type['PolicyId']) -> 'PolicyIdGenerator':
        '''
        Returns a generator instance for PolicyIds.
        '''
        klass._init_invalid_()
        return PolicyIdGenerator(klass)

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    @property
    def _format_(self) -> str:
        '''
        Format our value as a string and return only that.
        '''
        return str(self.value)
