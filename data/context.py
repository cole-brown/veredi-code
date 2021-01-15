# coding: utf-8

'''
Helper classes for managing data contexts for events, error messages, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, List
from veredi.base.null    import Null

import enum


from veredi.logger       import log

from veredi.base.context import EphemerealContext
from .repository.taxon   import Taxon


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

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 dotted:   str,
                 ctx_name: str,
                 key:      Any,
                 action:   DataAction) -> None:
        '''
        Initialize DataBareContext with `dotted`, `ctx_name`, something called
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
                 action:   DataAction) -> None:
        '''
        Initialize DataBareContext with `dotted`, `ctx_name`, something called
        '`key`' (right now just a file name to load for config's data...),
        and `load`.
        '''
        super().__init__(dotted, ctx_name, key, action)

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
                 dotted:    str,
                 ctx_name:  str,
                 action:    DataAction,
                 *taxonomy: Any) -> None:
        '''
        Initialize DataGameContext with dotted, ctx_name, and the load taxonomy
        information (a series of general to specific identifiers of some sort).

        `taxonomy` can be one single Taxon instance, or a list of things to
        create a Taxon from.
        '''
        # Save our taxonomy data into our context.
        ctx = self.sub
        taxon = None
        if len(taxonomy) == 1 and isinstance(taxonomy[0], Taxon):
            taxon = taxonomy[0]
        else:
            taxon = Taxon(*taxonomy)
        ctx[self._TAXON] = taxon

        # Key is just an easy context.taxon.taxon shortcut for game contexts.
        super().__init__(dotted, ctx_name, taxon.taxon, action)

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
                 dotted:    str,
                 *taxonomy: Any) -> None:
        super().__init__(dotted,
                         self._REQUEST_LOAD,
                         DataAction.LOAD,
                         *taxonomy)

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
                 dotted:    str,
                 *taxonomy: Any) -> None:
        super().__init__(dotted,
                         self._REQUEST_SAVE,
                         DataAction.SAVE,
                         *taxonomy)

    # -------------------------------------------------------------------------
    # Python Funcs (& related)
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return 'DSCtx'
