# coding: utf-8

'''
Helper classes for managing data contexts for events, error messages, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, List, Dict
import enum

from veredi.logger       import log

from veredi.base.context import EphemerealContext
from .exceptions         import LoadError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Data Context
# -----------------------------------------------------------------------------

class BaseDataContext(EphemerealContext):
    def __repr_name__(self):
        return 'DataCtx'


class DataBareContext(BaseDataContext):
    def __init__(self,
                 name: str,
                 key:  str,
                 load: Any) -> None:
        '''
        Initialize DataBareContext with name, key, and something called 'load'.
        Right now just a file name to load for config's data...
        '''
        super().__init__(name, key)
        self._load = load

    @property
    def load(self):
        return self._load

    def __repr_name__(self):
        return 'DBareCtx'


class DataGameContext(BaseDataContext):

    @enum.unique
    class DataType(enum.Enum):

        # ---
        # Entities
        # ---
        PLAYER  = 'player'
        MONSTER = 'monster'
        NPC     = 'npc'
        ITEM    = 'item'

        # ---
        # Misc/Etc...
        # ---
        GAME = 'game'

        def __str__(self):
            return str(self.value).lower()

    REQUEST_LOAD = 'load-request'
    REQUEST_SAVE = 'save-request'

    REQUEST_TYPE = 'type'
    REQUEST_CAMPAIGN = 'campaign'
    REQUEST_KEYS = {
        # ---
        # Entities
        # ---
        DataType.PLAYER:  [ 'user',     'player'  ],
        DataType.MONSTER: [ 'family',   'monster' ],
        DataType.NPC:     [ 'family',   'npc'     ],
        DataType.ITEM:    [ 'category', 'item'    ],

        # ---
        # Misc/Etc...
        # ---
    }
    '''
    Requests for a specific entity or other saved thing that there can be many
    of.
    '''

    _REQUEST_CONSTS = {
        DataType.GAME: [ 'game', 'record' ],
    }
    '''
    Requests for some saved data that exists as a singleton.
    '''

    def __init__(self,
                 name:     str,
                 key:      str,
                 type:     'DataGameContext.DataType',
                 campaign: str) -> None:
        '''
        Initialize DataGameContext with name, key, and type.
        '''
        super().__init__(name, key)
        self._type = type

        # Save our request type, request keys into our context.
        ctx = self.sub
        for key in self.data_keys:
            ctx[key] = None

        ctx[self.REQUEST_TYPE] = str(type)
        ctx[self.REQUEST_CAMPAIGN] = campaign

    @property
    def type(self) -> 'DataGameContext.DataType':
        return self._type

    @property
    def campaign(self) -> str:
        return self.sub[self.REQUEST_CAMPAIGN]

    @property
    def data_keys(self) -> List[str]:
        '''
        Get the keys that should exist in our data.
        '''
        # Is it the usual?
        try:
            return self.REQUEST_KEYS[self.type]

        except KeyError:
            # Hopefully it's a const then.
            return self._REQUEST_CONSTS[self.type]

        # Can't get to me here.

    @property
    def data_values(self) -> List[str]:
        return [self.sub.get(key, None) for key in self.data_keys]


class DataLoadContext(DataGameContext):

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    _LOAD_REQUEST_CONSTS = {
        # Just zip the keys list together with itself for these constants so
        # that normal load code path works with changes.
        DataGameContext.DataType.GAME: dict(zip(
            DataGameContext._REQUEST_CONSTS[DataGameContext.DataType.GAME],
            DataGameContext._REQUEST_CONSTS[DataGameContext.DataType.GAME]
        )),
    }
    '''
    Requests for some saved data that exists as a singleton.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 name:        str,
                 type:        'DataGameContext.DataType',
                 campaign:    str) -> None:
        super().__init__(name, self.REQUEST_LOAD, type, campaign)

    # -------------------------------------------------------------------------
    # Load Requests
    # -------------------------------------------------------------------------

    # ------------------------------
    # Generic
    # ------------------------------

    def set_load_request(self,
                         load_data: Dict[str, str]) -> None:
        '''
        Set our sub-context up for a specific load.
        '''
        for key in load_data:
            # Add load_data[key] into sub-context[key] if possible (don't
            # overwrite pre-existing).
            self.sub_add(key, key, load_data[key])

    # ------------------------------
    # Generic
    # ------------------------------

    def game_load_request(self) -> None:
        '''
        Set our sub-context up for loading the game's saved (meta-)data.
        '''
        self.set_load_request(
            self._LOAD_REQUEST_CONSTS[DataGameContext.DataType.GAME])

    # -------------------------------------------------------------------------
    # Python Funcs (& related)
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return 'DLCtx'


class DataSaveContext(DataGameContext):
    def __init__(self,
                 name:    str,
                 type:    'DataGameContext.DataType',
                 campaign: str) -> None:
        super().__init__(name, self.REQUEST_SAVE, type, campaign)

    def __repr_name__(self):
        return 'DSCtx'
