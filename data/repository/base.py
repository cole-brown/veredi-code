# coding: utf-8

'''
Base Repository Pattern for load, save, etc. from
various backend implementations (db, file, etc).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional)
if TYPE_CHECKING:
    from veredi.base.context import VerediContext
    from veredi.data.config.context import ConfigContext
    from veredi.data.context import BaseDataContext
    from io import TextIOBase

from abc import ABC, abstractmethod


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class BaseRepository(ABC):

    def __init__(self,
                 repo_name:         str,
                 config_context:    Optional['ConfigContext'] = None) -> None:
        '''
        `repo_name` should be short-ish and will be lowercased. It should
        probably be, like, 'file', 'mysql', 'sqlite3' etc...

        `config_context` is the context being used to create us.
        '''
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
    @abstractmethod
    def background(self):
        '''
        Data for the Veredi Background context.
        '''
        raise NotImplementedError

    def _make_background(self, dotted_name):
        '''
        Start of the background data.

        `dotted_name` should be the dotted version of your @register() string.
        e.g. for:
          @register('veredi', 'repository', 'file-bare')
        `dotted_name` is:
          'veredi.repository.file-bare'
        '''
        return {
            'name': dotted_name,
            'type': self.name,
        }

    # -------------------------------------------------------------------------
    # Abstract Methods
    # -------------------------------------------------------------------------

    @abstractmethod
    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''
        Allows repos to grab anything from the config data that they need to
        set up themselves.
        '''
        pass

    @abstractmethod
    def definition(self,
                   dotted_name: str,
                   context: 'VerediContext') -> 'TextIOBase':
        '''
        Load a definition data from repository based on `dotted_name`.
        '''
        raise NotImplementedError

    @abstractmethod
    def load(self,
             context: 'BaseDataContext') -> 'TextIOBase':
        '''
        Loads data from repository based on `load_id`, `load_type`.

        Returns io stream.
        '''
        raise NotImplementedError
