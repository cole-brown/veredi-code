# coding: utf-8

'''
Configuration file reader/writer for Veredi games.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
import os
import re

# Our Stuff
from veredi.logger import log
from .. import exceptions
from ..format.yaml import yaml
from ..format.yaml.document import DocMetadata, DocRepository
from ..repository.manager import Manager
from . import registry


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_NAME = "default.yaml"


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def default_path():
    '''Returns absolute path to the DEFAULT config file.

    Returns None if file does not exist.

    '''
    path = os.path.join(THIS_DIR, DEFAULT_NAME)
    if not os.path.exists(path):
        return None

    return path


class Configuration:
    '''Raises LoadError and ConfigError...'''
    def __init__(self, config_path=None, data_format=None):
        '''Raises LoadError and ConfigError'''
        self._path = config_path or default_path()
        self._data_format = data_format or yaml.YamlFormat()

        self._load()
        self._set_up()

    # §-TODO-§ [2020-05-06]: Change data into stuff we can use.
    # Classes and suchlike...
    def _set_up(self):
        self._set_up_repos()

    def _set_up_repos(self):
        '''Raises ConfigError'''

        if not self._data_repo:
            raise exceptions.ConfigError(
                "No repository config data after loading!",
                None,
                self.to_context())

        owner = None # self._set_up_repo('owner')
        campaign = None # self._set_up_repo('campaign')
        session = None # self._set_up_repo('session')
        player = self._set_up_repo('player')
        self.repository = Manager(owner, campaign, session, player)

    def _set_up_repo(self, kind):
        try:
            data = getattr(self._data_repo, kind)
        except AttributeError as error:
            log.exception(
                error,
                "Repo Config Data has no attribute '{}'! data: {}",
                kind, self._data_repo)
            raise exceptions.ConfigError(
                "Data has no attribute '{}'! data: {}",
                error,
                self.to_context()) from error

        try:
            # required
            dotted_key_fmt = data['format']
            dotted_key_repo = data['type']

            # optional
            directory = data.get('directory', None)
        except KeyError as error:
            log.exception(
                error,
                "Repo Config Data missing important key '{}'! data: {}",
                kind, data)
            raise exceptions.ConfigError(
                "Data has no attribute '{}'! data: {}",
                error,
                self.to_context()) from error

        # Replace any $this vars...
        dotted_key_fmt = self._var_sub(dotted_key_fmt, kind)
        dotted_key_repo = self._var_sub(dotted_key_repo, kind)

        formatter  = registry.create(dotted_key_fmt)
        repository = registry.create(dotted_key_repo,
                                     directory,
                                     data_format=formatter)
        return repository

    def _var_sub(self, string, replacement):
        '''
        Replace shell-style variables ($name or ${name}) with their value.
        '''
        return re.sub(r'\$\{?this\}?', replacement, string)

    def _load(self):
        '''Raises LoadError'''
        with open(self._path, 'r') as file_obj:
            # Can raise an error - we'll let it.
            try:
                log.debug(f"data format: {self._data_format}")
                generator = self._data_format.load_all(file_obj,
                                                       self._to_context())
                for each in generator:
                    log.debug("loading doc: {}", each)
                    self._load_doc(each)
            except exceptions.LoadError:
                # Let this one bubble up as-is.
                data = None
                raise
            except Exception as error:
                # Complain that we found an exception we don't handle.
                # ...then let it bubble up as-is.
                log.exception(error, "Unhandled exception! type: {}, str: {}",
                              type(error), str(error))
                data = None
                raise

    def _load_doc(self, document):
        if isinstance(document, DocMetadata):
            self._data_meta = document
        elif isinstance(document, DocRepository):
            self._data_repo = document
        else:
            log.error("Unknown document while loading! {}: {}",
                      type(document),
                      str(document))
            raise exceptions.LoadError(f"Unknown document while loading! "
                                       f"{type(document)}: {str(document)}",
                                       None,
                                       self.to_context(document=document))

    def _to_context(self, **context):
        '''Convert useful info we have for loading into a context object in case
        an error needs to throw itself off a cliff.

        '''
        context['config_path'] = self._path
        context['data_format'] = self._data_format.__class__.__name__
        return context
