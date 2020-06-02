# coding: utf-8

'''
Helper classes for managing data contexts for events, error messages, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Dict, Optional, Any, List, Type
import enum
import uuid
import copy

from veredi.logger import log
from veredi.base.exceptions import ContextError
from veredi.base.context import VerediContext, EphemerealContext


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# Data Context
# ------------------------------------------------------------------------------

class BaseDataContext(EphemerealContext):
    def __repr_name__(self):
        return 'DataCtx'


class DataBareContext(BaseDataContext):
    def __init__(self,
                 name: str,
                 key:  str,
                 load: Optional[List[Any]] = None) -> None:
        '''
        Initialize DataBareContext with name, key, and some list called 'load'.
        '''
        super().__init__(name, key)
        self._load = load
        self.sub['load'] = load

    @property
    def load(self):
        return self._load

    def __repr_name__(self):
        return 'DBareCtx'


class DataGameContext(BaseDataContext):

    @enum.unique
    class Type(enum.Enum):
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
        Type.PLAYER:  [ 'user',     'player'  ],
        Type.MONSTER: [ 'family',   'monster' ],
        Type.NPC:     [ 'family',   'npc'     ],
        Type.ITEM:    [ 'category', 'item'    ],
    }

    def __init__(self,
                 name:     str,
                 key:      str,
                 type:     'DataGameContext.Type',
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
    def type(self) -> 'DataGameContext.Type':
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
                 ignored_key: str,
                 type:        'DataGameContext.Type',
                 campaign:    str) -> None:
        super().__init__(name, self.REQUEST_LOAD, type, campaign)

    def __repr_name__(self):
        return 'DLCtx'


class DataSaveContext(DataGameContext):
    def __init__(self,
                 name:    str,
                 type:    'DataGameContext.Type',
                 campaign: str) -> None:
        super().__init__(name, self.REQUEST_SAVE, type, campaign)

    def __repr_name__(self):
        return 'DSCtx'
