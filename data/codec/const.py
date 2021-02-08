# coding: utf-8

'''
Encodable Types and Constants
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, NewType, Mapping


# -----------------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------------

# ---
# Input Types
# ---
# Any Encodable subclass.

# ---
# Output Types
# ---
EncodedComplex  = NewType('EncodedComplex', Mapping[str, str])
EncodedSimple   = NewType('EncodedSimple',  str)
EncodedEither   = Union[EncodedComplex, EncodedSimple]
