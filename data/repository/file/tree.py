# coding: utf-8

'''
Base Repository Pattern for load, save, etc. from
various backend implementations (db, file, etc).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, List


import shutil
import re
from io import StringIO, TextIOBase


from veredi.logger               import log

from veredi.data.config.registry import register
from veredi.data                 import background

from veredi.base                 import paths
from veredi.data.context         import (DataAction,
                                         DataGameContext,
                                         DataLoadContext,
                                         DataSaveContext)
from veredi.data.config.context  import ConfigContext


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

        self._log_start_up(self.dotted(),
                           "Set root to: {}",
                           self.root,
                           log_minimum=log.Level.DEBUG)

        self._log_start_up(self.dotted(),
                           "Done with configuration.")

    # -------------------------------------------------------------------------
    # Load / Save Helpers
    # -------------------------------------------------------------------------

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
        super()._load(path, context)

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

    def _save(self,
              save_path: paths.PathType,
              data:      TextIOBase,
              context:   DataSaveContext) -> bool:
        '''
        Save `data` to `save_path`. If it already exists, overwrites that file.
        '''
        super()._save(save_path, data, context)

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
