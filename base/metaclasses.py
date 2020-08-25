# coding: utf-8

'''
Some general metaclasses for Veredi.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Type, Any

from abc import ABCMeta


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# INVALID Class Property
# -----------------------------------------------------------------------------

class InvalidProvider(type):
    '''
    Metaclass shenanigans to make INVALID a read-only /class/ property.
    '''
    @property
    def INVALID(klass: Type) -> Any:
        return klass._INVALID


class ABC_InvalidProvider(ABCMeta, InvalidProvider):
    '''
    Mixin of ABCMeta and InvalidProvider metaclasses.

    InvalidProvider:
      - Metaclass shenanigans to make INVALID a read-only /class/ property.

    ABCMeta:
      - Makes class an Abstract Base Class.
    '''
    # We have nothing to do other than be the sum of our parents.
    pass
