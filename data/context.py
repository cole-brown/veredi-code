# coding: utf-8

'''
Helper classes for managing data contexts for events, error messages, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, Dict
from veredi.base.null    import NullNoneOr

import enum


from veredi.logger       import log

from veredi.base.context import EphemerealContext
from veredi.data         import background

from .repository.taxon   import Taxon, LabelTaxon, SavedTaxon


# -----------------------------------------------------------------------------
# Data Actions
# -----------------------------------------------------------------------------

@enum.unique
class DataAction(enum.Enum):
    '''
    Action to perform on the Data.
    '''

    UNKNOWN = enum.auto()
    '''Action is not known...'''

    LOAD = enum.auto()
    '''Load data action.'''

    SAVE = enum.auto()
    '''Save data action.'''


# -----------------------------------------------------------------------------
# Bare Data Context
# -----------------------------------------------------------------------------

class BaseDataContext(EphemerealContext):
    '''
    Base class for DataContexts.
    '''

    _KEY = 'key'
    _ACTION = 'action'

    _TO_TEMP = 'temp'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 dotted:   str,
                 ctx_name: str,
                 key:      Any,
                 action:   DataAction) -> None:
        '''
        Initialize BaseDataContext with `dotted`, `ctx_name`, something called
        '`key`' (right now just a file name to load for config's data...),
        and `load`.
        '''
        super().__init__(dotted, ctx_name)

        # Set our key and action into the context.
        self.key = key
        self.action = action

    # -------------------------------------------------------------------------
    # Add-to-Context Helpers
    # -------------------------------------------------------------------------

    @property
    def key(self) -> Optional[Any]:
        '''
        Get the key from our context data.
        '''
        return self.sub.get(self._KEY, None)

    @key.setter
    def key(self, key: Any) -> None:
        '''
        Set the key in our context data.
        '''
        self.sub[self._KEY] = key

    @property
    def action(self) -> DataAction:
        '''
        Get the action from our context data.
        If no action set, returns DataAction.UNKNOWN.
        '''
        return self.sub.get(self._ACTION, DataAction.UNKNOWN)

    @action.setter
    def action(self, action: DataAction) -> None:
        '''
        Set the action in our context data.
        '''
        self.sub[self._ACTION] = action

    @property
    def temp(self) -> bool:
        '''
        Returns the context's temp flag or False.
        '''
        # Only DataBareContext and DataSaveContext have temp, currently...
        # But we can try anyways.
        ctx = self.sub
        temp = ctx.get(self._TO_TEMP, False)
        return temp

    # -------------------------------------------------------------------------
    # Repository Helpers
    # -------------------------------------------------------------------------

    @property
    def repo_data(self) -> Dict[str, Any]:
        '''
        Context data that the repostiory has inserted into this DataContext.
        '''
        repo_ctx = self._get_sub(str(background.Name.REPO), False)
        return repo_ctx

    @repo_data.setter
    def repo_data(self,
                  data: NullNoneOr[Dict[str, Any]],
                  overwrite: bool = False) -> None:
        '''
        Setter for the repository to insert its context data into our context.
        '''
        self._set_sub(str(background.Name.REPO),
                      data,
                      overwrite)

    # -------------------------------------------------------------------------
    # String Helper
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return 'DataCtx'


class DataBareContext(BaseDataContext):
    '''
    DataContext for 'bare' repository.

    E.g. FileBareRepository vs FileTreeRepository.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 dotted:   str,
                 ctx_name: str,
                 key:      Any,
                 action:   DataAction,
                 temp:     bool = False) -> None:
        '''
        Initialize DataBareContext with `dotted`, `ctx_name`, something called
        '`key`' (right now just a file name to load for config's data...),
        and `load`.
        '''
        super().__init__(dotted, ctx_name, key, action)

        ctx = self.sub
        ctx[self._TO_TEMP] = temp or False

    # -------------------------------------------------------------------------
    # String Helper
    # -------------------------------------------------------------------------

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
                 action:   DataAction,
                 taxon:    Taxon) -> None:
        '''
        Initialize DataGameContext with caller's dotted, ctx_name, and the load
        taxonomy information (a series of general to specific identifiers of
        some sort).

        `taxonomy` can be one single Taxon instance, or a list of things to
        create a SavedTaxon from.
        '''
        # Sanity check...
        if not isinstance(taxon, Taxon):
            msg = (f"Must have a Taxon for the {self.__class__.__name__} "
                   f"- cannot initialize with: {taxon}")
            error = TypeError(msg, dotted, ctx_name, taxon)
            raise log.exception(error, msg)

        # Key is just an easy context.taxon.taxon shortcut for game contexts.
        super().__init__(dotted, ctx_name, taxon.taxon, action)

        # Save our taxon into our context. NOTE: Must do after
        # super().__init__() in order to get our key assigned.
        ctx = self.sub
        ctx[self._TAXON] = taxon

    @property
    def taxon(self) -> Optional[Taxon]:
        '''
        Returns the context's Taxon or None.
        '''
        ctx = self.sub
        taxon = ctx.get(self._TAXON, None)
        return taxon


class DataLoadContext(DataGameContext):
    '''
    Context for loading data from a repository.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 dotted: str,
                 taxon:  Taxon) -> None:
        super().__init__(dotted,
                         self._REQUEST_LOAD,
                         DataAction.LOAD,
                         taxon)

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
                 dotted: str,
                 taxon:  Taxon,
                 temp:   bool = False) -> None:
        '''
        If `temp` is True, save this to a temporary directory.
        Useful for e.g. unit testing.
        '''
        super().__init__(dotted,
                         self._REQUEST_SAVE,
                         DataAction.SAVE,
                         taxon)

        ctx = self.sub
        ctx[self._TO_TEMP] = temp

    # -------------------------------------------------------------------------
    # Python Funcs (& related)
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return 'DSCtx'
