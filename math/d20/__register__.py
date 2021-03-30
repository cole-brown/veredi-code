# coding: utf-8

'''
Module for auto-magical registration shenanigans.

This will be found and imported by run.registry in order to have whatever
Registries, Registrars, and Registrees this provides available at run-time.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.data.registration import codec, config


# ----------------------------------------------------------------------------
# Imports: Registration
# ----------------------------------------------------------------------------
from .tree import (Node, Leaf, Branch,
                   Dice, Constant, Variable,
                   OperatorMath, OperatorAdd, OperatorSub,
                   OperatorMult, OperatorDiv, OperatorPow)

from .parser import D20Parser


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

# Always register.
codec.register(Dice)
codec.register(Constant)
codec.register(Variable)
codec.register(OperatorAdd)
codec.register(OperatorSub)
codec.register(OperatorMult)
codec.register(OperatorDiv)
codec.register(OperatorPow)

# Always ignore.
codec.ignore(Node)
codec.ignore(Leaf)
codec.ignore(Branch)
codec.ignore(OperatorMath)


config.register(D20Parser)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
