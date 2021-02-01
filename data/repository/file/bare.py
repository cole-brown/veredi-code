# coding: utf-8

'''
Bare Repository Pattern for load, save, etc. from a
specified file.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional


import pathlib
import shutil
from io import StringIO, TextIOBase


from veredi.data.config.registry import register
from veredi.data                 import background

from veredi.base                 import paths
from veredi.data.context         import (DataBareContext,
                                         DataGameContext,
                                         DataLoadContext)
from veredi.data.config.context  import ConfigContext


from ..                          import exceptions
from .                           import base


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


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
        config = background.config.config(self.__class__.__name__,
                                          self.dotted(),
                                          context)

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

        self._log_debug("Set my root to: {}", self.root)
        self._log_debug("Set my path-safing to: {}", self.fn_path_safing)

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
    # Load / Save Helpers
    # -------------------------------------------------------------------------

    def _ext_glob(self, element: paths.PathType) -> paths.Path:
        '''Concatenates extensions glob onto pathlib.Path/str.'''
        # Convert to a path, then adjust suffix.
        path = paths.cast(element)
        return path.with_suffix(".*")

    @property
    def root(self) -> pathlib.Path:
        '''
        Returns the root of the repository.
        '''
        self._log_debug("root is: {}", self._root)
        return self._root

    def _context_data(self,
                      context: DataBareContext,
                      path:    paths.PathsInput
                      ) -> DataBareContext:
        '''
        Inject our repository, path, and any other desired data into the
        context. In the case of file repositories, include the file path.
        '''
        key = str(background.Name.REPO)
        meta, _ = self.background
        context[key] = {
            # Push our context data into here...
            'meta': meta,
            # And add any extra info.
            'action': context.action,
            'path': str(path),
        }
        return context

    def _key(self,
             context: DataBareContext) -> pathlib.Path:
        '''
        Turns load/save meta-data in the context into a key we can use to
        retrieve the data.
        '''
        self._root = context.key.parent
        # We are a FileBareRepo, and now we know our root (for the time
        # being...). Put it in our bg data.
        self._bg['path'] = self._root
        # And make sure our 'key' (path) is safe to use.
        if isinstance(context.key, pathlib.Path):
            return self._path_safed(*context.key.parts, context=context)

    # -------------------------------------------------------------------------
    # Load Methods
    # -------------------------------------------------------------------------

    def load(self,
             context: DataBareContext) -> TextIOBase:
        '''
        Loads data from repository based on the context.

        Returns io stream.
        '''
        key = self._key(context)
        return self._load(key, context)

    def _load(self,
              load_path: pathlib.Path,
              context: DataLoadContext) -> TextIOBase:
        '''
        Looks for file at load_path. If it exists, loads that file.
        '''
        self._context_data(context, load_path)

        # load_path should be exact - no globbing.
        if not load_path.exists():
            raise self._log_exception(
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
                raise self._log_exception(
                    self._error_type(context),
                    "Error loading data from file. context: {}",
                    context=context) from error

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
        key = self._key(context)
        return self._save(key, data, context)

    def _save(self,
              save_path: pathlib.Path,
              data:      TextIOBase,
              context:   DataBareContext) -> bool:
        '''
        Looks for file at save_path. If it exists, saves that file.
        '''
        self._context_data(context, save_path)

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
            # Can raise an error - we'll let it.
            try:
                # Make sure we're at the beginning of the data stream...
                data.seek(0)
                # ...and use shutils to copy the data to disk.
                shutil.copyfileobj(data, file_stream)

                # We don't have anything to easily check to return
                # success/failure...
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
        return path
