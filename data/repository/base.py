# coding: utf-8

'''
Base Repository Pattern for load, save, etc. from
various backend implementations (db, file, etc).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type, Dict, List, Tuple)
if TYPE_CHECKING:
    from veredi.data.config.context import ConfigContext

    from io                         import TextIOBase


from abc import ABC, abstractmethod


from veredi.logs               import log
from veredi.logs.mixin         import LogMixin
from veredi.base.strings       import label
from veredi.base.strings.mixin import NamesMixin
from veredi.base.exceptions    import VerediError
from veredi.data               import background
from veredi.data.context       import BaseDataContext, DataAction
from ..exceptions              import LoadError, SaveError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class BaseRepository(ABC, LogMixin, NamesMixin):
    '''
     Repository sub-classes are expected to use kwargs:
      - Required:
        + name_dotted: Optional[label.LabelInput]
          - string/strings to create the Veredi dotted label.
        + name_string: Optional[str]
          - Any short string for describing class. Either short-hand or class's
            __name__ are fine.
      - Optional:
        + name_klass:        Optional[str]
          - If None, will be class's __name__.
        + name_string_xform: Optional[Callable[[str], str]] = None,
        + name_klass_xform:  Optional[Callable[[str], str]] = to_lower_lambda,

    Example:
      class JeffRepository(BaseRepository,
                           name_dotted=label.normalize('repository', 'jeff'),
                           name_string='repo.jeff')
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # ------------------------------
    # Logging
    # ------------------------------

    _LOG_INIT: List[log.Group] = [
        log.Group.START_UP,
        log.Group.DATA_PROCESSING
    ]
    '''
    Group of logs we use a lot for log.group_multi().
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        self._primary_id: Any = None
        '''The game ID we'll be loading from.'''

    def __init__(self,
                 config_context:    Optional['ConfigContext'] = None) -> None:
        '''
        `config_context` is the context being used to create us.
        '''
        self._define_vars()

        # ---
        # Set-Up LogMixin before _configure() so we have logging.
        # ---
        self._log_config(self.dotted)
        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              f"{self.__class__.__name__} init...")
        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              "BaseRepository init...")

        # ---
        # Configure ourselves.
        # ---
        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              "Configure repo...")
        self._configure(config_context)

        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              "Done with BaseRepository init.")

    # -------------------------------------------------------------------------
    # Repo Properties/Methods
    # -------------------------------------------------------------------------

    @property
    def primary_id(self) -> str:
        '''
        The primary id (game/campaign name, likely, for file-tree repo).
        '''
        return self._primary_id

    # -------------------------------------------------------------------------
    # Context Properties/Methods
    # -------------------------------------------------------------------------

    @property
    @abstractmethod
    def background(self) -> Tuple[Dict[str, str], background.Ownership]:
        '''
        Data for the Veredi Background context.
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.background() "
                                  "is not implemented.")

    def _make_background(self) -> None:
        '''
        Base class's contribution to the background data.
        '''
        return {
            background.Name.DOTTED.key: self.dotted,
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
        Loads data from the repository based on data in the `context`.

        Returns io stream.
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.load() "
                                  "is not implemented.")

    @abstractmethod
    def save(self,
             data:    'TextIOBase',
             context: 'BaseDataContext') -> bool:
        '''
        Saves data to the repository based on data in the `context`.

        Returns success/failure of save operation.
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

    # -------------------------------------------------------------------------
    # Unit Testing Helpers
    # -------------------------------------------------------------------------

    def _ut_set_up(self) -> None:
        '''
        Set-up for unit testing.

        E.g. FileTreeRepository can create its temp dir.
        '''
        # Default set-up: nothing.
        pass

    def _ut_tear_down(self) -> None:
        '''
        Tear-down for unit testing.

        E.g. FileTreeRepository can delete its temp dir.
        '''
        # Default tear-down: also nothing.
        pass
