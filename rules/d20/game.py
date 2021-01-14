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

class D20SavedTaxon(SavedTaxon):
    '''
    A helpful class for figuring out what game things go where in our taxonomy.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # Nothing above family, currently...

    @enum.unique
    class Family(enum.Enum):
        '''
        What kind of thing is our thing...
        '''
        # ------------------------------
        # Enum Members
        # ------------------------------

        GAME = 'game'
        ITEM = 'item'
        MONSTER = 'monster'
        NPC = 'npc'
        PLAYER = 'player'

        # ------------------------------
        # Python Functions
        # ------------------------------

        def __str__(self) -> str:
            '''
            Python 'to string' function.
            '''
            return self.__class__.__name__ + '.' + self.name

        def __repr__(self) -> str:
            '''
            Python 'to repr' function.
            '''
            return self.__class__.__name__ + '.' + self.name

    # Cannot specify most here - depends on data that campaign/rule-set has:
    #   - genus
    #   - species
    # Can specify for the game data though.

    GENUS_GAME = 'game'
    SPECIES_GAME = 'saved'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 family:  Family,
                 genus:   str,
                 species: str) -> None:
        super().__init__(family, genus, species)

    @classmethod
    def game(self) -> 'D20SavedTaxon':
        '''
        Create and return a D20SavedTaxon for the game saved data.
        '''
        return D20SavedTaxon(Family.GAME, 'game', 'saved')


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
        return 'veredi.rules.d20.pf2.game'

    # -------------------------------------------------------------------------
    # Loading...
    # -------------------------------------------------------------------------

    def taxon_saved(self) -> 'D20SavedTaxon':
        '''
        Create and return a D20SavedTaxon for the game saved data.
        '''
        return D20SavedTaxon.game()

    # -------------------------------------------------------------------------
    # Saved
    # -------------------------------------------------------------------------

    # Anything?

    # -------------------------------------------------------------------------
    # Definition
    # -------------------------------------------------------------------------

    # Anything?
