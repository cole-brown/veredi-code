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

from veredi.logs          import log
from veredi.base.identity import SerializableId
from veredi.base.strings  import labeler
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


class PolicyId(SerializableId,
               name_dotted='veredi.security.abac.identity.policy',
               name_string='identity.policy'):
    '''
    Serializable PolicyId class.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # ------------------------------
    # Static UUIDs
    # ------------------------------

    _UUID_NAMESPACE: uuid.UUID = uuid.UUID(
        '5aac710d-8f35-5a25-9425-df41c4a9d214'
    )
    '''
    The 'namespace' for our UUIDs will be static so we can
    reproducably/reliably generate a UUID. Generated by:
      uuid.uuid5(uuid.UUID(int=0), 'veredi.security.abac.identity.PolicyId')
    '''

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

    # Everything from parent is fine.

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
