# coding: utf-8

'''
Base Repository Pattern for load, save, etc. from
various backend implementations (db, file, etc).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, Dict, NewType, Iterable, Union, Optional, Callable, List

import pathlib
import os

import re
import hashlib
from io import StringIO, TextIOBase

import enum

from veredi.logger import log
from veredi.data.config.registry import register
from veredi.data.config.config import Configuration, ConfigKey

from veredi.base.context import VerediContext
from veredi.data.context import (DataBareContext,
                                 DataGameContext)
from veredi.data.config.context import ConfigContext

from veredi.data.codec.base import BaseCodec

from .. import exceptions
from . import base


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

PathType = NewType('PathType', Union[str, pathlib.Path])

# §-TODO-§ [2020-05-23]: other file repos...
#   FileTreeDiffRepository - for saving history for players


# File Tree:
#   <root>/
#     <campaign>/
#       <type>/
#         <stuff>/
#           <things>/
#             <file>.<ext>
#
# Example File Tree:
#   /var/veredi/data/file-tree/
#     forgotten_campaign/
#       players/
#         username/
#           player_name.ext
#       monsters/
#         session-id?/
#           monster_name.ext
#       items/
#         something to break 'em up.../
#           ring_of_honor.ext
#
# So... need... a tuple of junk.
#   type: int/enum -> str?
#   extra:
#     - players: user name, player name, campaign name?, file name?, ext
#     - monsters: monster name, campaign name?, session name?, file name?, ext
#     - items: category name, item name..., file name?, ext
#
# So... data request should have...
#   context = {
#       load-request: {
#           ...
#           type: DataGameContext.Type.PLAYERS,
#           campaign: 'forgotten campaign'
#           keys: ['user', 'player']
#           user: 'user jeff',
#           player: 'jeff the farmer lizardman',
#       }
#       ...
#   }
#   context = {
#       load-request: {
#           ...
#           type: DataGameContext.Type.MONSTERS,
#           campaign: 'forgotten campaign'
#           keys: ['family', 'monster']
#           family: 'dragon',
#           moster: 'aluminum dragon',
#       }
#       ...
#   }
#
# But I doubt I have that much info, do I?
#   Maybe? Could load all db keys for a game or something?
#
# Player load data from user object...
# Monster load data from... campaign/session/dm typing input?
# Item load data from...
#   - things that own the item?
#   - typing input?


# ---
# Path Safing Consts
# ---

_HUMAN_SAFE = re.compile(r'[^\w\d-]')
_REPLACEMENT = '_'


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# -------------------------------Just Functions.--------------------------------
# --                            Paths In General                              --
# ------------------------------------------------------------------------------

def pathlib_cast(str_or_path: PathType) -> pathlib.Path:
    return pathlib.Path(str_or_path)


# --------------------------------------------------------------------------
# Path Safing Option:
#   "us?#:er" -> "us___er"
# --------------------------------------------------------------------------
@register('veredi', 'sanitize', 'human', 'path-safe')
def to_human_readable(path: PathType) -> pathlib.Path:
    return pathlib_cast(_HUMAN_SAFE.sub(_REPLACEMENT,
                                        path))

# --------------------------------------------------------------------------
# Path Safing Option:
#   "us?#:er" ->
#     'b3b31a87f6cca2e4d8e7909395c4b4fd0a5ee73b739b54eb3aeff962697ca603'
# --------------------------------------------------------------------------
@register('veredi', 'sanitize', 'hashed', 'sha256')
def to_hashed(path: PathType) -> pathlib.Path:
    return pathlib_cast(hashlib.sha256(path.encode()).hexdigest())


# ----------------------------Bare File Repository------------------------------
# --                        Load a file specifically.                         --
# ------------------------------------------------------------------------------

@register('veredi', 'repository', 'file-bare')
class FileBareRepository(base.BaseRepository):

    _REPO_NAME   = 'file-bare'
    _CONTEXT_NAME = 'file-bare'
    _CONTEXT_KEY  = 'repository'

    def __init__(self,
                 config_context: Optional[ConfigContext] = None) -> None:
        # Bare context doesn't have a root until it loads something from
        # somewhere. Then that directory is its root.
        self._root = None

        super().__init__(self._REPO_NAME,
                         self._CONTEXT_NAME,
                         self._CONTEXT_KEY,
                         config_context)

    def _configure(self,
                   context: Optional[ConfigContext]) -> None:
        '''
        Allows repos to grab anything from the config data that they need to
        set up themselves.
        '''
        config = ConfigContext.config(context)
        if not config:
            raise ConfigContext.exception(
                context,
                None,
                "Cannot configure {} without a Configuration in the "
                "supplied context.",
                self.__class__.__name__)

        # Bare context doesn't have a root until it loads something from
        # somewhere. Then that directory is its root.
        self._root = None

        # Config probably isn't much set up right now. May need to
        # inject/partially-load something to see if we can get options into
        # here now...
        path_safing_fn = None
        path_safing = config.get(ConfigKey.GAME,
                                 ConfigKey.REPO,
                                 ConfigKey.SANITIZE)
        if path_safing:
            path_safing_fn = config.get_registered(path_safing,
                                                   context)
        self.fn_path_safing = path_safing_fn or to_human_readable

        log.debug("Set my root to: {}", self.root)
        log.debug("Set my path-safing to: {}", self.fn_path_safing)

    # --------------------------------------------------------------------------
    # Load Methods
    # --------------------------------------------------------------------------

    @property
    def root(self) -> pathlib.Path:
        '''
        Returns the root of the repository.
        '''
        log.debug("root is: {}", self._root)
        return self._root

    def load(self,
             context: DataBareContext) -> TextIOBase:
        '''
        Loads data from repository based on the context.

        Returns io stream.
        '''
        load_id = self._id(context)
        load_path = self._id_to_path(load_id, context)

        # load_path should be exact - no globbing.
        if not load_path.exists():
            raise exceptions.LoadError(
                f"Cannot load file. Path/file does not exist: {str(load_path)}",
                None,
                self.context.push(context))

        data_stream = None
        with load_path.open('r') as file_stream:
            # Can raise an error - we'll let it.
            try:
                data_stream = StringIO(file_stream.read(None))
            except exceptions.LoadError:
                # Let this one bubble up as-is.
                if data_stream and not data_stream.closed:
                    data_stream.close()
                data_stream = None
                raise
            except Exception as error:
                # Complain that we found an exception we don't handle.
                # ...then let it bubble up.
                if data_stream and not data_stream.closed:
                    data_stream.close()
                data_stream = None
                raise log.exception(
                    error,
                    LoadError,
                    "Error loading data from file. context: {}",
                    context=context) from error

        return data_stream

    # --------------------------------------------------------------------------
    # Identification ("Leeloo Dallas, Multi-Pass")
    # --------------------------------------------------------------------------

    def _id(self,
            context:     DataGameContext) -> pathlib.Path:
        '''
        Turns data repo keys in the context into an id we can use to retrieve
        the data. Keys are safe and ready to go.
        '''
        self._root = context.load.parent
        return context.load

    def _id_to_path(self,
                    load_id: PathType,
                    context: DataGameContext) -> None:
        '''
        Turn identity stuff into filepath components.
        '''
        return pathlib_cast(load_id)

    # --------------------------------------------------------------------------
    # Path Safing
    # --------------------------------------------------------------------------

    def _safe_path(self,
                   unsafe: PathType,
                   context: Optional[DataGameContext] = None) -> pathlib.Path:
        '''Makes `unsafe` safe with self.fn_path_safing. '''

        if not self.fn_path_safing:
            raise exceptions.LoadError(
                "No path safing function set! Cannot create file paths. ",
                None,
                self.context.push(context)) from error

        return self.fn_path_safing(unsafe)


# ----------------------------File Tree Repository------------------------------
# --       Load a file given context information and a base directory.        --
# ------------------------------------------------------------------------------

@register('veredi', 'repository', 'file-tree')
class FileTreeRepository(base.BaseRepository):

    _REPO_NAME   = 'file-tree'
    _CONTEXT_NAME = 'file-tree'
    _CONTEXT_KEY  = 'repository'

    # ---
    # Path Names
    # ---
    _HUMAN_SAFE = re.compile(r'[^\w\d-]')
    _REPLACEMENT = '_'

    def __init__(self,
                 context: Optional[VerediContext] = None) -> None:
        self._root = None

#        # Unit-test / override
#        if directory:
#            self._root = pathlib.Path(directory).resolve()

#        # Use user-defined or set to our default.
#        self.fn_path_safing = path_safing_fn or to_human_readable

        super().__init__(self._REPO_NAME,
                         self._CONTEXT_NAME,
                         self._CONTEXT_KEY,
                         context)

    def _configure(self,
                   context: Optional[ConfigContext]) -> None:
        '''
        Allows repos to grab anything from the config data that they need to
        set up themselves.
        '''
        config = ConfigContext.config(context) # Configuration obj
        if not config:
            raise ConfigContext.exception(
                context,
                None,
                "Cannot configure {} without a Configuration in the "
                "supplied context.",
                self.__class__.__name__)

        self._root = ConfigContext.path(context)
        self._root = self._root / pathlib_cast(config.get(ConfigKey.GAME,
                                                          ConfigKey.REPO,
                                                          ConfigKey.DIR))
        self._root = self._root.resolve()

        path_safing_fn = None
        path_safing = config.get(ConfigKey.GAME,
                                 ConfigKey.REPO,
                                 ConfigKey.SANITIZE)
        if path_safing:
            path_safing_fn = config.get_registered(path_safing,
                                                   context)
        self.fn_path_safing = path_safing_fn or to_human_readable

        log.debug("Set my root to: {}", self.root)
        log.debug("Set my path-safing to: {}", self.fn_path_safing)

    # --------------------------------------------------------------------------
    # Load Methods
    # --------------------------------------------------------------------------

    @property
    def root(self) -> pathlib.Path:
        '''
        Returns the root of the repository.
        '''
        log.debug("root is: {}", self._root)
        return self._root

    def load(self,
             context: DataGameContext) -> TextIOBase:
        '''
        Loads data from repository based on the context.

        Returns io stream.
        '''
        ids = self._id(context.type,
                       context)
        pattern_path = self._id_to_path(ids, context)

        # Use path to find a file match.
        directory = pattern_path.parent
        glob = pattern_path.name
        file_path = None
        for match in directory.glob(glob):
            if file_path is not None:
                raise exceptions.LoadError(
                    f"Too many matches for loading file by id: "
                    f"directory: {directory}, glob: {glob}, "
                    f"matches: {sorted(directory.glob(glob))}",
                    None,
                    self.context.push(context))
            file_path = match

        if file_path is None:
            raise exceptions.LoadError(
                f"Zero matches for loading file by id: "
                f"directory: {directory}, glob: {glob}, "
                f"matches: {sorted(directory.glob(glob))}",
                None,
                self.context.push(context))

        data_stream = None
        with file_path.open('r') as file_stream:
            # Can raise an error - we'll let it.
            try:
                data_stream = StringIO(file_stream.read(None))
            except exceptions.LoadError:
                # Let this one bubble up as-is.
                if data_stream and not data_stream.closed:
                    data_stream.close()
                data_stream = None
                raise
            except Exception as err:
                # Complain that we found an exception we don't handle.
                # ...then let it bubble up.
                if data_stream and not data_stream.closed:
                    data_stream.close()
                data_stream = None
                raise log.exception(
                    error,
                    LoadError,
                    "Error loading data from file. context: {}",
                    context=context) from error

        return data_stream

    # --------------------------------------------------------------------------
    # Identification ("Leeloo Dallas, Multi-Pass")
    # --------------------------------------------------------------------------

    def _id_accum(self, path: PathType, accum: List[PathType]) -> None:
        accum.append(self._safe_path(path.lower()))

    def _id_type(self,
                 load_type: DataGameContext.Type,
                 context:   DataGameContext,
                 out_ids:   List[PathType]) -> None:
        '''
        Convert the DataGameContext.Type enum into part of the id usable for
        getting data from this repo.

        Appends the conversion to the `out_ids` list.
        '''
        if load_type == DataGameContext.Type.PLAYER:
            self._id_accum('players', out_ids)
        elif load_type == DataGameContext.Type.MONSTER:
            self._id_accum('monsters', out_ids)
        elif load_type == DataGameContext.Type.NPC:
            self._id_accum('npcs', out_ids)
        elif load_type == DataGameContext.Type.ITEM:
            self._id_accum('items', out_ids)
        else:
            raise exceptions.LoadError(
                f"No DataGameContext.Type to ID conversion for: {load_type}",
                None,
                self.context.push(context))

    def _id_keys(self,
                 load_type: DataGameContext.Type,
                 context:   DataGameContext,
                 out_ids:   List[PathType]) -> None:
        '''
        Turns each context.data_values element into part of the id for getting a
        datum from this repo.

        Appends the conversions to the `out_ids` list.
        '''
        for id_element in context.data_values:
            self._id_accum(id_element, out_ids)

    def _id(self,
            type:        DataGameContext.Type,
            context:     DataGameContext) -> List[PathType]:
        '''
        Turns data repo keys in the context into an id we can use to retrieve
        the data. Keys are safe and ready to go.
        '''
        ids = []
        self._id_accum(context.campaign, ids)
        self._id_type(type,
                      context,
                      ids)
        self._id_keys(type,
                      context,
                      ids)
        return ids

    def _id_to_path(self,
                    ids:     List[PathType],
                    context: DataGameContext) -> pathlib.Path:
        '''
        Turn identity stuff into filepath components.
        '''
        return self.rooted_path(*self._ext_glob(ids))

    # --------------------------------------------------------------------------
    # Paths In General
    # --------------------------------------------------------------------------

    def rooted_path(self, *args: PathType) -> pathlib.Path:
        '''
        Assumes args are already safe, joins them all to `self.root` and returns
        the pathlib.Path.
        '''
        return self.root.joinpath(*args)

    def _ext_glob(self, elements: List[PathType]) -> List[PathType]:
        '''Concatenates extensions glob onto last path element is list.'''
        if not elements:
            return elements

        last = elements[-1]
        try:
            # pathlib.Path?
            last = last.with_suffix(".*")
        except AttributeError:
            # str then?
            last = elements[-1] + ".*"

        elements[-1] = last
        return elements

    # --------------------------------------------------------------------------
    # Path Safing
    # --------------------------------------------------------------------------

    def _safe_path(self,
                   unsafe: PathType,
                   context: Optional[DataGameContext] = None) -> pathlib.Path:
        '''Makes `unsafe` safe with self.fn_path_safing. '''

        if not self.fn_path_safing:
            raise exceptions.LoadError(
                "No path safing function set! Cannot create file paths. ",
                None,
                self.context.push(context)) from error

        return self.fn_path_safing(unsafe)




# §-TODO-§ [2020-06-01]: templates repo?
# @register('veredi', 'repository', 'templates', 'file-tree')
# class FileTreeTemplates(FileTreeRepository):
#
#     _REPO_NAME   = 'file-tree'
#     _CONTEXT_NAME = 'file-tree'
#     _CONTEXT_KEY  = 'templates'
