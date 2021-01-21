# coding: utf-8

'''
A D20 Game Rules Base Class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.data.repository.taxon import SavedTaxon

import enum


from ..game import RulesGame


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Game Definition, Saved Data
# -----------------------------------------------------------------------------

class D20RulesGame(RulesGame):

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    # def _define_vars(self) -> None:
    #     '''
    #     Instance variable definitions, type hinting, doc strings, etc.
    #     '''
    #     super()._define_vars()

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @classmethod
    def dotted(klass: 'D20RulesGame') -> str:
        '''
        Veredi dotted label string.
        '''
        # _DOTTED magically provided by @register.
        return klass._DOTTED

    # -------------------------------------------------------------------------
    # Saved
    # -------------------------------------------------------------------------

    # Anything?

    # -------------------------------------------------------------------------
    # Definition
    # -------------------------------------------------------------------------

    # Anything?
