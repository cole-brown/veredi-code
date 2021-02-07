# coding: utf-8

'''
Base File Repository Pattern for load, save, etc. from
various backend implementations (file path, file tree, etc).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Any, Callable, Dict)
from veredi.base.null import Null, Nullable, is_null
if TYPE_CHECKING:
    from io                     import TextIOBase
    from veredi.base.context    import VerediContext


import shutil
from abc import abstractmethod

from veredi.logger              import log

from veredi.base                import paths
from veredi.base.string         import label
from veredi.data                import background
from veredi.data.context        import DataAction, BaseDataContext
from veredi.data.config.context import ConfigContext

from veredi.zest.exceptions     import UnitTestError

from ..base                     import BaseRepository


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class FileRepository(BaseRepository):

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    _SANITIZE_KEYCHAIN = ['repository', 'sanitize']
    _PATH_KEYCHAIN = ['repository', 'directory']

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

        self._root_temp: paths.Path = None
        '''
        Aboslute path to the root of this file repository's temporary
        directory. Used for unit testing and any files that aren't necessarily
        permanent (autosaves?).
        '''

        self._safing_dotted: label.DotStr = None
        '''
        Dotted string of our path safing function.
        '''

        self._bg: Dict[Any, Any] = None
        '''
        Dictionary of background context data we share with the background.
        '''

    def _configure(self,
                   context:        Optional[ConfigContext],
                   require_config: bool = True) -> None:
        '''
        Allows repos to grab anything from the config data that they need to
        set up themselves.
        '''
        # ------------------------------
        # Get Config.
        # ------------------------------
        config = background.config.config(self.__class__.__name__,
                                          self.dotted(),
                                          context,
                                          raises_error=require_config)
        if not require_config and is_null(config):
            self._log_start_up(self.dotted(),
                               "Config not required and is Null.",
                               log_minimum=log.Level.DEBUG)

        # ------------------------------
        # Game ID
        # ------------------------------
        # Grab our primary id from the context too.
        self._primary_id = ConfigContext.id(context)

        self._log_start_up(self.dotted(),
                           "Set primary-id to: {}",
                           self._primary_id,
                           log_minimum=log.Level.DEBUG)

        # ------------------------------
        # Paths
        # ------------------------------

        # ---
        # Path Safing
        # ---

        self._init_path_safing(context, require_config)

        # ---
        # Repo Paths
        # ---

        # Start at ConfigContext's path...
        self._root = ConfigContext.path(context)

        # ...and then it depends.
        if not require_config:
            # No config required. So the root is.... done.
            self._log_start_up(self.dotted(),
                               "Set root to context path: {}",
                               self._root,
                               log_minimum=log.Level.DEBUG)

        else:
            # We have a config. So add config's repo path on top of it (in case
            # it's a relative path (pathlib is smart enough to correctly handle
            # when it's not)).
            self._root = self._root / paths.cast(
                config.get_data(*self._PATH_KEYCHAIN))
            # Resolve it to turn into absolute path and remove ".."s and stuff.
            self._root = self._root.resolve()

            self._log_start_up(self.dotted(),
                               "Set root based on context and config: {}",
                               self._root,
                               log_minimum=log.Level.DEBUG)

        # Now we can set the temp root based on root.
        self._root_temp = self._path_temp()
        self._log_start_up(self.dotted(),
                           "Set root-temp to: {}",
                           self._root_temp,
                           log_minimum=log.Level.DEBUG)

        # ------------------------------
        # Background
        # ------------------------------

        # Add our data to the background context.
        self._make_background()

        self._log_start_up(self.dotted(),
                           "Made background data.",
                           log_minimum=log.Level.DEBUG)

        # ------------------------------
        # Done.
        # ------------------------------
        self._log_start_up(self.dotted(),
                           "FileRepository._configure() completed.",
                           log_minimum=log.Level.DEBUG)

    def _init_path_safing(self,
                          context:        Optional[ConfigContext],
                          require_config: bool = True) -> None:
        '''
        Set our path safing from a configuration context.

        If no context, no config, or no safing function found in config, use
        the default of `paths.safing.to_human_readable`.
        '''
        config = background.config.config(self.__class__.__name__,
                                          self.dotted(),
                                          context,
                                          raises_error=require_config)

        # Use the default if we can't figure out a setting.
        path_safing_fn = None
        path_safing_dotted = None
        if not context or not config:
            path_safing_fn, path_safing_dotted = paths.safing.default()
            self._log_start_up(self.dotted(),
                               "No context or config; using default "
                               "path-safing: '{}'",
                               path_safing_dotted,
                               log_minimum=log.Level.DEBUG)

        # But really, /most/ repos should get settings from config.
        else:
            self._log_start_up(self.dotted(),
                               "Getting path-safing from config...",
                               log_minimum=log.Level.DEBUG)
            path_safing_dotted = config.get_data(*self._SANITIZE_KEYCHAIN)
            self._log_start_up(self.dotted(),
                               "Getting path-safing registered "
                               "function '{}'...",
                               path_safing_dotted,
                               log_minimum=log.Level.DEBUG)
            path_safing_fn = config.get_registered(path_safing_dotted,
                                                   context)
            if not path_safing_fn:
                # Well - nothing more to try; this is a fail.
                msg = ("Failed to get a path-safing function "
                       "from our configuration!")
                self._log_start_up(self.dotted(),
                                   msg,
                                   path_safing_dotted,
                                   log_minimum=log.Level.ERROR)
                raise background.config.exception(context, msg)

        # Ok - set what we decided on.
        self._safing_fn = path_safing_fn
        self._safing_dotted = path_safing_dotted

        self._log_start_up(self.dotted(),
                           "Set path-safing to: '{}' {}",
                           self._safing_dotted,
                           self._safing_fn,
                           log_minimum=log.Level.DEBUG)

    def _make_background(self) -> None:
        self._bg = super()._make_background()

        self._bg[background.Name.PATH.key] = {
            'root': self.root(False),
            'temp': self.root(True),
        }
        self._bg['path-safing'] = self._safing_dotted

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

    # @property
    # def root(self) -> paths.Path:
    #     '''
    #     Returns the root of the repository.
    #     '''
    #     self._log_debug("root is: {}", self._root)
    #     return self._root

    def root(self, temp: bool = False) -> paths.Path:
        '''
        Returns either the root of the repository or the root temp dir of the
        repository.
        '''
        if temp:
            # Already have one?
            if self._root_temp:
                self._log_debug("Repo's root-temp: {}", self._root_temp)
                return self._root_temp
            # Nope; make one.
            root = self._path_temp()
            self._log_debug("Repo's path-temp: {}", root)
            return root
        self._log_debug("Repo's root: {}", self._root)
        return self._root

    # -------------------------------------------------------------------------
    # Load / Save Helpers
    # -------------------------------------------------------------------------

    @abstractmethod
    def _context_data(self,
                      context: BaseDataContext,
                      path:    paths.PathsInput
                      ) -> BaseDataContext:
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
             context: BaseDataContext) -> 'TextIOBase':
        '''
        Loads data from repository based on the context.

        Returns io stream.
        '''
        key = self._key(context)
        return self._load(key, context)

    @abstractmethod
    def _load(self,
              load_path: paths.Path,
              context:   BaseDataContext) -> 'TextIOBase':
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
             data:    'TextIOBase',
             context: BaseDataContext) -> bool:
        '''
        Saves data to the repository based on data in the `context`.

        Returns success/failure of save operation.
        '''
        key = self._key(context)
        return self._save(key, data, context)

    @abstractmethod
    def _save(self,
              load_path: paths.Path,
              data:      'TextIOBase',
              context:   BaseDataContext) -> 'TextIOBase':
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

    def _path_temp(self,
                   path_non_temp: Optional[paths.PathType] = None,
                   context:       Optional['VerediContext'] = None,
                   raise_errors:  bool = True,
                   ) -> Nullable[paths.Path]:
        '''
        Returns a path to either our temp directory, a path /in/ our temp
        directory, or Null().
        '''
        path_non_temp = (paths.cast(path_non_temp)
                         if path_non_temp else
                         None)
        path_temp = None

        # ------------------------------
        # No `self.root` Cases:
        # ------------------------------

        # No root is possible for some FileRepositories...
        # FileBareRepository was like that for a long time.
        if not self.root():
            # ------------------------------
            # Invalid.
            # ------------------------------

            # No root and no input? Gonna have a bad time.
            if not path_non_temp:
                msg = "Cannot make a temp path: no root and no path provided."
                if raise_errors:
                    error = self._error_type(context)(
                        msg,
                        data={
                            'root': self.root(),
                            'path': paths.to_str(path_non_temp),
                        })
                    raise self._log_exception(error, msg, context=context)
                else:
                    self._log_warning(msg + "root: {}, path: {}",
                                      self.root(), path_non_temp,
                                      context=context)
                return Null()

            # No root and input is relative? Can't be sure it's valid so don't
            # return anything.
            if not path_non_temp.is_absolute():
                msg = ("Cannot make a temp path: no root and provided path "
                       "is not absolute.")
                if raise_errors:
                    error = self._error_type(context)(
                        msg,
                        data={
                            'root': self.root(),
                            'path': paths.to_str(path_non_temp),
                            'absolute?': path_non_temp.is_absolute(),
                        })
                    raise self._log_exception(error, msg, context=context)
                else:
                    self._log_warning(msg + "root: {}, path: {}",
                                      self.root(), path_non_temp,
                                      context=context)
                return Null()

            # Otherwise, we have no root and an absolute path. Best we can do
            # is make sure the temp dir is in there somewhere? So... complain
            # as well.
            if self._TEMP_PATH not in path_non_temp.parts:
                msg = ("Cannot create a temp path when we have no repository "
                       f"root and '{self._TEMP_PATH}' is not in input: "
                       f"{path_non_temp}")
                if raise_errors:
                    error = self._error_type(context)(
                        msg,
                        data={
                            'root': self.root(),
                            'path': paths.to_str(path_non_temp),
                            'absolute?': path_non_temp.is_absolute(),
                        })
                    raise self._log_exception(error, msg, context=context)
                else:
                    self._log_warning(msg, context=context)
                return Null()

            # ------------------------------
            # Valid?
            # ------------------------------

            # Ok; We have:
            #   1) No root.
            #   2) Absolute input path.
            #   3) Input path with one `parts` being `self._TEMP_PATH`.
            # So... just send it back?
            path_temp = path_non_temp

        # ------------------------------
        # Normal/Expected Cases (w/ `self.root()`):
        # ------------------------------

        # We do have a root. Use it if the provided path is relative.

        # Nothing requested?
        elif not path_non_temp:
            # Provide the temp dir itself...
            path_temp = self.root() / self._TEMP_PATH

        # Specific path requested.
        else:
            path = path_non_temp

            # Make sure it's relative so it can be in our repo.
            if path.is_absolute():
                # Let this raise a ValueError if path isn't relative to root.
                path = path.relative_to(self.root())

            # It should have our `_TEMP_PATH` in it.
            path = (path
                    if self._TEMP_PATH in path.parts else
                    (self._TEMP_PATH / path))

            # And it should be rooted in the repo.
            path_temp = self.root() / path

        # ------------------------------
        # Done!
        # ------------------------------
        return path_temp

    def _path(self,
              *unsafe:  paths.PathType,
              context:  BaseDataContext,
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
        safe = self._path_safed(*unsafe, context=context)
        path = None
        if context.temp:
            path = self._path_temp(safe, context=context)
        else:
            path = self.root() / safe
        if glob:
            if context.action == DataAction.SAVE:
                msg = "Cannot glob filename when saving!"
                error = self._error_type(context)(msg,
                                                  data={
                                                      'unsafe': unsafe,
                                                      'action': context.action,
                                                      'ensure': ensure,
                                                      'glob': glob,
                                                      'path': path,
                                                  })
                raise self._log_exception(
                    error,
                    msg,
                    context=context)
            path = self._ext_glob(path)

        # Make sure the directory exists?
        if ensure and context.action == DataAction.SAVE:
            self._path_ensure(path)

        return path

    def _path_ensure(self,
                     path: paths.Path) -> None:
        '''
        Creates path's parent's path if it does not exist.

        NOTE: Currently will /not/ create path as I do not know if it is a dir
        or file component name.
        '''
        path.parent.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Path Safing
    # -------------------------------------------------------------------------

    def _path_safed(self,
                    *unsafe: paths.PathType,
                    context: Optional[BaseDataContext] = None
                    ) -> paths.Path:
        '''
        Makes `unsafe` safe with self._safing_fn.

        Combines all unsafe together and returns as one Path object.

        `context` used for Load/SaveError if no `self._safing_fn`.
        '''

        if not self._safing_fn:
            raise self._log_exception(
                self._error_type(context),
                "No path safing function set! Cannot create file paths.",
                context=context)

        path = self._safing_fn(*unsafe)
        self._log_debug(f"Unsafe: *{unsafe} -> Safe Path: {path}",
                        context=context)
        return path

    # -------------------------------------------------------------------------
    # Unit Testing Helpers
    # -------------------------------------------------------------------------

    def _ut_set_up(self) -> None:
        '''
        Ensure our unit-testing dir doesn't exist, and then create it.
        '''
        # Make sure our root /does/ exist...
        if (not self.root()
                or not self.root().exists()
                or not self.root().is_dir()):
            msg = ("Invalid root directory for repo data! It must exist "
                   "and be a directory.")
            error = UnitTestError(msg,
                                  data={
                                      'meta': self._bg,
                                      'root': paths.to_str(self.root()),
                                      'exists?': paths.exists(self.root()),
                                      'file?': paths.is_file(self.root()),
                                      'dir?': paths.is_dir(self.root()),
                                  })
            raise self._log_exception(error, msg)

        # Make sure temp path doesn't exist first... Don't want to accidentally
        # use data from a previous test.
        path = self._path_temp()
        if path.exists():
            msg = "Temp Dir Path for Unit-Testing already exists!"
            error = UnitTestError(msg,
                                  data={
                                      'meta': self._bg,
                                      'temp-path': paths.to_str(path),
                                      'exists?': paths.exists(path),
                                      'file?': paths.is_file(path),
                                      'dir?': paths.is_dir(path),
                                  })
            raise self._log_exception(error, msg)

        # And now we can create it.
        path.mkdir(parents=True)

    def _ut_tear_down(self) -> None:
        '''
        Deletes our temp directory and all files in it.
        '''
        # ---
        # Make sure our root /does/ exist...
        # ---
        if (not self.root()
                or not self.root().exists()
                or not self.root().is_dir()):
            msg = ("Invalid root directory for repo data! It must exist "
                   "and be a directory.")
            error = UnitTestError(msg,
                                  data={
                                      'meta': self._bg,
                                      'root': paths.to_str(self.root()),
                                      'exists?': paths.exists(self.root()),
                                      'file?': paths.is_file(self.root()),
                                      'dir?': paths.is_dir(self.root()),
                                  })
            raise self._log_exception(error, msg)

        # ---
        # Does temp path exist?
        # ---
        path = self._path_temp()
        if path.exists():
            # Is it a dir?
            if path.is_dir():
                # Yeah - ok; delete it and it's files now.
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
                raise self._log_exception(error, msg)

        # ---
        # Done.
        # ---
