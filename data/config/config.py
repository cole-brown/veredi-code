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

from veredi.logger import log
from veredi.base.exceptions import VerediError
from veredi.base.context import (VerediContext,
                                 PersistentContext,
                                 DataBareContext)
from veredi.base.const import VerediHealth

from .. import exceptions
from . import registry

from ..repository.base import BaseRepository

# For reading our config file:
from ..repository.file import FileBareRepository
from ..codec.base import BaseCodec, CodecOutput, CodecKeys, CodecDocuments
from ..codec.yaml import codec


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

THIS_DIR = pathlib.Path(__file__).resolve().parent
DEFAULT_NAME = "default.yaml"


@enum.unique
class ConfigKeys(enum.Enum):
    INVALID  = None

    # level 0
    GAME     = 'game'
    TEMPLATE = 'template'

    # level 1
    REPO     = 'repository'
    CODEC    = 'codec'
    DIR      = 'directory'

    # etc...

    def get(string: str) -> Optional['ConfigKeys']:
        '''
        Convert a string into a CodecDocuments enum value. Returns None if no
        conversion is found. Isn't smart - no case insensitivity or anything.
        Only compares input against our enum /values/.
        '''
        for each in CodecDocuments:
            if string == each.value:
                return each
        return None


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
                 config_repo:  Optional[BaseRepository] = None,
                 config_codec: Optional[BaseCodec]      = None):
        '''Raises LoadError and ConfigError'''
        self._path    = config_path or default_path()
        self._repo    = config_repo or FileBareRepository(self._path)
        self._codec   = config_codec or codec.YamlCodec()

        # Setup our context, import repo & codec's.
        self._context = PersistentContext('configuration', 'configuration')
        self._context.sub['path'] = str(self._path)
        self._context.import_to_sub(self._repo.context)
        self._context.import_to_sub(self._codec.context)

        # Our storage of the config data itself.
        self._config = {}

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
    def create_registered(self,
                          dotted_str: str,
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
                                     *args,
                                     context=context,
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

    # --------------------------------------------------------------------------
    # Config Data
    # --------------------------------------------------------------------------

    def get(self,
            doc_type: CodecDocuments,
            *keys:    ConfigKeys) -> Optional[Any]:
        '''
        Get a configuration thingy from us given some keys use to walk into our
        config data.

        Returns data found at end of doc_type, keys chain.
        Returns None if couldn't find doc_type or a key in our config data.
        '''
        # Get document type data first.
        data = self._config.get(doc_type, None)
        if data is None:
            return None

        # Now hunt for the keys they wanted...
        for key in keys:
            data = data.get(key, None)
            if data is None:
                return None

        return data

    # --------------------------------------------------------------------------
    # Load Config Stuff
    # --------------------------------------------------------------------------

    # §-TODO-§ [2020-05-06]: Change data into stuff we can use.
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
        ctx = self.context.spawn(DataBareContext, self._path)
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

    def _load_doc(self, document: codec.CodecOutput) -> None:
        if isinstance(document, list):
                raise log.exception(
                    error,
                    exceptions.LoadError,
                    "TODO: How do we deal with list document? {}: {}",
                    type(document),
                    str(document),
                    context=self.context)

        elif (isinstance(document, dict)
              and CodecKeys.DOC_TYPE.value in document):
            # Save these to our config dict under their doc-type key.
            doc_type_str = document[CodecKeys.DOC_TYPE.value]
            doc_type = CodecDocuments.get(doc_type_str)
            self._config[doc_type] = document

        else:
            raise log.exception(
                error,
                exceptions.LoadError,
                "Unknown document while loading! "
                "Does it have a '{}' field? "
                "{}: {}",
                CodecKeys.DOC_TYPE.value,
                type(document),
                str(document),
                context=self.context)
