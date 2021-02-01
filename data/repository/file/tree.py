# coding: utf-8

'''
Base Repository Pattern for load, save, etc. from
various backend implementations (db, file, etc).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, List


import pathlib
import shutil
import re
from io import StringIO, TextIOBase


from veredi.data.config.registry import register
from veredi.data                 import background

from veredi.base                 import paths
from veredi.data.context         import (DataAction,
                                         DataBareContext,
                                         DataGameContext,
                                         DataLoadContext,
                                         DataSaveContext)
from veredi.data.config.context  import ConfigContext
from veredi.zest.exceptions      import UnitTestError


from ..                          import exceptions
from .                           import base
from .taxon                      import Rank


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


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

    _TEMP_PATH = 'zest-temp'

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
        config = background.config.config(self.__class__.__name__,
                                          self.dotted(),
                                          context)

        # Start at ConfigContext's path...
        self._root = ConfigContext.path(context)
        # ...add config's repo path on top of it (in case it's a relative path
        # (pathlib is smart enough to correctly handle when it's not)).
        self._root = self._root / paths.cast(
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

        self._log_debug("Set my root to: {}", self.root)
        self._log_debug("Set my path-safing to: {}", self.fn_path_safing)

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
    # Load / Save Helpers
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
        self._log_debug("root is: {}", self._root)
        return self._root

    def _context_data(self,
                      context: DataGameContext,
                      paths:   paths.PathsInput) -> DataGameContext:
        '''
        Inject our repository, path, and any other desired data into the
        context. In the case of file repositories, include the file path.
        '''
        action = context.action
        if (action == DataAction.SAVE
                and not isinstance(context, DataSaveContext)):
            raise self._log_exception(
                self._error_type(context),
                "Cannot save data; mismatched context type and data "
                "action for {}: {}, {}",
                self._error_name(context, False),
                type(context),
                action,
                context=context)
        elif (action == DataAction.LOAD
              and not isinstance(context, DataLoadContext)):
            raise self._log_exception(
                self._error_type(context),
                "Cannot load data; mismatched context type and data "
                "action for {}: {}, {}",
                self._error_name(context, False),
                type(context),
                action,
                context=context)

        meta, _ = self.background
        context[str(background.Name.REPO)] = {
            # Push our context data into here.
            'meta': meta,
            # And add any extra info.
            'action': action,
            'paths': paths.to_str_list(paths),
        }
        return context

    def _key(self,
             context: DataGameContext) -> List[paths.PathType]:
        '''
        Give the DataContext, return the data's repository key.
        '''
        # Get the taxon from the context.
        taxon = context.taxon
        if not taxon:
            raise self._log_exception(
                self._error_type(context),
                "Cannot {} data; no Taxon present: {}",
                self._error_name(context, False),
                taxon,
                context=context)

        # And our key is the rooted path based on category and taxon data.
        replace = {
            Rank.Kingdom.CAMPAIGN: self.primary_id,
        }
        resolved = taxon.resolve(replace)

        # Should we be in the temp dir for this?
        if context.temp:
            # Insert our temp dir into the resolved components.
            resolved.insert(self._TEMP_PATH, 0)

        path = self._path(resolved, context, glob=False)
        return path

    # -------------------------------------------------------------------------
    # Load Methods
    # -------------------------------------------------------------------------

    def load(self,
             context: DataGameContext) -> TextIOBase:
        '''
        Loads data from repository based on the context.

        Returns io stream.
        '''
        key = self._key(context, DataAction.LOAD)
        return self._load(key, context)

    def _load(self,
              path:    paths.PathType,
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
            self._context_data(context, matches, DataAction.LOAD)
            raise self._log_exception(
                self._error_type(context),
                f"No matches for loading file: "
                f"directory: {directory}, glob: {glob}, "
                f"matches: {matches}",
                context=context)
        elif len(matches) > 1:
            # Throw all matches into context for error.
            self._context_load_data(context, matches, DataAction.LOAD)
            raise self._log_exception(
                self._error_type(context),
                f"Too many matches for loading file: "
                f"directory: {directory}, glob: {glob}, "
                f"matches: {sorted(matches)}",
                context=context)

        # ------------------------------
        # Set-Up...
        # ------------------------------
        path = matches[0]
        self._context_load_data(context, path, DataAction.LOAD)

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
                raise self._log_exception(
                    self._error_type(context),
                    "Error loading data from file. context: {}",
                    context=context) from error

        # ------------------------------
        # Done.
        # ------------------------------
        return data_stream

    # -------------------------------------------------------------------------
    # Save Methods
    # -------------------------------------------------------------------------

    def save(self,
             data:    TextIOBase,
             context: 'DataBareContext') -> bool:
        '''
        Saves data to the repository based on data in the `context`.

        Returns success/failure of save operation.
        '''
        key = self._key(context, DataAction.SAVE)
        return self._save(key, data, context)

    def _save(self,
              save_path: paths.PathType,
              data:      TextIOBase,
              context:   DataBareContext) -> bool:
        '''
        Save `data` to `save_path`. If it already exists, overwrites that file.
        '''
        self._context_data(context, save_path, DataAction.SAVE)

        # We could have some check here if we don't want to overwrite...
        # if save_path.exists():
        #     raise self._log_exception(
        #         self._error_type(context),
        #         "Cannot save file without overwriting. "
        #         "Path/file already exist: {}",
        #         str(save_path),
        #         context=context)

        success = False
        with save_path.open('w') as file_stream:
            # Can raise errors - we'll let it.
            try:
                # Make sure we're at the beginning of the data stream...
                data.seek(0)
                # ...and use shutils to copy the data to disk.
                shutil.copyfileobj(data, file_stream)

                # We don't have anything to easily check to return
                # success/failure... Other than exceptions. We're here and
                # no exceptions, so...:
                success = True

            except exceptions.SaveError:
                # Let this one bubble up as-is.
                # TODO: log to Group.DATA_PROCESSING
                raise

            except Exception as error:
                # Complain that we found an exception we don't handle.
                # ...then let it bubble up.
                # TODO: log to Group.DATA_PROCESSING
                raise self._log_exception(
                    self._error_type(context),
                    "Error saving data to file. context: {}",
                    context=context) from error

        return success

    # -------------------------------------------------------------------------
    # Paths In General
    # -------------------------------------------------------------------------

    def _ext_glob(self, element: paths.PathType) -> paths.PathType:
        '''Concatenates extensions glob onto pathlib.Path/str.'''
        # Convert to a path, then adjust suffix.
        path = paths.cast(element)
        return path.with_suffix(".*")

    def _path(self,
              unsafe:   paths.PathType,
              context:  DataGameContext,
              ensure:   bool = True,
              glob:     bool = False) -> pathlib.Path:
        '''
        Returns a path based on the Repository's root and `unsafe`.

        If `glob` is True, adds `_ext_glob()` to the end of the returned path.

        If `ensure` is False, skip (possible) parent directory creation. No
        need to set for load vs save; that is handled automatically.

        `context` is used for `context.action` and for errors.

        Returned path is safe according to `_path_safed()`.
        '''
        # Make it into a safe path.
        path = self.root.joinpath(self._path_safed(*unsafe,
                                                   context=context))
        if glob:
            path = self._ext_glob(path)

        # Make sure the directory exists?
        if ensure and context.action == DataAction.SAVE:
            self._path_ensure(path)

        return path

    def _path_ensure(self,
                     path: pathlib.Path) -> None:
        '''
        Creates path's parent path if it does not exist.
        '''
        path.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Path Safing
    # -------------------------------------------------------------------------

    def _path_safed(self,
                    *unsafe: paths.PathType,
                    context: Optional[DataGameContext] = None
                    ) -> pathlib.Path:
        '''
        Makes `unsafe` safe with self.fn_path_safing.

        Combines all unsafe together and returns as one Path object.

        `context` used for Load/SaveError if no `self.fn_path_safing`.
        '''

        if not self.fn_path_safing:
            raise self._log_exception(
                self._error_type(context),
                "No path safing function set! Cannot create file paths.",
                context=context)

        path = self.fn_path_safing(*unsafe)
        self._log_debug(f"Unsafe: *{unsafe} -> Safe Path: {path}",
                        context=context)
        return path

    # -------------------------------------------------------------------------
    # Unit Testing Helpers
    # -------------------------------------------------------------------------

    def _temp_path(self) -> None:
        '''
        Path to our unit-testing temp dir.
        '''
        path = self.root.joinpath(self._TEMP_PATH)
        return path

    def _ut_set_up(self) -> None:
        '''
        Ensure our unit-testing dir doesn't exist, and then create it.
        '''
        # Make sure our root /does/ exist...
        if not self.root.exists() or not self.root.is_dir():
            msg = ("Invalid root directory for repo data! It must exist "
                   "and be a directory.")
            error = UnitTestError(msg,
                                  data={
                                      'meta': self._bg,
                                      'root': paths.to_str(self.root),
                                      'exists?': self.root.exists(),
                                      'file?': self.root.is_file(),
                                      'dir?': self.root.is_dir(),
                                  })
            raise self._log_exception(msg, error)

        # Make sure temp path doesn't exist first... Don't want to accidentally
        # use data from a previous test.
        path = self._temp_path()
        if path.exists():
            msg = "Temp Dir Path for Unit-Testing already exists!"
            error = UnitTestError(msg,
                                  data={
                                      'meta': self._bg,
                                      'temp-path': paths.to_str(path),
                                      'exists?': path.exists(),
                                      'file?': path.is_file(),
                                      'dir?': path.is_dir(),
                                  })
            raise self._log_exception(msg, error)

        # And now we can create it.
        path.mkdir(parents=True)

    def _ut_tear_down(self) -> None:
        '''
        Deletes our temp directory and all files in it.
        '''
        # ---
        # Make sure our root /does/ exist...
        # ---
        if not self.root.exists() or not self.root.is_dir():
            msg = ("Invalid root directory for repo data! It must exist "
                   "and be a directory.")
            error = UnitTestError(msg,
                                  data={
                                      'meta': self._bg,
                                      'root': paths.to_str(self.root),
                                      'exists?': self.root.exists(),
                                      'file?': self.root.is_file(),
                                      'dir?': self.root.is_dir(),
                                  })
            raise self._log_exception(msg, error)

        # ---
        # Does temp path exist?
        # ---
        path = self._temp_path()
        if path.exists():
            # Is it a dir?
            if path.is_dir():
                # Yeah - ok; delete it and it's files now.
                path = self.root.joinpath(self._TEMP_PATH)
                shutil.rmtree(path)

            # Not a dir - error.
            else:
                msg = "Cannot delete temp dir path - it is not a directory!"
                error = UnitTestError(msg,
                                      data={
                                          'meta': self._bg,
                                          'temp-path': paths.to_str(path),
                                          'exists?': path.exists(),
                                          'file?': path.is_file(),
                                          'dir?': path.is_dir(),
                                      })
                raise self._log_exception(msg, error)

        # ---
        # Done.
        # ---
