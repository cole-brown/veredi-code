# coding: utf-8

'''
Evaluator for a Veredi Math Tree.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, Optional, Union
if TYPE_CHECKING:
    from veredi.base.context import VerediContext
from decimal import Decimal

from abc import ABC, abstractmethod

from veredi.logger import log
from .parser import MathTree, FINAL_VALUE_TYPES


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Evaluate Tree Nodes
# -----------------------------------------------------------------------------

class Evaluator:

    @staticmethod
    def eval(root: MathTree,
             context: Optional['VerediContext'] = None
             ) -> Union[int, float, Decimal]:
        '''
        Walk tree, evaluate each node, and return total result.
        '''
        total = 0

        # walk() is depth first, so we'll end this at root. node.eval() does
        # pull values up into branches as it goes, so once everything is
        # evaluated, the root should have the total.
        for each in root.walk():
            total = each.eval()
            if not isinstance(total, FINAL_VALUE_TYPES):
                msg = (f"Node {each} evaluated to unacceptable value "
                       f"({total}) for final eval - cannot resolve "
                       f"math of {root}.")
                raise log.exception(ValueError(msg, total),
                                    msg,
                                    context=context)

        return total
