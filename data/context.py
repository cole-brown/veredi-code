# coding: utf-8

'''
Helper classes for managing data contexts for events, error messages, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import List, Any
import enum

from veredi.base.context import EphemerealContext


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
        PLAYER  = 'player'
        MONSTER = 'monster'
        NPC     = 'npc'
        ITEM    = 'item'
        # etc...

        def __str__(self):
            return str(self.value).lower()

    REQUEST_LOAD = 'load-request'
    REQUEST_SAVE = 'save-request'

    REQUEST_TYPE = 'type'
    REQUEST_CAMPAIGN = 'campaign'
    REQUEST_KEYS = {
        DataType.PLAYER:  [ 'user',     'player'  ],
        DataType.MONSTER: [ 'family',   'monster' ],
        DataType.NPC:     [ 'family',   'npc'     ],
        DataType.ITEM:    [ 'category', 'item'    ],
    }

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
        return self.REQUEST_KEYS[self.type]

    @property
    def data_values(self) -> List[str]:
        return [self.sub.get(key, None) for key in self.data_keys]


class DataLoadContext(DataGameContext):
    def __init__(self,
                 name:        str,
                 type:        'DataGameContext.DataType',
                 campaign:    str) -> None:
        super().__init__(name, self.REQUEST_LOAD, type, campaign)

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
