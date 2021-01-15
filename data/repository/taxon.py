# coding: utf-8

'''
Taxonomic ranking for identifying things to be loaded by a repository.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, List
import enum

from veredi.logger       import log

from veredi.base import label

from veredi.base.context import EphemerealContext
from .exceptions         import LoadError


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
        rank = '->'.join(self._taxon)
        return f"{self.__class__.__name__}[{rank}]"

    def __repr__(self) -> str:
        '''
        Python 'to repr' function.
        '''
        # Build a string based on whatever taxonomic ranks we have...
        rank = ', '.join(self._taxon)
        return f"{self.__class__.__name__}({rank})"


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
        super().__init__(label.split(dotted))


# -----------------------------------------------------------------------------
# Saved Data Groupings
# -----------------------------------------------------------------------------

class SavedTaxon:
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
        self._taxon = list(ranks)

    # -------------------------------------------------------------------------
    # Properties/Getters
    # -------------------------------------------------------------------------

    def _get(self, negative_index) -> Optional[Any]:
        '''
        Get a taxonomic rank by indexing from the /end/ of the list.

        Returns None if list is too short.
        '''
        return (self._taxon[negative_index]
                if negative_index >= -len(self._taxon) else
                None)

    @property
    def domain(self) -> Any:
        '''
        The first, general grouping for identifying the thing we want to load.
        '''
        return self._get(-8)

    @property
    def kingdom(self) -> Any:
        '''
        The second grouping for identifying the thing we want to
        load.
        '''
        return self._get(-7)

    @property
    def phylum(self) -> Any:
        '''
        The third grouping for identifying the thing we want to
        load.
        '''
        return self._get(-6)

    @property
    def klass(self) -> Any:
        '''
        The forth/middle-most grouping for identifying the thing we want to
        load.
        '''
        return self._get(-5)

    @property
    def order(self) -> Any:
        '''
        The fifth grouping for identifying the thing we want to load.
        '''
        return self._get(-4)

    @property
    def family(self) -> Any:
        '''
        The sixth grouping for identifying the thing we want to load.
        '''
        return self._get(-3)

    @property
    def genus(self) -> Any:
        '''
        The seventh grouping for identifying the thing we want to load.
        '''
        return self._get(-2)

    @property
    def species(self) -> Any:
        '''
        The eight/last grouping for identifying the thing we want to load.
        '''
        return self._get(-1)

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        '''
        Python 'to string' function.
        '''
        # Build a string based on whatever taxonomic ranks we have...
        rank = '->'.join(self._taxon)
        return f"{self.__class__.__name__}[{rank}]"

    def __repr__(self) -> str:
        '''
        Python 'to repr' function.
        '''
        # Build it up with explicitly named params.
        ranks = []
        name = self.domain
        if name:
            ranks.append('domain=' + name)
        name = self.kingdom
        if name:
            ranks.append('kingdom=' + name)
        name = self.phylum
        if name:
            ranks.append('phylum=' + name)
        name = self.klass
        if name:
            ranks.append('klass=' + name)
        name = self.order
        if name:
            ranks.append('order=' + name)
        name = self.family
        if name:
            ranks.append('family=' + name)
        name = self.genus
        if name:
            ranks.append('genus=' + name)
        name = self.species
        if name:
            ranks.append('species=' + name)

        # Combine and return our represetation.
        rank = ', '.join(ranks)
        return f"{self.__class__.__name__}({rank})"
