# coding: utf-8

'''
Configuration file reader/writer for Veredi games.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Dict, Optional, Any, List
import pathlib
import re
import enum

from veredi.logger          import log
from veredi.base.exceptions import VerediError
from veredi.base.context    import VerediContext, EphemerealContext
from veredi.data.context    import DataBareContext
from .context               import ConfigContext
from veredi.base.const      import VerediHealth

from .. import exceptions
from .  import registry
from .hierarchy import Document, Hierarchy, MetadataHierarchy, ConfigHierarchy


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

THIS_DIR = pathlib.Path(__file__).resolve().parent
DEFAULT_NAME = "default.yaml"


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

    def __init__(self,
                 config_path:  Optional[pathlib.Path]   = None,
                 config_repo:  Optional['BaseRepository'] = None,
                 config_codec: Optional['BaseCodec']      = None):
        '''Raises LoadError and ConfigError'''
        self._path = config_path or default_path()

        # Our storage of the config data itself.
        self._config = {}

        try:
            # Setup our context, import repo & codec's.
            # Also includes a handy back-link to this Configuration.
            self._context = ConfigContext(self._path,
                                          self)

            # Avoid a circular import
            self._repo = config_repo
            if not self._repo:
                from ..repository.file import FileBareRepository
                self._repo = FileBareRepository(self._context)

            # Avoid a circular import
            self._codec = config_codec
            if not self._codec:
                from ..codec.yaml import codec
                self._codec = codec.YamlCodec(self._context)

            self._context.finish_init(self._repo.context,
                                      self._codec.context)
        except Exception as e:
            raise log.exception(e,
                                VerediError,
                                "Found an exception when creating...") from e

        self._load()
        self._set_up()

    # --------------------------------------------------------------------------
    # Context Properties/Methods
    # --------------------------------------------------------------------------

    @property
    def context(self):
        '''
        Will be the context dict for e.g. Events, Errors.
        '''
        return self._context

    # --------------------------------------------------------------------------
    # Registry Mediation
    # --------------------------------------------------------------------------
    def get_registered(self,
                       dotted_str: str,
                       *args: Any,
                       context: Optional[VerediContext] = None,
                       **kwargs: Any) -> Any:
        '''
        Mediator between any systems that don't care about any deep knowledge of
        veredi basics. Pass in a 'dotted' registration string, like:
        "veredi.rules.d11.health", and we will ask our registry to pass it back
        to the caller.

        Context is not required - will be included in errors/exceptions.

        Catches all exceptions and rewraps outside errors in a VerediError.
        '''
        if not dotted_str:
            raise log.exception(
                None,
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
                error,
                exceptions.ConfigError,
                "Configuration could not get '{}'. "
                "args: {}, kwargs: {}, context: {}",
                dotted_str, args, kwargs, context
            ) from error

        return retval

    def create_registered(self,
                          dotted_str: str,
                          # Leave (k)args for people who are not me...
                          context: Optional[VerediContext],
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
                error,
                exceptions.ConfigError,
                "Configuration could not create '{}'. "
                "args: {}, kwargs: {}, context: {}",
                dotted_str, args, kwargs, context
            ) from error

        return retval

    def make(self,
             context:   Optional[VerediContext],
             *keychain: str) -> Optional[Any]:
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
            return None

        if not context:
            context = self.context.spawn(EphemerealContext,
                                         self.context.name,
                                         self.context.key)
        else:
            context.pull(self.context)

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

    # --------------------------------------------------------------------------
    # Config Data
    # --------------------------------------------------------------------------

    def get_data(self,
                 *keychain: str) -> Optional[Any]:
        '''
        Get a configuration thingy from us given some keychain use to walk into
        our config data in 'data' entry.

        Returns data found at end keychain.
        Returns None if couldn't find a key in our config data.
        '''
        return self.get('data',
                        *keychain)

    def get_rules(self,
                  *keychain: str) -> Optional[Any]:
        '''
        Get a configuration thingy from us given some keychain use to walk into
        our config data in 'rules' entry.

        Returns data found at end keychain.
        Returns None if couldn't find a key in our config data.
        '''
        return self.get('rules',
                        *keychain)

    def get(self,
            *keychain: str) -> Optional[Any]:
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
                   *keychain: str) -> Optional[Any]:

        hierarchy = Document.hierarchy(doc_type)
        if not hierarchy.valid(*keychain):
            raise log.exception(
                None,
                exceptions.ConfigError,
                "Invalid keychain '{}' for {} document type. See its Hierarchy "
                "class for proper layout.",
                keychain, doc_type)

        # Get document type data first.
        doc_data = self._config.get(doc_type, None)
        data = doc_data
        if data is None:
            log.debug("No doc_type {} in our config data {}.",
                      doc_type, self._config)
            return None

        # Now hunt for the keychain they wanted...
        for key in keychain:
            data = data.get(key, None)
            if data is None:
                log.debug("No data for key {} in keychain {} "
                          "in our config data {}.",
                          key, keychain, doc_data)
                return None

        return data

    # --------------------------------------------------------------------------
    # Load Config Stuff
    # --------------------------------------------------------------------------

    # Â§-TODO-Â§ [2020-05-06]: Change data into stuff we can use.
    # Classes and suchlike...
    def _set_up(self) -> VerediHealth:
        '''Raises ConfigError'''

        if not self._path:
            raise exceptions.ConfigError(
                "No path for config data after loading!",
                None,
                self.context)

        if not self._codec:
            raise exceptions.ConfigError(
                "No codec for config data after loading!",
                None,
                self.context)

        if not self._repo:
            raise exceptions.ConfigError(
                "No repository for config data after loading!",
                None,
                self.context)

        return VerediHealth.HEALTHY

    def _load(self) -> VerediHealth:
        '''
        Load our context data so we know what the ever to do.

        Raises LoadError
        '''
        # Spawn a context from what we know, and ask the config repo to load
        # something based on that.
        ctx = self.context.spawn(DataBareContext,
                                 self.context.name,
                                 self.context.key,
                                 self._path)
        with self._repo.load(ctx) as stream:
            # Decode w/ codec.
            # Can raise an error - we'll let it.
            try:
                log.debug("Config Load Context: {}, "
                          "Confgig Repo: {}, "
                          "Confgig Codec: {}",
                          ctx, self._repo, self._codec)
                for each in self._codec.decode_all(stream, ctx):
                    log.debug("Config Loading Doc: {}", each)
                    self._load_doc(each)

            except exceptions.LoadError:
                # Let this one bubble up as-is.
                data = None
                raise
            except Exception as error:
                data = None
                # Complain that we found an exception we don't handle.
                # ...then let it bubble up as-is.
                raise log.exception(
                    error,
                    VerediError,
                    "Unhandled exception! type: {}, str: {}",
                    type(error), str(error)) from error

        return VerediHealth.HEALTHY

    def _load_doc(self, document: 'codec.CodecOutput') -> None:
        if isinstance(document, list):
                raise log.exception(
                    error,
                    exceptions.LoadError,
                    "TODO: How do we deal with list document? {}: {}",
                    type(document),
                    str(document),
                    context=self.context)

        elif (isinstance(document, dict)
              and Hierarchy.VKEY_DOC_TYPE in document):
            # Save these to our config dict under their doc-type key.
            doc_type_str = document[Hierarchy.VKEY_DOC_TYPE]
            doc_type = Document.get(doc_type_str)
            self._config[doc_type] = document

        else:
            raise log.exception(
                error,
                exceptions.LoadError,
                "Unknown document while loading! "
                "Does it have a '{}' field? "
                "{}: {}",
                Hierarchy.VKEY_DOC_TYPE,
                type(document),
                str(document),
                context=self.context)

    # --------------------------------------------------------------------------
    # Unit Testing
    # --------------------------------------------------------------------------

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
