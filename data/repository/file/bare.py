# coding: utf-8

'''
Bare Repository Pattern for load, save, etc. from a
specified file.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional


import shutil
from io import StringIO, TextIOBase


from veredi.data.config.registry import register
from veredi.data                 import background

from veredi.base                 import paths
from veredi.data.context         import DataBareContext
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

    _SANITIZE_KEYCHAIN = ['repository', 'sanitize']

    _REPO_NAME = 'file-bare'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 config_context: Optional[ConfigContext] = None) -> None:
        super().__init__(self._REPO_NAME, config_context)

    def _configure(self,
                   context: Optional[ConfigContext]) -> None:
        '''
        Allows repos to grab anything from the config data that they need to
        set up themselves.
        '''
        super()._configure(context)

        # Bare repo doesn't have a root until it loads something from
        # somewhere. Then that directory is its root.
        self._root = None

        self._log_debug("Set my root to: {}", self.root)

    # -------------------------------------------------------------------------
    # Load / Save Helpers
    # -------------------------------------------------------------------------

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
             context: DataBareContext) -> paths.Path:
        '''
        Turns load/save meta-data in the context into a key we can use to
        retrieve the data.
        '''
        self._root = context.key.parent
        # We are a FileBareRepo, and now we know our root (for the time
        # being...). Put it in our bg data.
        self._bg['path'] = self._root
        # And make sure our 'key' (path) is safe to use.
        if isinstance(context.key, paths.Path):
            return self._path_safed(*context.key.parts, context=context)

    # -------------------------------------------------------------------------
    # Load Methods
    # -------------------------------------------------------------------------

    def _load(self,
              load_path: paths.Path,
              context: DataBareContext) -> TextIOBase:
        '''
        Looks for file at load_path. If it exists, loads that file.
        '''
        super()._load(load_path, context)

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

    def _save(self,
              save_path: paths.Path,
              data:      TextIOBase,
              context:   DataBareContext) -> bool:
        '''
        Save `data` to `save_path`. If it already exists, overwrites that file.
        '''
        super()._save(save_path, data, context)

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
