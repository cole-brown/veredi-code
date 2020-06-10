# coding: utf-8

'''
Base Repository Pattern for load, save, etc. from
various backend implementations (db, file, etc).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional
from abc import ABC, abstractmethod

from io import TextIOBase

from veredi.base.context import PersistentContext
from veredi.data.context import BaseDataContext
from veredi.data.config.context import ConfigContext


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class BaseRepository(ABC):

    def __init__(self,
                 repo_name:         str,
                 self_context_name: str,
                 self_context_key:  str,
                 config_context:    Optional[ConfigContext] = None) -> None:
        '''
        `repo_name` should be short-ish and will be lowercased. It should
        probably be, like, 'file', 'mysql', 'sqlite3' etc...

        `self_context_name` and `self_context_key` are for /my/ context -
        used for Event and Error contexts.

        `config_context` is the context being used to create us.
        '''
        self._context = PersistentContext(self_context_name, self_context_key)
        self._name = repo_name.lower()
        self._configure(config_context)

    # -------------------------------------------------------------------------
    # Repo Properties/Methods
    # -------------------------------------------------------------------------

    @property
    def name(self) -> str:
        '''
        Should be short-ish and will be lowercased. It should probably be,
        like, 'file', 'mysql', 'sqlite3' etc...
        '''
        return self._name

    # -------------------------------------------------------------------------
    # Context Properties/Methods
    # -------------------------------------------------------------------------

    @property
    def context(self):
        '''
        Will be the context of this class.
        '''
        return self._context

    # -------------------------------------------------------------------------
    # Abstract Methods
    # -------------------------------------------------------------------------

    @abstractmethod
    def _configure(self,
                   context: Optional[ConfigContext]) -> None:
        '''
        Allows repos to grab anything from the config data that they need to
        set up themselves.
        '''
        pass

    @abstractmethod
    def load(self,
             context: BaseDataContext) -> TextIOBase:
        '''
        Loads data from repository based on `load_id`, `load_type`.

        Returns io stream.
        '''
        raise NotImplementedError
