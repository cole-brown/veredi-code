# coding: utf-8

'''
Helper classes for managing security contexts.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import List, Any
import enum

from veredi.base.context import EphemerealContext


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Security Context
# -----------------------------------------------------------------------------

class SecurityContext(EphemerealContext):
    '''
    Base class for SecurityContexts. Classes/modules that just want type
    hinting and/or don't know exactly what goes on beyond 'is this allowed to
    happen' should use this class.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # @enum.unique
    # class Key(enum.Enum):
    #     # ------------------------------
    #     # Base Level Keys:
    #     # ------------------------------
    #     SUBJECT    = 'subject'
    #     RESOURCE   = 'resource'
    #     ACTION     = 'action'
    #     CONTEXT    = 'context'
    #
    #     # ------------------------------
    #     # Second Level Keys:
    #     # ------------------------------
    #     ID         = 'id'
    #     ATTRIBUTES = 'attributes'
    #
    #     def __str__(self):
    #         return str(self.value).lower()

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    # def __init__(self,
    #              name: str,
    #              key:  str) -> None:
    #     '''
    #     Initialize SecurityContexts with name, key and _____.
    #     '''
    #     super().__init__(name, key)

    # -------------------------------------------------------------------------
    # Python Functions & Helpers for Them.
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return 'SecCtx'
