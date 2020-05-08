# coding: utf-8

'''Repository Pattern for a Player object. Abstract load, save, etc. from
various backend implementations (db, file, etc).

'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

#-----
# Python
#-----
from abc import ABC, abstractmethod

#-----
# File-Based
#-----
import os
import re
import hashlib

#-----
# Our Stuff
#-----
from veredi.logger import log
from veredi.data.config.registry import register
from .. import exceptions
# from ..format import json
from ..format import yaml

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------



# -----------------------------------------------------------------------------
# (Abstract) Base Class
# -----------------------------------------------------------------------------

class PlayerRepository(ABC):

    @abstractmethod
    def load_by_name(self, user, campaign, player):
        '''Gets (loads) a player from backend data store by:
          - campaign name
          - user name
          - player name
        ...may need more to pin it down..?

        '''
        pass

    def _to_context(self, user, campaign, player):
        '''Convert user-related info we have for whatever operation into a
        context object in case an error needs to throw itself off a cliff.

        '''
        context = {
            'user': user,
            'campaign': campaign,
            'player': player,
            'repository': self.__class__.__name__,
        }
        return context


@register('veredi', 'repository', 'player', 'file-tree')
class PlayerFileTree(PlayerRepository):
    # ---
    # File Revisions / Names
    # ---

    #   load user/campaign/player/0000-0000-0000-0000.json
    #   load user/campaign/player/0000-0000-0000-0001.json
    #    ...
    #   load user/campaign/player/0000-0000-0000-0999.json
    _MIN_DIFF = 0
    _MAX_DIFF = 10**16  # Ten quadrillion should be enough?..

    _DIFF_FMT_DIV = 10**4  # Get us our quad groups.
    _DIFF_FMT = "{:04d}-{:04d}-{:04d}-{:04d}.{:s}"

    # ---
    # Path Names
    # ---
    _HUMAN_SAFE = re.compile(r'[^\w\d-]')
    _REPLACEMENT = '_'

    def __init__(self, directory,
                 file_sys_safing_fn=None,
                 data_format=None):
        self.root = os.path.abspath(directory)

        # Use user-defined or set to our defaults.
        self.fn_path_safing = file_sys_safing_fn or self._to_human_readable
        self.data_format = data_format or yaml.YamlFormat()

    def __str__(self):
        return (
            f"{self.__class__.__name__}: "
            f"ext:{self.data_format.ext()} "
            f"root:{self.root}"
        )

    # --------------------------------------------------------------------------
    # Parent's Abstract Methods
    # --------------------------------------------------------------------------

    def load_by_name(self, user, campaign, player):
        '''Gets (loads) a player from backend data store by player name.'''
        path = self._to_path(user, campaign, player)
        return self._load_all(path,
                              self._to_context(user, campaign, player))

    # --------------------------------------------------------------------------
    # Unit Testing Methods
    # --------------------------------------------------------------------------

    def _load_for_unit_tests(self, path, **context):
        '''Just blindly load a single file given the path and context.'''
        return self._load_file(path,
                               context)

    # --------------------------------------------------------------------------
    # Path Safing
    # --------------------------------------------------------------------------

    def _safe_path(self, root, *args):
        '''Makes args safe with self.fn_path_safing, then joins them together
        with root path into a full path string.

        '''
        components = []
        for each in args:
            components.append(self.fn_path_safing(each))

        return os.path.join(root, *components)

    @staticmethod
    def _to_human_readable(string):
        return PlayerFileTree._HUMAN_SAFE.sub(PlayerFileTree._REPLACEMENT,
                                              string)

    @staticmethod
    def _to_hashed(string):
        return hashlib.sha256(string.encode()).hexdigest()

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------

    def _to_path(self, user, campaign, player):
        '''Convert input to path and filename.'''
        path = self._safe_path(self.root,
                               user, campaign,
                               player)
        return path

    def _to_filename(self, number):
        '''99 -> 0000-0000-0000-0099.json
        Or whatever the filename format is by now...'''
        least = number % self._DIFF_FMT_DIV
        number = number // self._DIFF_FMT_DIV

        lesser = number % self._DIFF_FMT_DIV
        number = number // self._DIFF_FMT_DIV

        greater = number % self._DIFF_FMT_DIV
        number = number // self._DIFF_FMT_DIV

        greatest = number % self._DIFF_FMT_DIV
        number = number // self._DIFF_FMT_DIV

        return self._DIFF_FMT.format(greatest, greater, lesser, least,
                                     self.data_format.ext())

    def _apply(self, data, diff):
        '''Applies a diff to the base data.

        Returns:
          Updated data. Could return diff as updated data if data is None.

        '''
        if data is None:
            return diff

        for each in diff:
            data[each] = diff[each]
        return data

    def _load_all(self, base_path, error_context):
        '''Load all data revisions from file path.'''
        data = None
        diff = None
        revision = -1

        try:
            for each in range(self._MIN_DIFF, self._MAX_DIFF):
                file_path = os.path.join(base_path,
                                         self._to_filename(each))
                # print(f"{each}: {file_path}\n  exists? {path.isfile(file_path)}")
                if not os.path.isfile(file_path):
                    # Any sequence break in revision number is an end to the
                    # revision chain.
                    break
                diff = self._load_file(file_path, error_context)
                data = self._apply(data, diff)
                revision += 1

        except exceptions.LoadError:
            data = None
            raise

        if revision == -1:
            raise exceptions.LoadError(
                f"Error loading player files - no revisions found: {base_path}",
                None,
                error_context)

        data['revision'] = revision
        return data

    def _load_file(self, path, error_context):
        '''Load a single data file from path.

        Raises:
          - exceptions.LoadError
            - wrapped error from self.data_format.load()
              - e.g. JSONDecodeError
        '''
        data = None
        with open(path, 'r') as f:
            # Can raise an error - we'll let it.
            try:
                data = self.data_format.load(f, error_context)
            except exceptions.LoadError:
                # Let this one bubble up as-is.
                data = None
                raise
            except Exception as e:
                # Complain that we found an exception we don't handle.
                # ...then let it bubble up as-is.
                log.error("Unhandled exception:", e)
                data = None
                raise

        return data


# -----------------------------------Veredi------------------------------------
# --                     Main Command Line Entry Point                       --
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    print(f"hi")
