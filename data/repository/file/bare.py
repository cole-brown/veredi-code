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


from veredi.logger               import log

from veredi.data.config.registry import register
from veredi.data                 import background

from veredi.base                 import paths
from veredi.data.context         import DataBareContext
from veredi.data.config.context  import ConfigContext


from ...                         import exceptions
from .base                       import FileRepository


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# ----------------------------Bare File Repository-----------------------------
# --                        Load a file specifically.                        --
# -----------------------------------------------------------------------------

@register('veredi', 'repository', 'file-bare')
class FileBareRepository(FileRepository):

    _SANITIZE_KEYCHAIN = ['repository', 'sanitize']

    _REPO_NAME = 'file-bare'

    _TEMP_PATH = 'zest-temp'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 config_context: Optional[ConfigContext] = None) -> None:
        super().__init__(self._REPO_NAME, config_context)
        self._log_start_up(self.dotted(),
                           "Done with init.")

    def _configure(self,
                   context: Optional[ConfigContext]) -> None:
        '''
        Allows repos to grab anything from the config data that they need to
        set up themselves.
        '''
        # ------------------------------
        # Have Mom set us up.
        # ------------------------------
        # We must not require a Configuration object to complete our set-up...
        # A Configuration object needs /us/.
        super()._configure(context, require_config=False)

        # ------------------------------
        # FileBareRepository Set-Up
        # ------------------------------

        # # ---
        # # Optional Config! No exception:
        # # ---
        # config = background.config.config(self.__class__.__name__,
        #                                   self.dotted(),
        #                                   context,
        #                                   raises_error=False)
        # # Expect Null() if no config.

        # Nothing unique to FileBareRepository, at the moment.

        # ------------------------------
        # Done.
        # ------------------------------
        self._log_start_up(self.dotted(),
                           "Done with configuration.")

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
        if not context.key:
            raise self._log_exception(
                self._error_type(context),
                "Context must have a key: {}",
                context.key,
                context=context)

        # Get the path to the file. Should be a full path for
        # FileBareRepository.
        key = paths.cast(context.key)

        # Make sure our 'key' (path) is safe to use and is in the temp dir if
        # needed.
        key = self._path(*key.parts,
                         context=context,
                         ensure=True,
                         glob=False)

        return key

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
