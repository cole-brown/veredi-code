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
from veredi.base            import label
from veredi.base.exceptions import VerediError
from veredi.data.context    import DataAction, DataBareContext
from veredi.base.const      import VerediHealth
from veredi.rules.game      import RulesGame

from ..                     import background
from ..                     import exceptions
from .                      import registry
from .hierarchy             import Document, Hierarchy
from .context               import ConfigContext


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

        self._rules: label.Dotted = None
        '''
        The game's dotted label for the rules.
        '''

        self._id: str = None
        '''
        The game's repository id/key/record-name string.
        '''

    def __init__(self,
                 rules:         label.Label,
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
        self._define_vars()

        self._rules = label.normalize(rules)
        self._id = game_id

        self._path = config_path or default_path()

        try:
            # Setup our context, import repo & serdes's.
            # Also includes a handy back-link to this Configuration.
            background.config.init(self._path,
                                   self)

            # TODO: Always get this from config file.
            # Avoid a circular import
            self._repo = config_repo
            if not self._repo:
                from ..repository.file import FileBareRepository
                self._repo = FileBareRepository(Null())

            # TODO: Always get this from config file.
            # Avoid a circular import
            self._serdes = config_serdes
            if not self._serdes:
                from ..serdes.yaml import serdes
                self._serdes = serdes.YamlSerdes(Null())

            self._set_background()

        except Exception as err:
            raise log.exception(exceptions.ConfigError,
                                "Found an exception when creating config."
                                ) from err

        self._load()
        self._set_up()

    # -------------------------------------------------------------------------
    # Context Properties/Methods
    # -------------------------------------------------------------------------

    def make_config_context(self):
        '''
        Returns a generic config context.
        '''
        context = ConfigContext(self._path,
                                self._DOTTED_NAME,
                                id=self._id)
        return context

    def _set_background(self):
        '''
        Sets our config info into the background context.
        '''
        self._bg = {
            'dotted': self._DOTTED_NAME,
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
                       *args: Any,
                       context: Optional['VerediContext'] = None,
                       **kwargs: Any) -> Any:
        '''
        Mediator between any systems that don't care about any deep knowledge
        of veredi basics. Pass in a 'dotted' registration string, like:
        "veredi.rules.d11.health", and we will ask our registry to pass it back
        to the caller.

        Context is not required - will be included in errors/exceptions.

        Catches all exceptions and rewraps outside errors in a VerediError.
        '''
        if not dotted_str:
            raise log.exception(
                exceptions.ConfigError,
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
                exceptions.ConfigError,
                "Configuration could not get '{}'. "
                "args: {}, kwargs: {}, context: {}",
                dotted_str, args, kwargs, context
            ) from error

        return retval

    def create_registered(self,
                          dotted_str: str,
                          # Leave (k)args for people who are not me...
                          context: Optional['VerediContext'],
                          *args: Any,
                          **kwargs: Any) -> Any:
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
                exceptions.ConfigError,
                "Configuration could not create '{}'. "
                "args: {}, kwargs: {}, context: {}",
                dotted_str, args, kwargs, context
            ) from error

        return retval

    def make(self,
             context:   Optional['VerediContext'],
             *keychain: str) -> Nullable[Any]:
        '''
        Gets value from these keychain in our config data, then tries to have
        our registry create that value.

        e.g. config.make('data', 'game', 'repository')

        Returns thing created using keychain or None.
        '''
        config_val = self.get(*keychain)
        if config_val is None:
            log.debug("Make requested for: {}. But we have no config "
                      "value for that. context: {}",
                      keychain, context)
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
        ret_val = self.create_registered(config_val,
                                         context)
        log.debug("Made: {} from {}. context: {}", ret_val, keychain, context)
        return ret_val

    # -------------------------------------------------------------------------
    # Config Data
    # -------------------------------------------------------------------------

    def get_data(self,
                 *keychain: str) -> Nullable[Any]:
        '''
        Get a configuration thingy from us given some keychain use to walk into
        our config data in 'data' entry.

        Returns data found at end keychain.
        Returns None if couldn't find a key in our config data.
        '''
        return self.get('data',
                        *keychain)

    def get(self,
            *keychain: str) -> Nullable[Any]:
        '''
        Get a configuration thingy from us given some keychain use to walk into
        our config data.

        Returns data found at end keychain.
        Returns None if couldn't find a key in our config data.
        '''
        return self.get_by_doc(Document.CONFIG,
                               *keychain)

    def get_by_doc(self,
                   doc_type:  Document,
                   *keychain: str) -> Nullable[Any]:

        hierarchy = Document.hierarchy(doc_type)
        if not hierarchy.valid(*keychain):
            raise log.exception(
                exceptions.ConfigError,
                "Invalid keychain '{}' for {} document type. See its "
                "Hierarchy class for proper layout.",
                keychain, doc_type)

        # Get document type data first.
        doc_data = self._config.get(doc_type, None)
        data = doc_data
        if data is None:
            log.debug("No doc_type {} in our config data {}.",
                      doc_type, self._config)
            return Null()

        # Now hunt for the keychain they wanted...
        for key in keychain:
            data = data.get(key, None)
            if data is None:
                log.debug("No data for key {} in keychain {} "
                          "in our config data {}.",
                          key, keychain, doc_data)
                return Null()

        return data

    # TODO: move _set_up() and _load() (and more?) up to init section

    # -------------------------------------------------------------------------
    # Load Config Stuff
    # -------------------------------------------------------------------------

    # TODO [2020-05-06]: Change data into stuff we can use.
    # Classes and suchlike...
    def _set_up(self) -> VerediHealth:
        '''Raises ConfigError'''

        if not self._path:
            raise log.exception(
                exceptions.ConfigError,
                "No path for config data after loading!")

        if not self._serdes:
            raise log.exception(
                exceptions.ConfigError,
                "No serdes for config data after loading!")

        if not self._repo:
            raise log.exception(
                exceptions.ConfigError,
                "No repository for config data after loading!")

        return VerediHealth.HEALTHY

    def _load(self) -> VerediHealth:
        '''
        Load our context data so we know what the ever to do.

        Raises LoadError
        '''
        # Spawn a context from what we know, and ask the config repo to load
        # something based on that.
        ctx = DataBareContext(self._DOTTED_NAME,
                              ConfigContext.KEY,
                              self._path,
                              DataAction.LOAD)
        with self._repo.load(ctx) as stream:
            # Decode w/ serdes.
            # Can raise an error - we'll let it.
            try:
                log.debug("Config Load Context: {}, "
                          "Confgig Repo: {}, "
                          "Confgig Serdes: {}",
                          ctx, self._repo, self._serdes)
                for each in self._serdes.deserialize_all(stream, ctx):
                    log.debug("Config Loading Doc: {}", each)
                    self._load_doc(each)

            except exceptions.LoadError:
                # Let this one bubble up as-is.
                raise
            except Exception as error:
                # Complain that we found an exception we don't handle.
                # ...then let it bubble up as-is.
                raise log.exception(
                    VerediError,
                    "Unhandled exception! type: {}, str: {}",
                    type(error), str(error)) from error

        return VerediHealth.HEALTHY

    def _load_doc(self, document: 'DeserializeTypes') -> None:
        if isinstance(document, list):
            raise log.exception(
                exceptions.LoadError,
                "TODO: How do we deal with list document? {}: {}",
                type(document),
                str(document))

        elif (isinstance(document, dict)
              and Hierarchy.VKEY_DOC_TYPE in document):
            # Save these to our config dict under their doc-type key.
            doc_type_str = document[Hierarchy.VKEY_DOC_TYPE]
            doc_type = Document.get(doc_type_str)
            self._config[doc_type] = document

        else:
            raise log.exception(
                exceptions.LoadError,
                "Unknown document while loading! "
                "Does it have a '{}' field? "
                "{}: {}",
                Hierarchy.VKEY_DOC_TYPE,
                type(document),
                str(document))

    def rules(self, context: 'VerediContext') -> Nullable[RulesGame]:
        '''
        Creates and returns the proper RulesGame object for this specific game
        with its game definition and saved data.

        Raises a ConfigError if no rules label or game id.
        '''
        # ---
        # Sanity
        # ---
        if not self._rules or not self._id:
            raise log.exception(
                exceptions.ConfigError,
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
                                    self._DOTTED_NAME,
                                    key=self._rules,
                                    id=self._id)

        # ---
        # Create the rules.
        # ---
        rules = self.create_registered(
            # '<rules-dotted>.game' is our full dotted string.
            label.normalize(self._rules, 'game'),
            context)
        return rules

    # -------------------------------------------------------------------------
    # Unit Testing
    # -------------------------------------------------------------------------

    def ut_inject(self,
                  value:     Any,
                  doc_type:  Document,
                  *keychain: str) -> None:
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
