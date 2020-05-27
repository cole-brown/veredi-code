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
from veredi.base.context import (PersistentContext,
                                 DataBareContext,
                                 DataGameContext)
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


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'repository', 'file-bare')
class FileBareRepository(base.BaseRepository):

    _REPO_NAME   = 'file-bare'
    _CONTEXT_NAME = 'file-bare'
    _CONTEXT_KEY  = 'repository'

    # ---
    # Path Names
    # ---
    _HUMAN_SAFE = re.compile(r'[^\w\d-]')
    _REPLACEMENT = '_'

    def __init__(self,
                 path_safing_fn: Optional[Callable[[str], str]] = None
            ) -> None:
        super().__init__(self._REPO_NAME, self._CONTEXT_NAME, self._CONTEXT_KEY)

        # Use user-defined or set to our default.
        self.fn_path_safing = path_safing_fn or self._to_human_readable

    # --------------------------------------------------------------------------
    # Load Methods
    # --------------------------------------------------------------------------

    def load(self,
             context: DataBareContext) -> TextIOBase:
        '''
        Loads data from repository based on the context.

        Returns io stream.
        '''
        ids = self._id(context)
        load_path = self._id_to_path(ids, context)

        # load_path should be exact - no globbing.
        if not load_path.exists():
            raise exceptions.LoadError(
                f"Cannot load file. Path/file does not exist: {str(load_path)}",
                None,
                self.context.merge(context))

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
            except Exception as err:
                # Complain that we found an exception we don't handle.
                # ...then let it bubble up as-is.
                log.exception(err,
                              "Error loading data from file. context: {}",
                              context)
                if data_stream and not data_stream.closed:
                    data_stream.close()
                data_stream = None
                raise

        return data_stream

    # --------------------------------------------------------------------------
    # Identification ("Leeloo Dallas, Multi-Pass")
    # --------------------------------------------------------------------------

    def _id(self,
            context:     DataGameContext) -> List[str]:
        '''
        Turns data repo keys in the context into an id we can use to retrieve
        the data. Keys are safe and ready to go.
        '''
        return context.load

    def _id_to_path(self,
                    id:      Union[str, pathlib.Path],
                    context: DataGameContext) -> None:
        '''
        Turn identity stuff into filepath components.
        '''
        return self._pathlib_cast(id)

    # --------------------------------------------------------------------------
    # Paths In General
    # --------------------------------------------------------------------------

    def _pathlib_cast(self, string: PathType) -> pathlib.Path:
        return pathlib.Path(string)

    # --------------------------------------------------------------------------
    # Path Safing
    # --------------------------------------------------------------------------

    def _safe_path(self,
                   unsafe: PathType,
                   context: Optional[DataGameContext] = None) -> str:
        '''Makes `unsafe` safe with self.fn_path_safing. '''

        if not self.fn_path_safing:
            raise exceptions.LoadError(
                "No path safing function set! Cannot create file paths. ",
                None,
                self.context.merge(context)) from error

        return self.fn_path_safing(str(unsafe))

    # --------------------------------------------------------------------------
    # Path Safing Option:
    #   "us?#:er" -> "us___er"
    # --------------------------------------------------------------------------
    @staticmethod
    def _to_human_readable(string: str) -> str:
        return FileTreeRepository._HUMAN_SAFE.sub(
            FileTreeRepository._REPLACEMENT,
            string)

    # --------------------------------------------------------------------------
    # Path Safing Option:
    #   "us?#:er" ->
    #     'b3b31a87f6cca2e4d8e7909395c4b4fd0a5ee73b739b54eb3aeff962697ca603'
    # --------------------------------------------------------------------------
    @staticmethod
    def _to_hashed(string: str) -> str:
        return hashlib.sha256(string.encode()).hexdigest()


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
                 directory: PathType,
                 path_safing_fn: Optional[Callable[[str], str]] = None
            ) -> None:
        super().__init__(self._REPO_NAME, self._CONTEXT_NAME, self._CONTEXT_KEY)

        # Resolve into an absolute path.
        self.root = pathlib.Path(directory).resolve()

        # Use user-defined or set to our default.
        self.fn_path_safing = path_safing_fn or self._to_human_readable

    # --------------------------------------------------------------------------
    # Load Methods
    # --------------------------------------------------------------------------

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
                    self.context.merge(context))
            file_path = match

        if file_path is None:
            raise exceptions.LoadError(
                f"Zero matches for loading file by id: "
                f"directory: {directory}, glob: {glob}, "
                f"matches: {sorted(directory.glob(glob))}",
                None,
                self.context.merge(context))

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
                # ...then let it bubble up as-is.
                log.exception(err,
                              "Error loading data from file. context: {}",
                              context)
                if data_stream and not data_stream.closed:
                    data_stream.close()
                data_stream = None
                raise

        return data_stream

    # --------------------------------------------------------------------------
    # Identification ("Leeloo Dallas, Multi-Pass")
    # --------------------------------------------------------------------------

    def _id_accum(self, string: str, accum: List[str]) -> None:
        accum.append(self._safe_path(string.lower()))

    def _id_type(self,
                 load_type: DataGameContext.Type,
                 context:   DataGameContext,
                 out_ids:   List[str]) -> None:
        '''
        Convert the DataGameContext.Type enum into part of the id usable for getting
        data from this repo.

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
                self.context.merge(context))

    def _id_keys(self,
                 load_type: DataGameContext.Type,
                 context:   DataGameContext,
                 out_ids:   List[str]) -> None:
        '''
        Turns each context.data_values element into part of the id for getting a
        datum from this repo.

        Appends the conversions to the `out_ids` list.
        '''
        for id_element in context.data_values:
            self._id_accum(id_element, out_ids)

    def _id(self,
            type:        DataGameContext.Type,
            context:     DataGameContext) -> List[str]:
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
                    ids:     List[str],
                    context: DataGameContext) -> None:
        '''
        Turn identity stuff into filepath components.
        '''
        return self._rooted_path(*self._ext_glob(ids))

    # --------------------------------------------------------------------------
    # Paths In General
    # --------------------------------------------------------------------------

    def _ext_glob(self, elements: List[str]) -> List[str]:
        '''Concatenates extensions glob onto last path element is list.'''
        if elements:
            elements[-1] = elements[-1] + ".*"
        return elements

    def _rooted_path(self, *args: PathType) -> pathlib.Path:
        '''
        Assumes args are already safe, joins them all to `self.root` and returns
        the pathlib.Path.
        '''
        return self.root.joinpath(*args)

    def _pathlib_cast(self, string: PathType) -> pathlib.Path:
        return pathlib.Path(string)

    # --------------------------------------------------------------------------
    # Path Safing
    # --------------------------------------------------------------------------

    def _safe_path(self,
                   unsafe: PathType,
                   context: Optional[DataGameContext] = None) -> str:
        '''Makes `unsafe` safe with self.fn_path_safing. '''

        if not self.fn_path_safing:
            raise exceptions.LoadError(
                "No path safing function set! Cannot create file paths. ",
                None,
                self.context.merge(context)) from error

        return self.fn_path_safing(str(unsafe))

    # --------------------------------------------------------------------------
    # Path Safing Option:
    #   "us?#:er" -> "us___er"
    # --------------------------------------------------------------------------
    @staticmethod
    def _to_human_readable(string: str) -> str:
        return FileTreeRepository._HUMAN_SAFE.sub(
            FileTreeRepository._REPLACEMENT,
            string)

    # --------------------------------------------------------------------------
    # Path Safing Option:
    #   "us?#:er" ->
    #     'b3b31a87f6cca2e4d8e7909395c4b4fd0a5ee73b739b54eb3aeff962697ca603'
    # --------------------------------------------------------------------------
    @staticmethod
    def _to_hashed(string: str) -> str:
        return hashlib.sha256(string.encode()).hexdigest()


@register('veredi', 'repository', 'templates', 'file-tree')
class FileTreeTemplates(FileTreeRepository):

    def __init__(self,
                 directory: PathType,
                 path_safing_fn: Optional[Callable[[str], str]] = None
            ) -> None:
        super().__init__(directory, path_safing_fn)

        self._registry: Dict[str, pathlib.Path] = {}

    # §-TODO-§ [2020-05-26]: pass in config for set_up.
    def set_up(self, codec: BaseCodec) -> None:
        '''
        Initialize our template registry.
        '''
        # Walk directory tree.

        # Open each file, read it, decode it.

        # For each document in decoded data...

        # Register it if we see meta.registry key.

    # --------------------------------------------------------------------------
    # Load Methods
    # --------------------------------------------------------------------------

    def load(self,
             context: DataGameContext) -> TextIOBase:
        '''
        Loads data from repository based on `load_id`, `load_type`.

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
                    self.context.merge(context))
            file_path = match

        if file_path is None:
            raise exceptions.LoadError(
                f"Zero matches for loading file by id: "
                f"directory: {directory}, glob: {glob}, "
                f"matches: {sorted(directory.glob(glob))}",
                None,
                self.context.merge(context))

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
                # ...then let it bubble up as-is.
                log.exception(err,
                              "Error loading data from file. context: {}",
                              context)
                if data_stream and not data_stream.closed:
                    data_stream.close()
                data_stream = None
                raise

        return data_stream

    # --------------------------------------------------------------------------
    # Identification ("Leeloo Dallas, Multi-Pass")
    # --------------------------------------------------------------------------

    def _id_accum(self, string: str, accum: List[str]) -> None:
        accum.append(self._safe_path(string.lower()))

    def _id_type(self,
                 load_type: DataGameContext.Type,
                 context:   DataGameContext,
                 out_ids:   List[str]) -> None:
        '''
        Convert the DataGameContext.Type enum into part of the id usable for getting
        data from this repo.

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
                self.context.merge(context))

    def _id_keys(self,
                 load_type: DataGameContext.Type,
                 context:   DataGameContext,
                 out_ids:   List[str]) -> None:
        '''
        Turns each context.data_values element into part of the id for getting a
        datum from this repo.

        Appends the conversions to the `out_ids` list.
        '''
        for id_element in context.data_values:
            self._id_accum(id_element, out_ids)

    def _id(self,
            type:        DataGameContext.Type,
            context:     DataGameContext) -> List[str]:
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
                    ids:     List[str],
                    context: DataGameContext) -> None:
        '''
        Turn identity stuff into filepath components.
        '''
        return self._rooted_path(*self._ext_glob(ids))

    # --------------------------------------------------------------------------
    # Paths In General
    # --------------------------------------------------------------------------

    def _ext_glob(self, elements: List[str]) -> List[str]:
        '''Concatenates extensions glob onto last path element is list.'''
        if elements:
            elements[-1] = elements[-1] + ".*"
        return elements

    def _rooted_path(self, *args: PathType) -> pathlib.Path:
        '''
        Assumes args are already safe, joins them all to `self.root` and returns
        the pathlib.Path.
        '''
        return self.root.joinpath(*args)

    def _pathlib_cast(self, string: PathType) -> pathlib.Path:
        return pathlib.Path(string)

    # --------------------------------------------------------------------------
    # Path Safing
    # --------------------------------------------------------------------------

    def _safe_path(self,
                   unsafe: PathType,
                   context: Optional[DataGameContext] = None) -> str:
        '''Makes `unsafe` safe with self.fn_path_safing. '''

        if not self.fn_path_safing:
            raise exceptions.LoadError(
                "No path safing function set! Cannot create file paths. ",
                None,
                self.context.merge(context)) from error

        return self.fn_path_safing(str(unsafe))

    # --------------------------------------------------------------------------
    # Path Safing Option:
    #   "us?#:er" -> "us___er"
    # --------------------------------------------------------------------------
    @staticmethod
    def _to_human_readable(string: str) -> str:
        return FileTreeRepository._HUMAN_SAFE.sub(
            FileTreeRepository._REPLACEMENT,
            string)

    # --------------------------------------------------------------------------
    # Path Safing Option:
    #   "us?#:er" ->
    #     'b3b31a87f6cca2e4d8e7909395c4b4fd0a5ee73b739b54eb3aeff962697ca603'
    # --------------------------------------------------------------------------
    @staticmethod
    def _to_hashed(string: str) -> str:
        return hashlib.sha256(string.encode()).hexdigest()
