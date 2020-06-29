# coding: utf-8

'''
Null Object Design Pattern
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, TypeVar, Literal

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

NType = TypeVar('NType')
Nullable = Union[NType, 'Null']
NullNoneOr = Union[NType, 'Null', None]
NullFalseOr = Union[NType, 'Null', Literal[False]]


# -----------------------------------------------------------------------------
# Null Helpers
# -----------------------------------------------------------------------------

def null_or_none(check):
    '''
    Makes sure `check` is neither Null nor None.
    '''
    return (check is Null()
            or check is None)


# -----------------------------------------------------------------------------
# Null Itself
# -----------------------------------------------------------------------------

class NullMeta(type):
    '''
    This Metaclass provides Null's class property 'instance'.
    '''

    def instance(klass):
        return klass._instance

    instance = property(instance)


class Null(metaclass=NullMeta):
    '''
    This Null object singleton always and reliably 'does nothing.'
    '''

    _instance = None

    def __new__(klass, *args, **kwargs):
        '''
        Enforces the singleton.
        '''
        if Null._instance is None:
            Null._instance = super().__new__(klass)
        return Null._instance

    # Have to get this from metaclass.
    # @property
    # def instance(klass):
    #     return __instance

    # -------------------------------------------------------------------------
    # Do-Nothing Methods. Return self where appropriate for Null chaining.
    # -------------------------------------------------------------------------

    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return self

    def __nonzero__(self):
        return 0

    def __getattr__(self, name):
        return self

    def __setattr__(self, name, value):
        return self

    def __delattr__(self, name):
        return self

    # -------------------------------------------------------------------------
    # 'If' Helper
    # -------------------------------------------------------------------------

    def __bool__(self):
        '''
        Null is always Falsy.

        Always returns False as a bool for help in 'if obj:' and 'if not obj:'
        conditionals for classes that use Null.
        '''
        return False

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr__(self):
        return 'Null( )'
