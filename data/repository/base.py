# coding: utf-8

'''
Base Repository Pattern for load, save, etc. from
various backend implementations (db, file, etc).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type)
if TYPE_CHECKING:
    from veredi.data.config.context import ConfigContext

    from io                         import TextIOBase


from abc import ABC, abstractmethod


from veredi.logger.mixin    import LogMixin
from veredi.base.exceptions import VerediError
from veredi.data            import background
from veredi.data.context    import BaseDataContext, DataAction
from ..exceptions           import LoadError, SaveError

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class BaseRepository(LogMixin, ABC):

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        self._name: str = None
        '''The name of the repository.'''

        self._primary_id: Any = None
        '''The game ID we'll be loading from.'''

    def __init__(self,
                 repo_name:         str,
                 config_context:    Optional['ConfigContext'] = None) -> None:
        '''
        `repo_name` should be short-ish and will be lowercased. It should
        probably be, like, 'file', 'mysql', 'sqlite3' etc...

        `config_context` is the context being used to create us.
        '''
        self._define_vars()
        self._log_define_vars()

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
        raise NotImplementedError(f"{self.__class__.__name__}.background() "
                                  "is not implemented.")

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
            background.Name.DOTTED.key: dotted_name,
            background.Name.TYPE.key: self.name,
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
        ...

    @abstractmethod
    def _key(self,
             context: 'BaseDataContext') -> Any:
        '''
        Give the DataContext, return the data's repository key.
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.load() "
                                  "is not implemented.")

    @abstractmethod
    def load(self,
             context: 'BaseDataContext') -> 'TextIOBase':
        '''
        Loads data from repository based on `load_id`, `load_type`.

        Returns io stream.
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.load() "
                                  "is not implemented.")

    # -------------------------------------------------------------------------
    # Load and/or Save Methods
    # -------------------------------------------------------------------------

    def _load_or_save(self,
                      loading:        Union[bool, BaseDataContext],
                      return_load:    Any,
                      return_save:    Any,
                      return_unknown: Any) -> Any:
        '''
        Returns either `return_load` or `return_save`, based on `loading`.

        If it can't determine which to return: logs at error level, and returns
        `return_unknown`.
        '''
        # ------------------------------
        # DataGameContext -> Load/SaveError
        # ------------------------------
        if isinstance(loading, BaseDataContext):
            # ---
            # Load vs Save comes from the action the context has.
            # ---
            if loading.action == DataAction.LOAD:
                return return_load

            elif loading.action == DataAction.SAVE:
                return return_save

            else:
                self._log_error("Unknown action: '{}'. Cannot determine "
                                "load/save! Returning the unknown value: {}",
                                loading, return_unknown)
                return return_unknown

        # ------------------------------
        # Sanity Check...
        # ------------------------------
        elif isinstance(loading, BaseDataContext):
            self._log_error("Unknown BaseDataContext sub-class: '{}'. Cannot "
                            "determine proper exception type! Returning "
                            "generic VerediError!",
                            loading)
            return return_unknown

        # ------------------------------
        # bool -> Load/SaveError
        # ------------------------------
        else:
            # And the default: loading is bool for "I want LoadError"/"I want
            # the other one".
            return return_load if loading else return_save

    def _error_name(self,
                    loading:    Any,
                    suffix_ing: bool) -> str:
        '''
        Returns either "load"/"loading" or "save"/"saving", based on
        `is_loading` and `suffix_ing`.
        '''
        if suffix_ing:
            return self._load_or_save(loading,
                                      "loading",
                                      "saving",
                                      "loading/saving/munging")
        return self._load_or_save(loading,
                                  "load",
                                  "save",
                                  "load/save/munge")

    def _error_type(self,
                    loading: Union[bool, BaseDataContext]
                    ) -> Type[VerediError]:
        '''
        Returns either LoadError or SaveError, depending on `loading`.
        '''
        return self._load_or_save(loading,
                                  LoadError,
                                  SaveError,
                                  VerediError)
