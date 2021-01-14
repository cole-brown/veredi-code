# coding: utf-8

'''
Game Rules Base Class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Type, Any, Union, Tuple)
from veredi.base.null import Null, Nullable
if TYPE_CHECKING:
    from veredi.config.context import ConfigContext

from abc import ABC, abstractmethod


from veredi.logger.mixin          import LogMixin
from veredi.base.const            import VerediHealth
from veredi.base                  import label
from veredi.debug.const           import DebugFlag

from veredi.data                  import background
from veredi.data.repository.taxon import LabelTaxon, SavedTaxon
from veredi.data.records          import (DataType,
                                          DocType,
                                          Definition,
                                          Saved)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class RulesGame(LogMixin, ABC):

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        self._definition: Definition = None
        '''Game's definition data for our D20 Rules-based game.'''

        self._saved: Saved = None
        '''Game's saved data record.'''

    def __init__(self,
                 context:  Optional['ConfigContext']) -> None:
        '''
        Initializes the Game Rules from config/context/repo data.
        '''
        super.__init__()

        self._configure(context)

    def _configure(self,
                   context: 'ConfigContext') -> None:
        '''
        Get rules definition file and configure it for use.
        Load the saved game data.
        '''
        # ---
        # Sanity
        # ---
        config = background.config.config
        if not config:
            raise background.config.exception(
                context,
                None,
                "Cannot configure {} without a Configuration in the "
                "supplied context.",
                self.__class__.__name__)

        # ---
        # TODO: anything else to configure on init?
        # ---

    def loaded(definition: Definition, saved: Saved) -> None:
        '''
        Set our game Definition and Saved data records.
        '''
        self._definition = definition
        self._saved = saved

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @abstractmethod
    @classmethod
    def dotted(klass: 'RulesGame') -> str:
        '''
        Veredi dotted label string.
        '''
        raise NotImplementedError(f"{klass.__name__}.dotted() "
                                  "is not implemented in base class. "
                                  "Subclasses should defined it themselves.")

    @property
    def definition(self) -> Definition:
        '''
        Returns the game Definition data.
        '''
        return self._definition

    @property
    def saved(self) -> Saved:
        '''
        Returns the game Saved data.
        '''
        return self._saved

    # -------------------------------------------------------------------------
    # Loading...
    # -------------------------------------------------------------------------

    def taxon_definition(self) -> 'LabelTaxon':
        '''
        Create and return a LabelTaxon for the game definition data.
        '''
        return LabelTaxon(self.dotted())

    @abstractmethod
    def taxon_saved(self) -> 'SavedTaxon':
        '''
        Create and return a SavedTaxon for the game saved data.
        '''
        raise NotImplementedError(f"{klass.__name__}.taxon_saved() "
                                  "is not implemented in base class. "
                                  "Subclasses should defined it themselves.")

    # -------------------------------------------------------------------------
    # General
    # -------------------------------------------------------------------------

    def _data(self, data_type: DataType) -> Union[Saved, Definition]:
        '''
        Returns either the game's Saved data or its Definition data.

        Raises a ValueError if unknown `data_type`.
        Raises a ValueError if data for `data_type` is Null/None/empty.
        '''
        data = None
        if data_type is DataType.SAVED:
            data = self._saved

        elif data_type is DataType.DEFINITION:
            data = self._definition

        else:
            msg = (f"{self.dotted()}: Unknown type '{data_type}'; do not "
                   "have data to return for it.")
            error = ValueError(msg, data_type)
            raise self._log_exception(error, msg)

        if not data:
            msg = (f"{self.dotted()}: No data for '{data_type}'!")
            error = ValueError(msg, data_type)
            raise self._log_exception(error, msg)

        return data

    def _get(self, data_type: DataType, *keychain: str) -> Any:
        '''
        Gets a value from the definition or saved data, depending
        on `data_type`.

        Follows `keychain` in order to find the value. Example
            data_type: DataType.DEFINITION
            keychain:  'time', 'round'
            definition:
                --- !definition.game
                time:
                  tick: veredi.game.time.tick.round
                  round: 6 seconds
          -> 6 seconds
             - TODO: Type? Probably a timespan?
        '''
        # ---
        # Sanity
        # ---
        # TODO: Verify keychain is correct for our document. Use a less
        # temporary solution than what Config does.
        #   Config's "temporary" solution:
        #     hierarchy = Document.hierarchy(doc_type)
        #     if not hierarchy.valid(*keychain):
        #         raise self._log_exception(
        #             exceptions.ConfigError,
        #             "Invalid keychain '{}' for {} document type. See its "
        #             "Hierarchy class for proper layout.",
        #             keychain, doc_type)

        # ---
        # Get the relevant record.
        # ---
        # Raises error if no data.
        data = self._data(data_type)

        # ---
        # Get the value by following the keychain.
        # ---
        value = data
        for key in keychain:
            value = value.get(key, None)
            if value is None:
                self._log_debug("No data for key {key} in keychain {keychain} "
                                "in our {data_type} data. "
                                "'{key}' data: {}, "
                                "all '{data_type}' data: {}",
                                value, data,
                                key=key,
                                keychain=keychain,
                                data_type=data_type)
                return Null()

        return value

    # -------------------------------------------------------------------------
    # Saved
    # -------------------------------------------------------------------------

    def _save(self) -> bool:
        '''
        Saves our Saved game record. Returns success/failure bool.
        '''
        # TODO: THIS!!! I need the whole "saving" things side of
        # serdes/repo/etc.
        raise NotImplementedError(
            f"{self.__class__..__name__}._save() "
            "is not implemented. "
            "I need that save side of data serialization.")
        return False

    # -------------------------------------------------------------------------
    # Definition
    # -------------------------------------------------------------------------

    # Anything?
