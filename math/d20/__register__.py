# coding: utf-8

'''
Module for auto-magical registration shenanigans.

This will be found and imported by run.registry in order to have whatever
Registries, Registrars, and Registrees this provides available at run-time.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------


# ------------------------------
# Registries & Registrars
# ------------------------------
from veredi.data.codec import register, ignore


# ------------------------------
# Registrees
# ------------------------------
from .tree import (Node, Leaf, Branch,
                   Dice, Constant, Variable,
                   OperatorMath, OperatorAdd, OperatorSub,
                   OperatorMult, OperatorDiv, OperatorPow)


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

# Always register.
register(Dice)
register(Constant)
register(Variable)
register(OperatorAdd)
register(OperatorSub)
register(OperatorMult)
register(OperatorDiv)
register(OperatorPow)


# Always ignore.
ignore(Node)
ignore(Leaf)
ignore(Branch)
ignore(OperatorMath)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
