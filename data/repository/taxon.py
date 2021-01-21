# coding: utf-8

'''
Taxonomic ranking for identifying things to be loaded by a repository.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, List, Dict


import enum


from veredi.base import label


# -----------------------------------------------------------------------------
# Named Ranks
# -----------------------------------------------------------------------------

class Rank:
    '''
    Namespace for named Rank enums for Taxons.
    '''

    # -------------------------------------------------------------------------
    # Named Ranks
    # -------------------------------------------------------------------------

    @enum.unique
    class Domain(enum.Enum):
        '''
        The most general rank of a taxon - what data is it.
        '''
        # ------------------------------
        # Enum Members
        # ------------------------------

        INVALID = None
        '''An invalid domain.'''

        GAME = 'game'
        '''Game data like saved characters, monsters, items, etc.'''

        DEFINITIONS = 'definitions'
        '''System/rules definitions like skills, etc.'''

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

    @enum.unique
    class Kingdom(enum.Enum):
        '''
        The second-most general rank of a taxon - game id lives here.
        '''
        # ------------------------------
        # Enum Members
        # ------------------------------

        INVALID = None
        '''An invalid knigdom.'''

        CAMPAIGN = enum.auto()
        '''
        Game-instance-specific data like saved characters, monsters, items,
        etc.
        '''

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

    # -------------------------------------------------------------------------
    # Helper Functions
    # -------------------------------------------------------------------------

    @classmethod
    def replace(klass: 'Rank', rank: Any) -> Any:
        '''
        If `rank` is a Rank member enum, and we know how to do the
        substitution, this will return the substitution.

        Otherwise it returns `rank`.
        '''
        if isinstance(rank, klass.Domain):
            return rank.value

        return rank


# -----------------------------------------------------------------------------
# Base Class
# -----------------------------------------------------------------------------

class Taxon:
    '''
    An ordering of identifiers.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        super()._define_vars()

        self._taxon: List[Any] = []
        '''
        The ordered list of identifiers for the thing we want to load.
        '''

    def __init__(self,
                 *ranks: Any) -> None:
        '''
        Initialize the Taxon with the provided ranks.
        '''
        self._taxon = list(ranks)

    # -------------------------------------------------------------------------
    # Properties/Getters
    # -------------------------------------------------------------------------

    @property
    def taxon(self) -> List[Any]:
        '''
        Get the full taxonomic rank list.
        '''
        return self._taxon

    def resolve(self, replacements: Dict[Any, Any]) -> List[Any]:
        '''
        Returns a list of taxon ranks resolved based on `replacements`.
        Any ranks not found in `replacements` are returns as-is.
        '''
        resolved = []
        for rank in self._taxon:
            # Try provided dict first, then any default replacements.
            replace_with = replacements.get(rank, None)
            if not replace_with:
                replace_with = Rank.replace(rank)
            resolved.append(replace_with)
        return resolved

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __iter__(self):
        '''
        Iterate over the taxon ranks:
          taxon = Taxon(...)
          for rank in taxon:
            print(rank)
        '''
        return iter(self._taxon)

    def __str__(self) -> str:
        '''
        Python 'to string' function.
        '''
        # Build a string based on whatever taxonomic ranks we have...
        ranks = '->'.join([str(rank) for rank in self._taxon])
        return f"{self.__class__.__name__}[{ranks}]"

    def __repr__(self) -> str:
        '''
        Python 'to repr' function.
        '''
        # Build a string based on whatever taxonomic ranks we have...
        ranks = ', '.join([str(rank) for rank in self._taxon])
        return f"{self.__class__.__name__}({ranks})"


# -----------------------------------------------------------------------------
# Definition Data Groupings
# -----------------------------------------------------------------------------

class LabelTaxon(Taxon):
    '''
    An ordering of identifiers based on veredi dotted labels.
    '''

    def __init__(self, dotted: str) -> None:
        '''
        Initialize the LabelTaxon with the provided dotted label.
        '''
        super().__init__(Rank.Domain.DEFINITIONS,
                         *label.split(dotted))

    def __str__(self) -> str:
        '''
        Python 'to string' function.
        '''
        # Build a string based on whatever taxonomic ranks we have...
        dotted = label.join(*[str(rank) for rank in self._taxon])
        return f"{self.__class__.__name__}['{dotted}']"


# -----------------------------------------------------------------------------
# Saved Data Groupings
# -----------------------------------------------------------------------------

class SavedTaxon(Taxon):
    '''
    An ordering of identifiers based on biology names.
      Domain
        -> Kingdom
           -> Phylum
              -> Class
                 -> Order
                    -> Family
                       -> Genus
                          -> Species

    https://en.wikipedia.org/wiki/Taxon
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 *ranks: Any) -> None:
        '''
        Initialize the Taxon with the provided taxonomic ranks.

        Fill our grouping vars so that the least specific are left
        unset/unchanged if not enough args supplied.
        '''
        super().__init__(Rank.Domain.GAME,
                         *ranks)

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        '''
        Python 'to string' function.
        '''
        # Build a string based on whatever taxonomic ranks we have...
        rank = '->'.join([str(rank) for rank in self._taxon])
        return f"{self.__class__.__name__}[{rank}]"

    def __repr__(self) -> str:
        '''
        Python 'to repr' function.
        '''
        # Build a string based on whatever taxonomic ranks we have...
        rank = ', '.join([str(rank) for rank in self._taxon])
        return f"{self.__class__.__name__}(*{rank})"
