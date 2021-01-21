# coding: utf-8

'''
A PF2 Game Rules Base Class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, Optional, Any
if TYPE_CHECKING:
    from veredi.base.context   import VerediContext


import enum


from veredi.base                  import label
from veredi.data.config.registry  import register
from veredi.data.repository.taxon import Rank, SavedTaxon

from ..game                       import D20RulesGame


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

class PF2Rank(Rank):
    '''
    What kind of thing is our thing...
    '''

    @enum.unique
    class Phylum(enum.Enum):
        '''
        Top rank for our PF2 game Saved data.
        '''

        INVALID = None

        GAME = 'game'
        ITEM = 'items'
        MONSTER = 'monsters'
        NPC = 'npcs'
        PLAYER = 'players'

        # ------------------------------
        # Python Functions
        # ------------------------------

        def __str__(self) -> str:
            '''
            Python 'to string' function.
            '''
            return self.value

        def __repr__(self) -> str:
            '''
            Python 'to repr' function.
            '''
            return self.__class__.__name__ + '.' + self.name


class PF2SavedTaxon(SavedTaxon):
    '''
    A helpful class for figuring out what game things go where in our taxonomy.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    GAME_SAVED = 'saved'
    '''Name of Saved game record.'''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 phylum:  'PF2Rank.Phylum',
                 *ranks:  str) -> None:
        # This is a SavedTaxon, so:
        #   1) Domain is always GAME (the saved data).
        #   2) Kingdom is always CAMPAIGN (the identifier for /this/ game).
        super().__init__(PF2Rank.Kingdom.CAMPAIGN,
                         phylum,
                         *ranks)

    @classmethod
    def game(self) -> 'PF2SavedTaxon':
        '''
        Create and return a PF2SavedTaxon for the game saved data.
        '''
        return PF2SavedTaxon(PF2Rank.Phylum.GAME,
                             'saved')


# -----------------------------------------------------------------------------
# Game Definition, Saved Data
# -----------------------------------------------------------------------------

@register('veredi', 'rules', 'd20', 'pf2', 'game')
class PF2RulesGame(D20RulesGame):

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
    def dotted(klass: 'PF2RulesGame') -> str:
        '''
        Veredi dotted label string.
        '''
        # _DOTTED magically provided by @register.
        return klass._DOTTED

    # -------------------------------------------------------------------------
    # Loading...
    # -------------------------------------------------------------------------

    def _taxon_saved(self,
                     phylum:    PF2Rank.Phylum,
                     *taxonomy: Any,
                     context:   Optional['VerediContext'] = None
                     ) -> 'PF2SavedTaxon':
        '''
        Create and return a PF2SavedTaxon for this d20.pf2 game rules.

        `context` only (currently [2021-01-21]) used for error log.

        E.g. with game rules 'veredi.rules.d20.pf2', should return a
        PF2SavedTaxon.
        '''
        saved = PF2SavedTaxon(phylum, *taxonomy)
        return saved

    def game_saved(self) -> 'PF2SavedTaxon':
        '''
        Create and return a PF2SavedTaxon for the game saved data.
        '''
        saved = PF2SavedTaxon.game()
        return saved

    # -------------------------------------------------------------------------
    # Saved
    # -------------------------------------------------------------------------

    # Anything?

    # -------------------------------------------------------------------------
    # Definition
    # -------------------------------------------------------------------------

    # Anything?
