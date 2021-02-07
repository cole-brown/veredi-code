# coding: utf-8

'''
Configuration file reader/writer for Veredi games.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Any, Mapping, Dict, Tuple)
from veredi.base.null import Nullable, Null
if TYPE_CHECKING:
    from veredi.base.context         import VerediContext
    from veredi.data.repository.base import BaseRepository
    from veredi.data.serdes.base     import BaseSerdes, DeserializeTypes

import pathlib

from veredi.logger          import log
from veredi.base.string     import label
from veredi.base.exceptions import VerediError
from veredi.data.context    import DataAction, DataBareContext
from veredi.base.const      import VerediHealth
from veredi.rules.game      import RulesGame

from ..                     import background
from ..exceptions           import ConfigError, LoadError
from .                      import registry
from .hierarchy             import Document, Hierarchy
from .context               import ConfigContext
from ..repository.file.bare import FileBareRepository
from ..serdes.yaml.serdes   import YamlSerdes


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

THIS_DIR = pathlib.Path(__file__).resolve().parent
DEFAULT_NAME = 'config.veredi.yaml'


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def default_path() -> Optional[pathlib.Path]:
    '''Returns absolute path to the DEFAULT config file.

    Returns None if file does not exist.

    '''
    if not THIS_DIR.exists():
        return None

    path = THIS_DIR / DEFAULT_NAME
    if not path.exists():
        return None
    return path


class Configuration:
    '''Config data for how a game will run and what stuff it will use.'''

    _DOTTED_NAME = 'veredi.data.config.config'

    _CTX_KEY  = 'configuration'
    _CTX_NAME = 'configuration'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''

        self._path: pathlib.Path = None
        '''
        Path to our config file.
        '''

        self._config: Dict[Any, Any] = {}
        '''
        Our storage of the config data itself.
        '''

        self._repo: 'BaseRepository' = None
        '''
        The repository for the game's saved data.
        '''

        self._serdes: 'BaseSerdes' = None
        '''
        The serializer/deserializer for the game's saved data.
        '''

        self._rules: label.DotStr = None
        '''
        The game's dotted label for the rules.
        '''

        self._id: str = None
        '''
        The game's repository id/key/record-name string.
        '''

    def __init__(self,
                 rules:         label.LabelInput,
                 game_id:       Any,
                 config_path:   Optional[pathlib.Path]     = None,
                 config_repo:   Optional['BaseRepository'] = None,
                 config_serdes: Optional['BaseSerdes']     = None) -> None:
        '''
        Create a Configuration object for the game's set-up.

        `rules_dotted` is the veredi dotted label of the game's rules type.
          example: 'veredi.rules.d20.pf2.game'

        `game_id` is the Repository id/key/record-name for the game's Saved
        records.

        `config_repo` and `config_serdes` are the repository and serdes to use
        for the games' Definitions and Saved records.

        `config_path` is an optional override of the default_path() used to
        find the general Veredi configuration data.

        Raises LoadError and ConfigError
        '''
        log.start_up(self.dotted(),
                     "Creating Configuration...")
        self._define_vars()

        # ---
        # Params
        # ---
        self._rules = label.normalize(rules)
        self._id = game_id
        log.start_up(self.dotted(),
                     "Creating Configuration for: "
                     f"rules: '{self._rules}', game-id: '{self._id}'...")

        self._path = config_path or default_path()
        log.start_up(self.dotted(),
                     "Configuration path (using {}): {}",
                     ('provided' if config_path else 'default'),
                     self._path)

        try:
            # ---
            # NOTE:
            # Config's Repo & Serdes are not the game's repo/serdes. Ours are
            # used for loading the config data itself, and so:
            #   1) Can't rely on config data to configure themselves.
            #   2) Are the type for loading "this file (or data) exactly".
            # ---

            context = ConfigContext(self._path, self.dotted())

            # ---
            # Config Repository
            # ---
            # This will usually be a FileBareRepository created by us, but
            # allow it to be passed in.
            self._repo = config_repo
            if not self._repo:
                self._repo = FileBareRepository(context)
                log.start_up(self.dotted(),
                             "  Created config's repo: '{}'",
                             self._repo.dotted())
            else:
                log.start_up(self.dotted(),
                             "  Using passed in repo: '{}'",
                             self._repo.dotted())

            # ---
            # Config Serdes
            # ---
            # This will usually be a YamlSerdes created by us, but allow it to
            # be passed in.
            self._serdes = config_serdes
            if not self._serdes:
                self._serdes = YamlSerdes()
                log.start_up(self.dotted(),
                             "  Created config's serdes: '{}'",
                             self._serdes.dotted())
            else:
                log.start_up(self.dotted(),
                             "  Using passed in serdes: '{}'",
                             self._serdes.dotted())

            # ---
            # Background
            # ---
            # Do background stuff after repo/serdes so that they cannot try to
            # use us to make stuff from the config we haven't loaded yet.
            log.start_up(self.dotted(),
                         "Setting Configuration into background data...")

            # Set ourself into the background.
            background.config.init(self._path,
                                   self)
            self._set_background()
            log.start_up(self.dotted(),
                         "Configuration set into background data.")

        except Exception as err:
            log.start_up(self.dotted(),
                         "Configuration failed to initialize... Erroring out.",
                         log_success=False)
            raise log.exception(ConfigError,
                                "Found an exception when creating config."
                                ) from err

        # ---
        # Finalize: Load & Set-Up Configuration
        # ---
        log.start_up(self.dotted(),
                     "Configuration final load, set-up...")
        self._load()
        self._set_up()

        log.start_up(self.dotted(),
                     "Done initializing Configuration.",
                     log_success=True)

    # -------------------------------------------------------------------------
    # Properties: Generic
    # -------------------------------------------------------------------------

    @classmethod
    def dotted(klass: 'Configuration') -> str:
        '''
        Veredi dotted name for this class.
        '''
        return klass._DOTTED_NAME

    # -------------------------------------------------------------------------
    # Load Config Stuff
    # -------------------------------------------------------------------------

    def _load(self) -> VerediHealth:
        '''
        Load our configuration data from its file.

        Raises LoadError
        '''
        log_groups = [log.Group.START_UP, log.Group.DATA_PROCESSING]
        log.group_multi(log_groups,
                        self.dotted(),
                        "Configuration load...")

        # Spawn a context from what we know, and ask the config repo to load
        # something based on that.
        ctx = DataBareContext(self.dotted(),
                              ConfigContext.KEY,
                              self._path,
                              DataAction.LOAD)
        log.group_multi(log_groups,
                        self.dotted(),
                        "Configuration loading from repo...")
        with self._repo.load(ctx) as stream:
            # Decode w/ serdes.
            # Can raise an error - we'll let it.
            try:
                log.group_multi(log_groups,
                                self.dotted(),
                                "Configuration deserializing with serdes...")
                log.debug("Config Load Context: {}, "
                          "Confgig Repo: {}, "
                          "Confgig Serdes: {}",
                          ctx, self._repo, self._serdes)
                for each in self._serdes.deserialize_all(stream, ctx):
                    log.debug("Config Loading Doc: {}", each)
                    self._load_doc(each)

            except LoadError as error:
                log.group_multi(log_groups,
                                self.dotted(),
                                "Configuration load/deserialization failed "
                                "with a LoadError. Erroring out.",
                                log_success=False)
                # Log exception and let bubble up as-is.
                raise log.exception(
                    error,
                    "Configuration init load/deserialization failed "
                    "with a LoadError:  type: {}, str: {}",
                    type(error), str(error))

            except Exception as error:
                log.group_multi(log_groups,
                                self.dotted(),
                                "Configuration load/deserialization failed "
                                "with an error of type {}. Erroring out.",
                                type(error),
                                log_success=False)
                # Complain that we found an exception we don't handle.
                # ...then let it bubble up as-is.
                raise log.exception(
                    LoadError,
                    "Unhandled exception! type: {}, str: {}",
                    type(error), str(error)) from error

        return VerediHealth.HEALTHY

    def _load_doc(self, document: 'DeserializeTypes') -> None:
        '''
        Load each document from our config file int our config data.

        Raises LoadError
        '''
        log_groups = [log.Group.START_UP, log.Group.DATA_PROCESSING]
        log.group_multi(log_groups,
                        self.dotted(),
                        "Configuration loading document...")

        if isinstance(document, list):
            log.group_multi(log_groups,
                            self.dotted(),
                            "Configuration loaded a list instead of a dict?! "
                            "Erroring out.",
                            log_success=False)
            raise log.exception(
                LoadError,
                "TODO: How do we deal with list document? {}: {}",
                type(document),
                str(document))

        elif (isinstance(document, dict)
              and Hierarchy.VKEY_DOC_TYPE in document):
            # Save these to our config dict under their doc-type key.
            doc_type_str = document[Hierarchy.VKEY_DOC_TYPE]
            doc_type = Document.get(doc_type_str)
            log.group_multi(log_groups,
                            self.dotted(),
                            "Configuration loaded doc_type: {}",
                            doc_type_str)
            self._config[doc_type] = document

        else:
            log.group_multi(log_groups,
                            self.dotted(),
                            "Configuration cannot load unknow document. "
                            "Erroring out.",
                            log_success=False)
            raise log.exception(
                LoadError,
                "Unknown document while loading! "
                "Does it have a '{}' field? "
                "{}: {}",
                Hierarchy.VKEY_DOC_TYPE,
                type(document),
                str(document))

    def _set_up(self) -> VerediHealth:
        '''
        Sanity checks before loading, and any additional set-up required after
        initialization.

        Raises ConfigError
        '''
        # TODO: Move creation of our repo/serdes here?

        log.start_up(self.dotted(),
                     "Configuration set-up...")
        if not self._path:
            log.start_up(self.dotted(),
                         "Configuration set-up: No path! Erroring out...",
                         log_success=False)
            raise log.exception(
                ConfigError,
                "No path for config data after loading!")

        if not self._serdes:
            log.start_up(self.dotted(),
                         "Configuration set-up: No Serdes! Erroring out...",
                         log_success=False)
            raise log.exception(
                ConfigError,
                "No serdes for config data after loading!")

        if not self._repo:
            log.start_up(self.dotted(),
                         "Configuration set-up: No Repository! "
                         "Erroring out...",
                         log_success=False)
            raise log.exception(
                ConfigError,
                "No repository for config data after loading!")

        log.start_up(self.dotted(),
                     "Done setting up Configuration.",
                     log_success=True)
        return VerediHealth.HEALTHY

    # -------------------------------------------------------------------------
    # Context Properties/Methods
    # -------------------------------------------------------------------------

    def make_config_context(self):
        '''
        Returns a generic config context.
        '''
        context = ConfigContext(self._path,
                                self.dotted(),
                                id=self._id)
        return context

    def _set_background(self):
        '''
        Sets our config info into the background context.
        '''
        self._bg = {
            'dotted': self.dotted(),
        }
        background.config.set(background.Name.CONFIG,
                              self._bg,
                              background.Ownership.SHARE)

        # Set config's repo/serdes too.
        bg_data, bg_owner = (self._repo.background
                             if self._repo else
                             (None, background.Ownership.SHARE))
        background.config.set(background.Name.REPO,
                              bg_data,
                              bg_owner)
        bg_data, bg_owner = (self._serdes.background
                             if self._serdes else
                             (None, background.Ownership.SHARE))
        background.config.set(background.Name.SERDES,
                              bg_data,
                              bg_owner)

    # -------------------------------------------------------------------------
    # Registry Mediation
    # -------------------------------------------------------------------------
    def get_registered(self,
                       dotted_str: str,
                       *args:      Any,
                       context:    Optional['VerediContext'] = None,
                       **kwargs:   Any) -> Any:
        '''
        Mediator between any systems that don't care about any deep knowledge
        of veredi basics. Pass in a 'dotted' registration string, like:
        "veredi.rules.d11.health", and we will ask our registry to pass it back
        to the caller.

        Context is not required - will be included in errors/exceptions.

        Catches all exceptions and reraises all (non-VerediErrors wrapped as
        `ConfigError from error`).
        '''
        if not dotted_str:
            raise log.exception(
                ConfigError,
                "Need a dotted_str in order to get anything from registry. "
                "dotted_str: {}, args: {}, kwargs: {}, context: {}",
                dotted_str, args, kwargs, context
            )

        try:
            retval = registry.get(dotted_str,
                                  context,
                                  *args,
                                  **kwargs)
        except VerediError:
            # Ignore these and subclasses - bubble up.
            raise
        except Exception as error:
            raise log.exception(
                ConfigError,
                "Configuration could not get '{}'. "
                "args: {}, kwargs: {}, context: {}",
                dotted_str, args, kwargs, context
            ) from error

        return retval

    def create_from_label(self,
                          dotted_str: label.DotStr,
                          # Leave (k)args for people who are not me...
                          *args:      Any,
                          context:    Optional['VerediContext'] = None,
                          **kwargs:   Any) -> Any:
        '''
        Mediator between any game systems that don't care about any deep
        knowledge of veredi basics. Pass in a 'dotted' registration string,
        like: "veredi.rules.d11.health", and we will ask our registry to create
        it.

        Catches all exceptions and rewraps outside errors in a VerediError.
        '''
        try:
            retval = registry.create(dotted_str,
                                     context,
                                     *args,
                                     **kwargs)
        except VerediError:
            # Ignore these and subclasses - bubble up.
            raise
        except Exception as error:
            raise log.exception(
                ConfigError,
                "Configuration could not create '{}'. "
                "args: {}, kwargs: {}",
                dotted_str, args, kwargs,
                context=context
            ) from error

        return retval

    def create_from_config(self,
                           *keychain: label.LabelInput,
                           context:   Optional['VerediContext'] = None,
                           ) -> Nullable[Any]:
        '''
        Gets value from these keychain in our config data, then tries to have
        our registry create that value.

        e.g. config.create_from_config('data', 'game', 'repository')
           -> from config file: 'veredi.repository.file-tree'
              -> from create_from_label('veredi.repository.file-tree', ...)
                 -> FileTreeRepository object

        Will use provided context, or create a ConfigContext to use via
        `make_config_context()` if none provided.

        Returns thing created using keychain or None.
        '''
        # Ensure the keychain is in good shape from whatever was passed in.
        keychain = label.regularize(*keychain)
        config_val = self.get(*keychain)
        if not isinstance(config_val, str):
            error_info = ("no config value"
                          if not config_val else
                          "incorrect config value of type "
                          f"'{type(config_val)}' (need str)")
            log.debug("Make requested for: {}. But we have {} "
                      "for that. context: {}",
                      error_info, keychain, context)
            return Null()

        if not context:
            context = self.make_config_context()

        context.add(ConfigContext.Link.KEYCHAIN, list(keychain[:-1]))
        log.debug("Make requested for: {}. context: {}",
                  keychain, context)

        # Assume their relevant data is one key higher up...
        # e.g. if we're making the thing under keychain (GAME, REPO, TYPE),
        # then the repository we're making will want (GAME, REPO) as its
        # root so it can get, say, DIRECTORY.
        ret_val = self.create_from_label(config_val,
                                         context=context)
        log.debug("Made: {} from {}. context: {}", ret_val, keychain, context)
        return ret_val

    # -------------------------------------------------------------------------
    # Config Data
    # -------------------------------------------------------------------------

    def get_data(self,
                 *keychain: label.LabelInput) -> Nullable[Any]:
        '''
        Get a configuration thingy from us given some keychain use to walk into
        our config data in 'data' entry.

        Returns data found at end keychain.
        Returns None if couldn't find a key in our config data.
        '''
        # Ensure the keychain is in good shape from whatever was passed in.
        keychain = label.regularize(*keychain)

        data = self.get('data', *keychain)

        log.data_processing(self.dotted(),
                            'get_data: keychain: {} -> data: {}',
                            keychain, data,
                            log_minimum=log.Level.DEBUG)

        return data

    def get(self,
            *keychain: label.LabelInput) -> Nullable[Any]:
        '''
        Get a configuration thingy from us given some keychain use to walk into
        our config data.

        Returns data found at end keychain.
        Returns None if couldn't find a key in our config data.
        '''
        # Ensure the keychain is in good shape from whatever was passed in.
        keychain = label.regularize(*keychain)

        data = self.get_by_doc(Document.CONFIG,
                               *keychain)

        log.data_processing(self.dotted(),
                            'get: doc: {}, keychain: {} -> data: {}',
                            Document.CONFIG, keychain, data,
                            log_minimum=log.Level.DEBUG)

        return data

    def get_by_doc(self,
                   doc_type:  Document,
                   *keychain: label.LabelInput) -> Nullable[Any]:
        '''
        Get value of `keychain` from `doc_type`.

        Raises a ConfigError if invalid `doc_type` supplied.
        Returns Null() if `doc_type` doesn't exist or `keychain` isn't in it.
        '''
        # Ensure the keychain is in good shape from whatever was passed in.
        keychain = label.regularize(*keychain)

        log.data_processing(self.dotted(),
                            'get_by_doc: Getting doc: {}, keychain: {}...',
                            doc_type, keychain,
                            log_minimum=log.Level.DEBUG)

        hierarchy = Document.hierarchy(doc_type)
        if not hierarchy.valid(*keychain):
            log.data_processing(self.dotted(),
                                "get_by_doc: invalid document hierarchy for "
                                "doc: {}, keychain: {}...",
                                doc_type, keychain,
                                log_minimum=log.Level.DEBUG)
            raise log.exception(
                ConfigError,
                "Invalid keychain '{}' for {} document type. See its "
                "Hierarchy class for proper layout.",
                keychain, doc_type)

        # Get document type data first.
        doc_data = self._config.get(doc_type, None)
        data = doc_data
        if data is None:
            log.data_processing(self.dotted(),
                                "get_by_doc: No document type '{}' in "
                                "our config data: {}",
                                doc_type, self._config,
                                log_minimum=log.Level.DEBUG,
                                log_success=False)
            return Null()

        # Now hunt for the keychain they wanted...
        for key in keychain:
            data = data.get(key, None)
            if data is None:
                log.data_processing(self.dotted(),
                                    "get_by_doc: No data for key '{}' in "
                                    "keychain {} in our config "
                                    "document data: {}",
                                    key, keychain, doc_data,
                                    log_minimum=log.Level.DEBUG,
                                    log_success=False)
                return Null()

        log.data_processing(self.dotted(),
                            "get_by_doc: Got data for {} in "
                            "keychain {}. Data: {}",
                            doc_type, keychain, data,
                            log_minimum=log.Level.DEBUG,
                            log_success=True)
        return data

    def rules(self, context: 'VerediContext') -> Nullable[RulesGame]:
        '''
        Creates and returns the proper RulesGame object for this specific game
        with its game definition and saved data.

        Raises a ConfigError if no rules label or game id.
        '''
        log_groups = [log.Group.START_UP, log.Group.DATA_PROCESSING]
        log.group_multi(log_groups,
                        self.dotted(),
                        "rules: Creating game rules object "
                        "from rules: {}, id: {}",
                        self._rules, self._id)

        # ---
        # Sanity
        # ---
        if not self._rules or not self._id:
            log.group_multi(log_groups,
                            self.dotted(),
                            "rules: Failed to create game rules... missing "
                            "our rules or id: rules {}, id: {}",
                            self._rules, self._id,
                            log_success=False)
            raise log.exception(
                ConfigError,
                "No rules label or id for game; cannot create the "
                "RulesGame object. rules: {}, id: {}",
                self._rules, self._id)

        # ---
        # Context
        # ---
        # Allow something else if the caller wants, but...
        if not context:
            # ...this default w/ rules/id should be good in most cases.
            context = ConfigContext(self._path,
                                    self.dotted(),
                                    key=self._rules,
                                    id=self._id)

        # ---
        # Create the rules.
        # ---
        rules = self.create_from_label(
            # '<rules-dotted>.game' is our full dotted string.
            label.normalize(self._rules, 'game'),
            context=context)
        log.group_multi(log_groups,
                        self.dotted(),
                        "rules: Created game rules.",
                        log_success=True)
        return rules

    # -------------------------------------------------------------------------
    # Unit Testing
    # -------------------------------------------------------------------------

    def ut_inject(self,
                  value:     Any,
                  doc_type:  Document,
                  *keychain: label.LabelInput) -> None:
        # Ensure the keychain is in good shape from whatever was passed in.
        keychain = label.regularize(*keychain)

        # Get document type data first.
        doc_data = self._config.get(doc_type, None)
        data = doc_data
        if data is None:
            log.debug("No doc_type {} in our config data {}.",
                      doc_type, self._config)
            return None

        # Now hunt for/create the keychain they wanted...
        for key in keychain[:-1]:
            data = data.setdefault(key, {})

        # And set the key.
        data[keychain[-1]] = value
