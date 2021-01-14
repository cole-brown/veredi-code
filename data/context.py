# coding: utf-8

'''
Helper classes for managing data contexts for events, error messages, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, List
from veredi.base.null    import Null

from veredi.logger       import log

from veredi.base.context import EphemerealContext
from .repository.taxon   import Taxon


# -----------------------------------------------------------------------------
# Bare Data Context
# -----------------------------------------------------------------------------

class BaseDataContext(EphemerealContext):
    def __repr_name__(self):
        return 'DataCtx'


class DataBareContext(BaseDataContext):
    def __init__(self,
                 dotted: str,
                 ctx_name:  str,
                 load: Any) -> None:
        '''
        Initialize DataBareContext with dotted, ctx_name, and something called
        'load'. Right now just a file name to load for config's data...
        '''
        super().__init__(dotted, ctx_name)
        self._load = load

    @property
    def load(self):
        return self._load

    def __repr_name__(self):
        return 'DBareCtx'


# -----------------------------------------------------------------------------
# Game Data Context
# -----------------------------------------------------------------------------

class DataGameContext(BaseDataContext):

    _REQUEST_LOAD = 'load-request'
    _REQUEST_SAVE = 'save-request'
    _TAXON = 'taxon'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------
    def __init__(self,
                 dotted:   str,
                 ctx_name: str,
                 *taxonomy: Any) -> None:
        '''
        Initialize DataGameContext with dotted, ctx_name, and the load taxonomy
        information (a series of general to specific identifiers of some sort).

        `taxonomy` can be one single Taxon instance, or a list of things to
        create a Taxon from.
        '''
        super().__init__(dotted, ctx_name)

        # Save our taxonomy data into our context.
        ctx = self.sub
        if len(taxonomy) == 1 and isinstance(taxonomy[0], Taxon):
            ctx[self._TAXON] = taxonomy[0]
        else:
            ctx[self._TAXON] = Taxon(*taxonomy)

    @property
    def uid(self) -> Optional[List[Any]]:
        '''
        Get the list of unique ids for this requested data.

        Returns a list or None.
        '''
        ctx = self.sub
        data = ctx.get(self._TAXON, Null())
        return data.taxon or None


class DataLoadContext(DataGameContext):
    '''
    Context for loading data from a repository.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 dotted:   str,
                 *taxonomy: Any) -> None:
        super().__init__(dotted, self._REQUEST_LOAD, *taxonomy)

    # -------------------------------------------------------------------------
    # Python Funcs (& related)
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return 'DLCtx'


class DataSaveContext(DataGameContext):
    '''
    Context for saving data to a repository.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 dotted:   str,
                 *taxonomy: Any) -> None:
        super().__init__(dotted, self._REQUEST_SAVE, *taxonomy)

    # -------------------------------------------------------------------------
    # Python Funcs (& related)
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return 'DSCtx'
