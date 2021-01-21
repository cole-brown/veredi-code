# coding: utf-8

'''
Base Repository Pattern for load, save, etc. from
various backend implementations (db, file, etc).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, Type, NewType, List


import pathlib
import re
import hashlib
import enum
from io import StringIO, TextIOBase


from veredi.logger               import log
from veredi.data.config.registry import register
from veredi.data                 import background

from veredi.base                 import label, vstring, lists
from veredi.base.exceptions      import VerediError
from veredi.data.context         import (BaseDataContext,
                                         DataBareContext,
                                         DataGameContext,
                                         DataLoadContext,
                                         DataSaveContext)
from veredi.data.config.context  import ConfigContext

from ..                          import exceptions
from .                           import base
from .taxon                      import Rank, Taxon, LabelTaxon, SavedTaxon


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

PathType = NewType('PathType', Union[str, pathlib.Path])

# TODO [2020-05-23]: other file repos...
#   FileTreeDiffRepository - for saving history for players

# ---
# Path Safing Consts
# ---

_HUMAN_SAFE = re.compile(r'[^\w\d_.-]')
_REPLACEMENT = '_'


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# -------------------------------Just Functions.-------------------------------
# --                            Paths In General                             --
# -----------------------------------------------------------------------------

# TODO: move to a base/path.py file?
def pathlib_cast(*str_or_path: PathType) -> pathlib.Path:
    '''
    Ensure that `str_or_path` is a pathlib.Path.
    '''
    return pathlib.Path(*str_or_path)


# --------------------------------------------------------------------------
# Path Safing Option:
#   "us?#:er" -> "us___er"
# --------------------------------------------------------------------------
@register('veredi', 'sanitize', 'human', 'path-safe')
def to_human_readable(*part: PathType) -> pathlib.Path:
    '''
    Sanitize each part of the path by converting illegal characters to safe
    characters.

    "/" is illegal.

    So ensure that the safe portion of the paths is split if providing a full
    path.
    '''
    sanitized = []
    try:
        first = True
        for each in part:
            # First part can be a root, in which case we can't sanitize it.
            if first:
                check = pathlib_cast(each)
                # Must be a path.
                if (isinstance(check, pathlib.Path)
                        # Must be absolute.
                        and check.is_absolute()
                        # Must be /only/ the root.
                        and len(check.parts) == 1):
                    # Ok; root can be used as-is.
                    sanitized.append(check)

                # Not a root; sanitize it.
                else:
                    sanitized.append(_part_to_human_readable(each))

            # All non-first parts get sanitized.
            else:
                sanitized.append(_part_to_human_readable(each))
            first = False

    except TypeError as error:
        log.exception(error,
                      "to_human_readable: Cannot sanitize path: {}",
                      part)
        raise

    return pathlib_cast(*sanitized)


def _part_to_human_readable(part: PathType) -> str:
    '''
    Sanitize a single part of the path by converting illegal characters to safe
    characters.

    "/" is illegal.
    '''
    try:
        # Normalize our string first.
        normalized = vstring.normalize(part)
        # Then ensure part is a string before doing the regex replace.
        humanized = _HUMAN_SAFE.sub(_REPLACEMENT, normalized)
    except TypeError as error:
        log.exception(error,
                      "to_human_readable: Cannot sanitize path: {}",
                      part)
        raise
    return humanized


# --------------------------------------------------------------------------
# Path Safing Option:
#   "us?#:er" ->
#     'b3b31a87f6cca2e4d8e7909395c4b4fd0a5ee73b739b54eb3aeff962697ca603'
# --------------------------------------------------------------------------
@register('veredi', 'sanitize', 'hashed', 'sha256')
def to_hashed(*part: PathType) -> pathlib.Path:
    '''
    Sanitize each part of the path by converting it to a hash string.

    So ensure that all directories in the path are split if providing a full
    path.
    '''
    sanitized = []
    try:
        first = True
        for each in part:
            # First part can be a root, in which case we can't sanitize it.
            if first:
                check = pathlib_cast(each)
                # Must be a path.
                if (isinstance(check, pathlib.Path)
                        # Must be absolute.
                        and check.is_absolute()
                        # Must be /only/ the root.
                        and len(check.parts) == 1):
                    # Ok; root can be used as-is.
                    sanitized.append(check)

                # Not a root; sanitize it.
                else:
                    sanitized.append(_part_to_hashed(each))

            # All non-first parts get sanitized.
            else:
                sanitized.append(_part_to_hashed(each))

    except TypeError as error:
        log.exception(error,
                      "to_hashed: Cannot sanitize path: {}",
                      part)
        raise

    return pathlib_cast(*sanitized)


def _part_to_hashed(part: PathType) -> str:
    '''
    Sanitize each part of the path by converting it to a hash.
    '''
    try:
        # Ensure part is a string, encode to bytes, and hash those.
        hashed = hashlib.sha256(str(part).encode()).hexdigest()
    except TypeError as error:
        log.exception(error,
                      "_part_to_hashed: Cannot sanitize part: {}",
                      part)
        raise
    return hashed


# ----------------------------Bare File Repository-----------------------------
# --                        Load a file specifically.                        --
# -----------------------------------------------------------------------------

@register('veredi', 'repository', 'file-bare')
class FileBareRepository(base.BaseRepository):

    _DOTTED_NAME = 'veredi.repository.file-bare'

    _SANITIZE_KEYCHAIN = ['repository', 'sanitize']

    _REPO_NAME = 'file-bare'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        super()._define_vars()

        self._root: pathlib.Path = None
        '''Aboslute path to the root of this file repository.'''

    def __init__(self,
                 config_context: Optional[ConfigContext] = None) -> None:
        super().__init__(self._REPO_NAME, config_context)

    def _configure(self,
                   context: Optional[ConfigContext]) -> None:
        '''
        Allows repos to grab anything from the config data that they need to
        set up themselves.
        '''
        config = background.config.config
        if not config:
            raise background.config.exception(
                context,
                "Cannot configure {} without a Configuration in the "
                "supplied context.",
                self.__class__.__name__)

        # Bare repo doesn't have a root until it loads something from
        # somewhere. Then that directory is its root.
        self._root = None

        # Grab our primary id from the context, if it's there...
        self._primary_id = context.id  # or config.primary_id?

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

    def _make_background(self, safing_dotted: str) -> None:
        self._bg = super()._make_background(self._DOTTED_NAME)

        self._bg[background.Name.PATH.key] = self.root
        self._bg['path-safing'] = safing_dotted

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

    def load(self,
             context: DataBareContext) -> TextIOBase:
        '''
        Loads data from repository based on the context.

        Returns io stream.
        '''
        key = self._key(context)
        return self._load(key, context)

    def _context_load_data(self,
                           context: DataLoadContext,
                           load_path: pathlib.Path) -> DataLoadContext:
        '''
        Inject our repository data and our load data into the context.
        In the case of file repositories, include the file path.
        '''
        meta, _ = self.background
        context.repo_data = {
            'meta': meta,
            'path': str(load_path),
        }
        return context

    def _load(self,
              load_path: pathlib.Path,
              context: DataLoadContext) -> TextIOBase:
        '''
        Looks for file at load_path. If it exists, loads that file.
        '''
        self._context_load_data(context, load_path)

        # load_path should be exact - no globbing.
        if not load_path.exists():
            raise log.exception(
                self._error_type(context),
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
                    self._error_type(context),
                    "Error loading data from file. context: {}",
                    context=context) from error

        return data_stream

    # -------------------------------------------------------------------------
    # Identification ("Leeloo Dallas, Multi-Pass")
    # -------------------------------------------------------------------------

    def _key(self,
             context: DataBareContext) -> pathlib.Path:
        '''
        Turns load data in the context into a key we can use to retrieve
        the data.
        '''
        self._root = context.key.parent
        # We are a FileBareRepo, and now we know our root (for the time
        # being...). Put it in our bg data.
        self._bg['path'] = self._root
        # And make sure our 'key' (path) is safe to use.
        if isinstance(context.key, pathlib.Path):
            return self._safe_path(*context.key.parts, context=context)

    # -------------------------------------------------------------------------
    # Path Safing
    # -------------------------------------------------------------------------

    def _safe_path(self,
                   *unsafe: PathType,
                   context: Optional[DataGameContext] = None
                   ) -> pathlib.Path:
        '''
        Makes `unsafe` safe with self.fn_path_safing.

        Combines all unsafe together and returns as one Path object.

        `context` used for Load/SaveError if no `self.fn_path_safing`.
        '''
        if not self.fn_path_safing:
            raise log.exception(
                self._error_type(context),
                "No path safing function set! Cannot create file paths.",
                context=context)

        path = self.fn_path_safing(*unsafe)
        return path


# ----------------------------File Tree Repository-----------------------------
# --       Load a file given context information and a base directory.       --
# -----------------------------------------------------------------------------

@register('veredi', 'repository', 'file-tree')
class FileTreeRepository(base.BaseRepository):

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    _DOTTED_NAME = 'veredi.repository.file-tree'
    _REPO_NAME   = 'file-tree'

    _SANITIZE_KEYCHAIN = ['repository', 'sanitize']
    _PATH_KEYCHAIN = ['repository', 'directory']

    # ---
    # Path Names
    # ---
    _HUMAN_SAFE = re.compile(r'[^\w\d-]')
    _REPLACEMENT = '_'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        super()._define_vars()

        self._root: pathlib.Path = None
        '''Aboslute path to the root of this file repository.'''

    def __init__(self,
                 config_context: Optional[ConfigContext] = None) -> None:
        super().__init__(self._REPO_NAME, config_context)

    def _configure(self,
                   context: Optional[ConfigContext]) -> None:
        '''
        Allows repos to grab anything from the config data that they need to
        set up themselves.
        '''
        config = background.config.config
        if not config:
            raise background.config.exception(
                context,
                "Cannot configure {} without a Configuration in the "
                "supplied context.",
                self.__class__.__name__)

        # Start at ConfigContext's path...
        self._root = ConfigContext.path(context)
        # ...add config's repo path on top of it (in case it's a relative path
        # (pathlib is smart enough to correctly handle when it's not)).
        self._root = self._root / pathlib_cast(
            config.get_data(*self._PATH_KEYCHAIN))
        # Resolve it to turn into absolute path and remove ".."s and stuff.
        self._root = self._root.resolve()

        # Grab our primary id from the context too.
        self._primary_id = ConfigContext.id(context)  # or config.primary_id?

        # Set up our path safing too...
        path_safing_fn = None
        path_safing = config.get_data(*self._SANITIZE_KEYCHAIN)
        if path_safing:
            path_safing_fn = config.get_registered(path_safing,
                                                   context)
        self.fn_path_safing = path_safing_fn or to_human_readable

        self._make_background(path_safing)

        log.debug("Set my root to: {}", self.root)
        log.debug("Set my path-safing to: {}", self.fn_path_safing)

    def _make_background(self, safing_dotted: str) -> None:
        self._bg = super()._make_background(self._DOTTED_NAME)

        self._bg['path'] = self.root
        self._bg['path-safing'] = safing_dotted

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
    def primary_id(self) -> str:
        '''
        The primary id (game/campaign name, likely, for file-tree repo).
        '''
        return self._primary_id

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
        key = self._key(context)
        return self._load(key, context)

    def _context_load_data(self,
                           context: DataLoadContext,
                           load_path: pathlib.Path) -> DataLoadContext:
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
              path:    pathlib.Path,
              context: DataLoadContext) -> TextIOBase:
        '''
        Looks for a match to `path` by splitting into parent dir and
        glob/file name. If only one match, loads that file.
        '''
        # ------------------------------
        # Search...
        # ------------------------------
        # Use path to find all file matchs...
        directory = path.parent
        glob = path.name
        matches = []
        for match in directory.glob(glob):
            matches.append(match)

        # ------------------------------
        # Sanity
        # ------------------------------
        # Error if we found more than one match.
        if not matches:
            # We found nothing.
            self._context_load_data(context, matches)
            raise log.exception(
                self._error_type(context),
                f"No matches for loading file: "
                f"directory: {directory}, glob: {glob}, "
                f"matches: {matches}",
                context=context)
        elif len(matches) > 1:
            # Throw all matches into context for error.
            self._context_load_data(context, matches)
            raise log.exception(
                self._error_type(context),
                f"Too many matches for loading file: "
                f"directory: {directory}, glob: {glob}, "
                f"matches: {sorted(matches)}",
                context=context)

        # ------------------------------
        # Set-Up...
        # ------------------------------
        path = matches[0]
        self._context_load_data(context, path)

        # ------------------------------
        # Load!
        # ------------------------------
        data_stream = None
        with path.open('r') as file_stream:
            # Can raise an error - we'll let it.
            try:
                # print("\n\nfile tell:", file_stream.tell())
                data_stream = StringIO(file_stream.read(None))
                # print("string tell:", data_stream.tell(), "\n\n")
                # print("\ndata_stream:")
                # print(data_stream.read(None))
                # print("\n")

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
                    self._error_type(context),
                    "Error loading data from file. context: {}",
                    context=context) from error

        # ------------------------------
        # Done.
        # ------------------------------
        return data_stream

    # -------------------------------------------------------------------------
    # Identification ("Leeloo Dallas, Multi-Pass")
    # -------------------------------------------------------------------------

    def _key(self,
             context:     DataGameContext) -> List[PathType]:
        '''
        Give the DataContext, return the data's repository key.
        '''
        # Get the taxon from the context.
        taxon = context.taxon
        if not taxon:
            raise log.exception(
                self._error_type(context),
                "Cannot {} data; no Taxon present: {}",
                self._error_name(context, False),
                taxon,
                context=context)

        # # Get our category (game saves vs definitions)...
        # category = self._category(context)

        # And our key is the rooted path based on category and taxon data.
        replace = {
            Rank.Kingdom.CAMPAIGN: self.primary_id,
        }
        resolved = taxon.resolve(replace)
        # path = self._path(category, resolved, glob=True)
        path = self._path(resolved, glob=True)
        return path

    # -------------------------------------------------------------------------
    # Paths In General
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

    def _path(self,
              unsafe:   PathType,
              glob:     bool            = False,
              context:  DataGameContext = None) -> pathlib.Path:
        '''
        Returns a path based on the Repository's root and `unsafe`.

        If `glob` is True, adds `_ext_glob()` to the end of the returned path.

        `context` is used indirectly - probably for errors - and can be None.

        Returned path is safe according to `_safe_path()`.
        '''
        # Make it into a safe path.
        path = self.root.joinpath(self._safe_path(*unsafe,
                                                  context=context))
        if glob:
            path = self._ext_glob(path)
        return path

    # -------------------------------------------------------------------------
    # Path Safing
    # -------------------------------------------------------------------------

    def _safe_path(self,
                   *unsafe: PathType,
                   context: Optional[DataGameContext] = None
                   ) -> pathlib.Path:
        '''
        Makes `unsafe` safe with self.fn_path_safing.

        Combines all unsafe together and returns as one Path object.

        `context` used for Load/SaveError if no `self.fn_path_safing`.
        '''

        if not self.fn_path_safing:
            raise log.exception(
                self._error_type(context),
                "No path safing function set! Cannot create file paths.",
                context=context)

        path = self.fn_path_safing(*unsafe)
        log.debug(f"Unsafe: *{unsafe} -> Safe Path: {path}",
                  context=context)
        return path


# ----------------------------File Tree Templates------------------------------
# --               Files for Defining Components and Stuff.                  --
# -----------------------------------------------------------------------------

# TODO [2020-06-01]: templates repo?
# @register('veredi', 'repository', 'templates', 'file-tree')
# class FileTreeTemplates(FileTreeRepository):
#
#     _REPO_NAME   = 'file-tree'
