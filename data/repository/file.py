# coding: utf-8

'''
Base Repository Pattern for load, save, etc. from
various backend implementations (db, file, etc).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    NewType, Union, Optional, List)
if TYPE_CHECKING:
    from veredi.base.context import VerediContext


import pathlib
import re
import hashlib
from io import StringIO, TextIOBase
import enum


from veredi.logger               import log
from veredi.data.config.registry import register
from veredi.data                 import background

from veredi.base                 import dotted
from veredi.data.context         import (DataBareContext,
                                         DataGameContext)
from veredi.data.config.context  import ConfigContext

from ..                          import exceptions
from .                           import base


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

PathType = NewType('PathType', Union[str, pathlib.Path])

# TODO [2020-05-23]: other file repos...
#   FileTreeDiffRepository - for saving history for players

# ---
# Path Safing Consts
# ---

_HUMAN_SAFE = re.compile(r'[^\w\d-]')
_REPLACEMENT = '_'


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# -------------------------------Just Functions.-------------------------------
# --                            Paths In General                             --
# -----------------------------------------------------------------------------

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


# ----------------------------Bare File Repository-----------------------------
# --                        Load a file specifically.                        --
# -----------------------------------------------------------------------------

@register('veredi', 'repository', 'file-bare')
class FileBareRepository(base.BaseRepository):

    _DOTTED_NAME = 'veredi.repository.file-bare'

    _SANITIZE_KEYCHAIN = ['repository', 'sanitize']

    _REPO_NAME = 'file-bare'

    def __init__(self,
                 config_context: Optional['ConfigContext'] = None) -> None:
        # Bare context doesn't have a root until it loads something from
        # somewhere. Then that directory is its root.
        self._root = None

        super().__init__(self._REPO_NAME,
                         config_context)

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''
        Allows repos to grab anything from the config data that they need to
        set up themselves.
        '''
        config = background.config.config
        if not config:
            raise background.config.exception(
                context,
                None,
                "Cannot configure {} without a Configuration in the "
                "supplied context.",
                self.__class__.__name__)

        # Bare repo doesn't have a root until it loads something from
        # somewhere. Then that directory is its root.
        self._root = None

        # Config probably isn't much set up right now. May need to
        # inject/partially-load something to see if we can get options into
        # here now...
        path_safing_fn = None
        path_safing = config.get_data(*self._SANITIZE_KEYCHAIN)
        if path_safing:
            path_safing_fn = config.get_registered(path_safing,
                                                   context)
        self.fn_path_safing = path_safing_fn or to_human_readable

        self._make_background(path_safing)

        log.debug("Set my root to: {}", self.root)
        log.debug("Set my path-safing to: {}", self.fn_path_safing)

    def _make_background(self, safing_ds: str) -> None:
        self._bg = super()._make_background(self._DOTTED_NAME)

        self._bg['path'] = self.root
        self._bg['path-safing'] = safing_ds

    @property
    def background(self):
        '''
        Data for the Veredi Background context.

        Returns: (data, background.Ownership)
        '''
        return self._bg, background.Ownership.SHARE

    # -------------------------------------------------------------------------
    # Load Methods
    # -------------------------------------------------------------------------

    def _ext_glob(self, element: PathType) -> PathType:
        '''Concatenates extensions glob onto pathlib.Path/str.'''
        try:
            # pathlib.Path?
            element = element.with_suffix(".*")
        except AttributeError:
            # str then?
            element = element + ".*"

        return element

    @property
    def root(self) -> pathlib.Path:
        '''
        Returns the root of the repository.
        '''
        log.debug("root is: {}", self._root)
        return self._root

    def _definiton_path(self,
                        dotted_name: str,
                        context: 'VerediContext') -> pathlib.Path:
        '''
        Turns a dotted name into a path.
        '''
        path = dotted.to_path(dotted_name)
        return self.root / self._ext_glob(path)

    def load(self,
             context: DataBareContext) -> TextIOBase:
        '''
        Loads data from repository based on the context.

        Returns io stream.
        '''
        load_id = self._id(context)
        load_path = self._id_to_path(load_id, context)

        return self._load(load_path, context)

    def definition(self,
                   dotted_name: str,
                   context: 'VerediContext') -> TextIOBase:
        '''
        Load a definition file by splitting `dotted_name` and looking there for
        a file matching a glob we create.

        e.g. if `dotted_name` is 'veredi.rules.d20.skill.system', this will
        look in self.root for "veredi/rules/d20/skill/system.*".
        '''
        defpath = self._definiton_path(dotted_name, context)

        return self._load(defpath, context)

    def _context_load_data(self,
                           context: 'VerediContext',
                           load_path: pathlib.Path) -> 'VerediContext':
        '''
        Inject our repository data and our load data into the context.
        In the case of file repositories, include the file path.
        '''
        meta, _ = self.background
        context[str(background.Name.REPO)] = {
            'meta': meta,
            'path': str(load_path),
        }
        return context

    def _load(self,
              load_path: pathlib.Path,
              context: 'VerediContext') -> TextIOBase:
        '''
        Looks for file at load_path. If it exists, loads that file.
        '''
        self._context_load_data(context, load_path)

        # load_path should be exact - no globbing.
        if not load_path.exists():
            raise log.exception(
                None,
                exceptions.LoadError,
                "Cannot load file. Path/file does not exist: {}",
                str(load_path),
                context=context)

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
                    exceptions.LoadError,
                    "Error loading data from file. context: {}",
                    context=context) from error

        return data_stream

    # -------------------------------------------------------------------------
    # Identification ("Leeloo Dallas, Multi-Pass")
    # -------------------------------------------------------------------------

    def _id(self,
            context: DataGameContext) -> pathlib.Path:
        '''
        Turns data repo keys in the context into an id we can use to retrieve
        the data. Keys are safe and ready to go.
        '''
        self._root = context.load.parent
        self._bg['path'] = self._root
        return context.load

    def _id_to_path(self,
                    load_id: PathType,
                    context: DataGameContext) -> None:
        '''
        Turn identity stuff into filepath components.
        '''
        return pathlib_cast(load_id)

    # -------------------------------------------------------------------------
    # Path Safing
    # -------------------------------------------------------------------------

    def _safe_path(self,
                   unsafe: PathType,
                   context: Optional[DataGameContext] = None) -> pathlib.Path:
        '''Makes `unsafe` safe with self.fn_path_safing. '''

        if not self.fn_path_safing:
            raise log.exception(
                None,
                exceptions.LoadError,
                "No path safing function set! Cannot create file paths. ",
                context=context)

        return self.fn_path_safing(unsafe)


# ----------------------------File Tree Repository-----------------------------
# --       Load a file given context information and a base directory.       --
# -----------------------------------------------------------------------------

@register('veredi', 'repository', 'file-tree')
class FileTreeRepository(base.BaseRepository):

    _DOTTED_NAME = 'veredi.repository.file-tree'
    _REPO_NAME   = 'file-tree'

    _SANITIZE_KEYCHAIN = ['repository', 'sanitize']
    _PATH_KEYCHAIN = ['repository', 'directory']

    # ---
    # Sub-Directories
    # ---
    @enum.unique
    class Category(enum.Enum):
        GAME = 'game'
        '''Game data like saved characters, monsters, items, etc.'''

        DEFINITIONS = 'definitions'
        '''System/rules definitions like skills, etc.'''

    # ---
    # Path Names
    # ---
    _HUMAN_SAFE = re.compile(r'[^\w\d-]')
    _REPLACEMENT = '_'

    def __init__(self,
                 context: Optional['VerediContext'] = None) -> None:
        self._root = None

        super().__init__(self._REPO_NAME,
                         context)

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''
        Allows repos to grab anything from the config data that they need to
        set up themselves.
        '''
        config = background.config.config
        if not config:
            raise background.config.exception(
                context,
                None,
                "Cannot configure {} without a Configuration in the "
                "supplied context.",
                self.__class__.__name__)

        # Start at ConfigContext's path...
        self._root = ConfigContext.path(context)
        # ...add config's repo path on top of it
        # (in case it's a relative path).
        self._root = self._root / pathlib_cast(
            config.get_data(*self._PATH_KEYCHAIN))
        # Resolve to turn into absolute path and remove ".."s and stuff.
        self._root = self._root.resolve()

        path_safing_fn = None
        path_safing = config.get_data(*self._SANITIZE_KEYCHAIN)
        if path_safing:
            path_safing_fn = config.get_registered(path_safing,
                                                   context)
        self.fn_path_safing = path_safing_fn or to_human_readable

        self._make_background(path_safing)

        log.debug("Set my root to: {}", self.root)
        log.debug("Set my path-safing to: {}", self.fn_path_safing)

    def _make_background(self, safing_ds: str) -> None:
        self._bg = super()._make_background(self._DOTTED_NAME)

        self._bg['path'] = self.root
        self._bg['path-safing'] = safing_ds

    @property
    def background(self):
        '''
        Data for the Veredi Background context.

        Returns: (data, background.Ownership)
        '''
        return self._bg, background.Ownership.SHARE

    # -------------------------------------------------------------------------
    # Load Methods
    # -------------------------------------------------------------------------

    @property
    def root(self) -> pathlib.Path:
        '''
        Returns the root of the repository.
        '''
        log.debug("root is: {}", self._root)
        return self._root

    def _definiton_path(self,
                        dotted_name: str,
                        context: 'VerediContext') -> pathlib.Path:
        '''
        Turns a dotted name into a path.
        '''
        path = dotted.to_path(dotted_name)
        return self.rooted_path(self.Category.DEFINITIONS,
                                self._ext_glob(path))

    def load(self,
             context: DataGameContext) -> TextIOBase:
        '''
        Loads data from repository based on the context.

        Returns io stream.
        '''
        ids = self._id(context.type,
                       context)
        pattern_path = self._id_to_path(ids, context)
        return self._load(pattern_path, context)

    def definition(self,
                   dotted_name: str,
                   context: 'VerediContext') -> TextIOBase:
        '''
        Load a definition file by splitting `dotted_name` and looking there for
        a file matching a glob we create.

        e.g. if `dotted_name` is 'veredi.rules.d20.skill.system', this will
        look in self.root for "veredi/rules/d20/skill/system.*".
        '''
        defpath = self._definiton_path(dotted_name, context)
        return self._load(defpath, context)

    def _context_load_data(self,
                           context: 'VerediContext',
                           load_path: pathlib.Path) -> 'VerediContext':
        '''
        Inject our repository data and our load data into the context.
        In the case of file repositories, include the file path.
        '''
        meta, _ = self.background
        context[str(background.Name.REPO)] = {
            'meta': meta,
            'path': load_path,
        }
        return context

    def _load(self,
              pattern_path: pathlib.Path,
              context: 'VerediContext') -> TextIOBase:
        '''
        Looks for a match to pattern_path by splitting into parent dir and
        glob/file name. If only one match, loads that file.
        '''
        # Use path to find a file match.
        directory = pattern_path.parent
        glob = pattern_path.name
        file_path = None
        # print(f"\n\nmatches for glob: {directory}/{glob}:")
        # print(f"  {list(directory.glob(glob))}")
        for match in directory.glob(glob):
            if file_path is not None:
                # Throw all matches into context for error.
                self._context_load_data(context,
                                        list(directory.glob(glob)))
                raise exceptions.LoadError(
                    f"Too many matches for loading file by id: "
                    f"directory: {directory}, glob: {glob}, "
                    f"matches: {sorted(directory.glob(glob))}",
                    None,
                    context)
            file_path = match

        self._context_load_data(context, file_path)

        if file_path is None:
            raise exceptions.LoadError(
                f"Zero matches for loading file by id: "
                f"directory: {directory}, glob: {glob}, "
                f"matches: {sorted(directory.glob(glob))}",
                None,
                context)

        # with file_path.open('r') as xxx:
        #     print(xxx.read(None))

        data_stream = None
        with file_path.open('r') as file_stream:
            # Can raise an error - we'll let it.
            try:
                # print("\n\nfile tell:", file_stream.tell())
                data_stream = StringIO(file_stream.read(None))
                # print("string tell:", data_stream.tell(), "\n\n")
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
                    exceptions.LoadError,
                    "Error loading data from file. context: {}",
                    context=context) from error

        return data_stream

    # -------------------------------------------------------------------------
    # Identification ("Leeloo Dallas, Multi-Pass")
    # -------------------------------------------------------------------------

    def _id_accum(self, path: PathType, accum: List[PathType]) -> None:
        accum.append(self._safe_path(path.lower()))

    def _id_type(self,
                 load_type: DataGameContext.DataType,
                 context:   DataGameContext,
                 out_ids:   List[PathType]) -> None:
        '''
        Convert the DataGameContext.DataType enum into part of the id usable
        for getting data from this repo.

        Appends the conversion to the `out_ids` list.
        '''
        if load_type == DataGameContext.DataType.PLAYER:
            self._id_accum('players', out_ids)
        elif load_type == DataGameContext.DataType.MONSTER:
            self._id_accum('monsters', out_ids)
        elif load_type == DataGameContext.DataType.NPC:
            self._id_accum('npcs', out_ids)
        elif load_type == DataGameContext.DataType.ITEM:
            self._id_accum('items', out_ids)
        else:
            raise exceptions.LoadError(
                "No DataGameContext.DataType to ID conversion for: "
                f"{load_type}",
                None,
                context)

    def _id_keys(self,
                 load_type: DataGameContext.DataType,
                 context:   DataGameContext,
                 out_ids:   List[PathType]) -> None:
        '''
        Turns each context.data_values element into part of the id for getting
        a datum from this repo.

        Appends the conversions to the `out_ids` list.
        '''
        for id_element in context.data_values:
            self._id_accum(id_element, out_ids)

    def _id(self,
            type:        DataGameContext.DataType,
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
        return self.rooted_path(self.Category.GAME,
                                *self._ext_glob_list(ids))

    # -------------------------------------------------------------------------
    # Paths In General
    # -------------------------------------------------------------------------

    def rooted_path(self, category: Category, *args: PathType) -> pathlib.Path:
        '''
        Assumes args are already safe, joins them all to `self.root` and
        returns the pathlib.Path.
        '''
        return self.root.joinpath(category.value, *args)

    def _ext_glob_list(self, elements: List[PathType]) -> List[PathType]:
        '''Concatenates extensions glob onto last path element is list.'''
        if not elements:
            return elements

        # Update last element in list with its glob.
        elements[-1] = self._ext_glob(elements[-1])
        return elements

    def _ext_glob(self, element: PathType) -> PathType:
        '''Concatenates extensions glob onto pathlib.Path/str.'''
        try:
            # pathlib.Path?
            element = element.with_suffix(".*")
        except AttributeError:
            # str then?
            element = element + ".*"

        return element

    # -------------------------------------------------------------------------
    # Path Safing
    # -------------------------------------------------------------------------

    def _safe_path(self,
                   unsafe: PathType,
                   context: Optional[DataGameContext] = None) -> pathlib.Path:
        '''Makes `unsafe` safe with self.fn_path_safing. '''

        if not self.fn_path_safing:
            raise log.exception(
                None,
                exceptions.LoadError,
                "No path safing function set! Cannot create file paths.",
                context=context)

        return self.fn_path_safing(unsafe)


# ----------------------------File Tree Templates------------------------------
# --               Files for Defining Components and Stuff.                  --
# -----------------------------------------------------------------------------

# TODO [2020-06-01]: templates repo?
# @register('veredi', 'repository', 'templates', 'file-tree')
# class FileTreeTemplates(FileTreeRepository):
#
#     _REPO_NAME   = 'file-tree'
