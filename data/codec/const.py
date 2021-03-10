# coding: utf-8

'''
Encodable Types and Constants
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, NewType, Mapping

import enum


from veredi.base           import numbers
from veredi.base.enum      import FlagCheckMixin, FlagSetMixin
from veredi.base.null      import Null


# -----------------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------------

# ---
# Input Types
# ---
# Any Encodable subclass.
EncodeNull = NewType('EncodeNull', Union[None, Null])
EncodeAsIs = NewType('EncodeAsIs', Union[str, numbers.NumberTypes])
EncodeAsIsTuple = (str, *numbers.NumberTypesTuple)

# ---
# Output Types
# ---
EncodedComplex  = NewType('EncodedComplex', Mapping[str, str])
EncodedSimple   = NewType('EncodedSimple',  str)
EncodedEither   = Union[EncodedComplex, EncodedSimple]



# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

@enum.unique
class Encoding(FlagCheckMixin, FlagSetMixin, enum.Flag):
    '''
    What sort of data are we expecting from this encodable?
    '''
    INVALID = None
    '''Do not use this one.'''

    SIMPLE = enum.auto()
    '''A string, numbers, etc.'''

    COMPLEX = enum.auto()
    '''Sequences, Maps, etc.'''

    BOTH = SIMPLE | COMPLEX
    '''Can be encoded as either simple or complex, depending on situation.'''
