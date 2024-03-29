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


from veredi.logs                 import log

from veredi.data                 import background

from veredi.base                 import paths
from veredi.base.strings         import label
from veredi.data.context         import DataBareContext
from veredi.data.config.context  import ConfigContext


from ...exceptions               import LoadError, SaveError
from .base                       import FileRepository


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# ----------------------------Bare File Repository-----------------------------
# --                        Load a file specifically.                        --
# -----------------------------------------------------------------------------

class FileBareRepository(FileRepository,
                         name_dotted='veredi.repository.file-bare',
                         name_string='file-bare'):

    _SANITIZE_KEYCHAIN = ['repository', 'sanitize']

    _TEMP_PATH = 'zest-temp'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 config_context: Optional[ConfigContext] = None) -> None:
        # ------------------------------
        # Config Sanity Check
        # ------------------------------
        # Don't care about a specific case: zest_bare.py.
        # In that case, the unit test is creating a config before it does
        # tests on a FileBareRepository.
        unit_testing = ConfigContext.testing(config_context)
        ut_target_class = ConfigContext.ut_get(config_context,
                                               'testing_target')
        log_config_complaint = False
        if (not unit_testing
            or (unit_testing
                and self.klass != ut_target_class)):
            # Either we aren't unit testing at all, or it's a test that's not
            # our specific unit test. Either way, we expect not to have a
            # config.
            config = background.config.config(self.klass,
                                              self.dotted,
                                              config_context,
                                              raises_error=False)
            if config:
                # Cannot log yet; haven't done _log_config()...
                log_config_complaint = True

        # ------------------------------
        # Normal Init
        # ------------------------------
        super().__init__(config_context)

        # ------------------------------
        # Now we can log complaint.
        # ------------------------------
        if log_config_complaint:
            self._log_critical(
                "{}._init_path_safing(): Expects no Configuration to "
                "exist in the background yet, but Config and Context "
                "exist. config: {}",
                self.klass,
                config,
                context=config_context)

        # ------------------------------
        # Done.
        # ------------------------------
        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              "Done with init.")

    def _configure(self,
                   context: Optional[ConfigContext]) -> None:
        '''
        Allows repos to grab anything from the config data that they need to
        set up themselves.
        '''
        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              f"{self.klass} configure...")

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
        # config = background.config.config(self.klass,
        #                                   self.dotted,
        #                                   context,
        #                                   raises_error=False)
        # # Expect Null() if no config.

        # Nothing unique to FileBareRepository, at the moment.

        # ------------------------------
        # Done.
        # ------------------------------
        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              "Done with configuration.")

    # --------------------------------------------------------------------------
    # Load / Save Helpers
    # --------------------------------------------------------------------------

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
        self._log_data_processing(self.dotted,
                                  "Getting data from context to "
                                  "create key...")
        if not context.key:
            self._log_data_processing(self.dotted,
                                      "Context must have a key: {}",
                                      context.key,
                                      context=context,
                                      success=False)
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

        self._log_data_processing(self.dotted,
                                  "Created key: {}",
                                  key,
                                  context=context,
                                  success=True)
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
        self._log_data_processing(self.dotted,
                                  "Loading '{}'...",
                                  paths.to_str(load_path),
                                  context=context)

        super()._load(load_path, context)

        # load_path should be exact - no globbing.
        if not load_path.exists():
            msg = "Cannot load file. Path/file does not exist: {}"
            self._log_data_processing(self.dotted,
                                      msg,
                                      paths.to_str(load_path),
                                      context=context,
                                      success=False)

            raise self._log_exception(
                self._error_type(context),
                msg,
                str(load_path),
                context=context)

        data_stream = None
        with load_path.open('r') as file_stream:
            self._log_data_processing(self.dotted,
                                      "Reading...",
                                      context=context)
            # Can raise an error - we'll let it.
            try:
                data_stream = StringIO(file_stream.read(None))
            except LoadError:
                self._log_data_processing(self.dotted,
                                          "Got LoadError trying to "
                                          "read file: {}",
                                          paths.to_str(load_path),
                                          context=context,
                                          success=False)
                # Let this one bubble up as-is.
                if data_stream and not data_stream.closed:
                    data_stream.close()
                data_stream = None
                raise
            except Exception as error:
                self._log_data_processing(self.dotted,
                                          "Got an exception trying to "
                                          "read file: {}",
                                          paths.to_str(load_path),
                                          context=context,
                                          success=False)

                # Complain that we found an exception we don't handle.
                # ...then let it bubble up.
                if data_stream and not data_stream.closed:
                    data_stream.close()
                data_stream = None
                raise self._log_exception(
                    self._error_type(context),
                    "Error loading data from file. context: {}",
                    context=context) from error

        self._log_data_processing(self.dotted,
                                  "Loaded file '{}'!",
                                  paths.to_str(load_path),
                                  context=context,
                                  success=True)
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
        self._log_data_processing(self.dotted,
                                  "Saving '{}'...",
                                  paths.to_str(save_path),
                                  context=context)

        super()._save(save_path, data, context)

        success = False
        with save_path.open('w') as file_stream:
            self._log_data_processing(self.dotted,
                                      "Writing...",
                                      context=context)
            # Can raise an error - we'll let it.
            try:
                # Make sure we're at the beginning of the data stream...
                data.seek(0)
                # ...and use shutils to copy the data to disk.
                shutil.copyfileobj(data, file_stream)

                # We don't have anything to easily check to return
                # success/failure...
                success = True

            except SaveError:
                self._log_data_processing(self.dotted,
                                          "Got SaveError trying to "
                                          "write file: {}",
                                          paths.to_str(save_path),
                                          context=context,
                                          success=False)

                # Let this one bubble up as-is.
                raise

            except Exception as error:
                self._log_data_processing(self.dotted,
                                          "Got an exception trying to "
                                          "write file: {}",
                                          paths.to_str(save_path),
                                          context=context,
                                          success=False)
                # Complain that we found an exception we don't handle.
                # ...then let it bubble up.
                raise self._log_exception(
                    self._error_type(context),
                    "Error saving data to file. context: {}",
                    context=context) from error

        self._log_data_processing(self.dotted,
                                  "Saved file '{}'!",
                                  paths.to_str(save_path),
                                  context=context,
                                  success=True)
        return success
