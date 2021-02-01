# coding: utf-8

'''
Base File Repository Pattern for load, save, etc. from
various backend implementations (file path, file tree, etc).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type, Dict)
if TYPE_CHECKING:
    from veredi.data.config.context import ConfigContext
    from io                         import TextIOBase

from abc import ABC, abstractmethod


import shutil


from veredi.logger          import log

from veredi.base            import paths
from veredi.data            import background
from veredi.data.context    import DataAction, DataContext

from veredi.zest.exceptions import UnitTestError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class FileRepository(ABC):

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        super()._define_vars()

        self._root: paths.Path = None
        '''Aboslute path to the root of this file repository.'''

        self._bg: Dict[Any, Any] = None
        '''
        Dictionary of background context data we share with the background.
        '''

    def _configure(self,
                   context: Optional[ConfigContext]) -> None:
        '''
        Allows repos to grab anything from the config data that they need to
        set up themselves.
        '''
        config = background.config.config(self.__class__.__name__,
                                          self.dotted(),
                                          context)

        # Grab our primary id from the context too.
        self._primary_id = ConfigContext.id(context)  # or config.primary_id?

        # Set up our path safing too...
        path_safing_fn = None
        path_safing = config.get_data(*self._SANITIZE_KEYCHAIN)
        if path_safing:
            path_safing_fn = config.get_registered(path_safing,
                                                   context)
        self.fn_path_safing = path_safing_fn or paths.safing.to_human_readable

        # Add our data to the background context.
        self._make_background(path_safing)

        self._log_start_up(self.dotted(),
                           "Set path-safing to: {}",
                           self.fn_path_safing,
                           log_minimum=log.Level.DEBUG)

    def _make_background(self, safing_dotted: str) -> None:
        self._bg = super()._make_background()

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
    # Properties
    # -------------------------------------------------------------------------

    @property
    def root(self) -> paths.Path:
        '''
        Returns the root of the repository.
        '''
        self._log_debug("root is: {}", self._root)
        return self._root

    # -------------------------------------------------------------------------
    # Load / Save Helpers
    # -------------------------------------------------------------------------

    @abstractmethod
    def _context_data(self,
                      context: DataContext,
                      path:    paths.PathsInput
                      ) -> DataContext:
        '''
        Inject our repository, path, and any other desired data into the
        context. In the case of file repositories, include the file path.
        '''
        raise NotImplementedError(f"{self.__class__.__name__}._context_data() "
                                  "is not implemented.")

    # -------------------------------------------------------------------------
    # Load Methods
    # -------------------------------------------------------------------------

    def load(self,
             context: DataContext) -> TextIOBase:
        '''
        Loads data from repository based on the context.

        Returns io stream.
        '''
        key = self._key(context, DataAction.LOAD)
        return self._load(key, context)

    @abstractmethod
    def _load(self,
              load_path: paths.Path,
              context:   DataContext) -> TextIOBase:
        '''
        Base class adds our `_context_data()` to the context; sub-classes
        should finish the implementation.

        Looks for file at load_path. If it exists, loads that file.
        '''
        self._context_data(context, load_path)

        # Sub-class must do the rest.
        pass

    # -------------------------------------------------------------------------
    # Save Methods
    # -------------------------------------------------------------------------

    def save(self,
             data:    TextIOBase,
             context: DataContext) -> bool:
        '''
        Saves data to the repository based on data in the `context`.

        Returns success/failure of save operation.
        '''
        key = self._key(context)
        return self._save(key, data, context)

    @abstractmethod
    def _save(self,
              load_path: paths.Path,
              context:   DataContext) -> TextIOBase:
        '''
        Base class adds our `_context_data()` to the context; sub-classes
        should finish the implementation.

        Save `data` to `save_path`. If it already exists, overwrites that file.
        '''
        self._context_data(context, load_path)

        # We could have some check here if we don't want to overwrite...
        # if save_path.exists():
        #     raise self._log_exception(
        #         self._error_type(context),
        #         "Cannot save file without overwriting. "
        #         "Path/file already exist: {}",
        #         str(save_path),
        #         context=context)

        # Sub-class must do the rest.
        pass

    # -------------------------------------------------------------------------
    # Path Helpers
    # -------------------------------------------------------------------------

    def _ext_glob(self, element: paths.PathType) -> paths.Path:
        '''Concatenates extensions glob onto paths.Path/str.'''
        # Convert to a path, then adjust suffix.
        path = paths.cast(element)
        return path.with_suffix(".*")

    def _path(self,
              unsafe:   paths.PathType,
              context:  DataContext,
              ensure:   bool = True,
              glob:     bool = False) -> paths.Path:
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
                     path: paths.Path) -> None:
        '''
        Creates path's parent path if it does not exist.
        '''
        path.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Path Safing
    # -------------------------------------------------------------------------

    def _path_safed(self,
                    *unsafe: paths.PathType,
                    context: Optional[DataContext] = None
                    ) -> paths.Path:
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
