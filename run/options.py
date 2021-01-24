# coding: utf-8

'''
Options for an instance of Veredi.

Can come from command line, config file, or wherever.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any


import pathlib
import os


from veredi.logger             import log
from veredi.base               import label
from veredi.data.config.config import Configuration
from veredi.data.exceptions    import ConfigError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_DOTTED = "veredi.run.options"


_CONFIG_FILE_NAME_GLOBS = [
    'config*.yaml'
]
'''
If `configuration()` is supplied a directory as the `path`, these are the
file name globs it will look for, in order, for the configuration file.
'''


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

def configuration(rules:   label.LabelInput,
                  game_id: Any,
                  path:    pathlib.Path = None) -> Configuration:
    '''
    Find config file and parse into the Configuration object for this game.

    `rules` is the Label for the rules type, e.g. 'veredi.rules.d20.pf2'

    `game_id` is the repository identity key for the specific game.

    `path` can be either a directory or the config file path. If `path` is
    None, this looks in the current directory for the first file that matches
    the _CONFIG_FILE_NAME_GLOBS patterns.
    '''
    log_dotted = label.normalize(_DOTTED, 'configuration')
    log.start_up(log_dotted,
                 "Creating Veredi Configuration...")

    # ------------------------------
    # Sanity Checks?
    # ------------------------------
    log.start_up(
        log_dotted,
        "Checking Inputs...",
        path,
        _CONFIG_FILE_NAME_GLOBS)

    # Normalize rules to a dotted string.
    rules = label.normalize(rules)

    # game_id... dunno much about it until we get a repository for it.

    # ------------------------------
    # Figure out actual config file path from input path.
    # ------------------------------
    log.start_up(
        log_dotted,
        "Finding Config File...",
        path,
        _CONFIG_FILE_NAME_GLOBS)
    path = _config_path(log_dotted, path)

    # ------------------------------
    # Create Configuration.
    # ------------------------------
    log.start_up(
        log_dotted,
        "Creating Configuration...",
        path,
        _CONFIG_FILE_NAME_GLOBS)
    config = Configuration(rules, game_id,
                           config_path=path)

    # ------------------------------
    # Done.
    # ------------------------------
    log.start_up(log_dotted,
                 "Done creating Veredi Configuration.",
                 log_success=log.SuccessType.SUCCESS)
    return config


def _config_path(log_dotted: label.DotStr,
                 path:       pathlib.Path = None) -> pathlib.Path:
    '''
    Find config file from `path` and parse into the Configuration object for
    the game.

    `path` can be either a directory or the config file path. If `path` is
    None, this looks in the current directory for the first file that matches
    the _CONFIG_FILE_NAME_GLOBS patterns.
    '''
    # ---
    # Default path?
    # ---
    if path:
        log.start_up(log_dotted,
                     "Looking for config in provided path: {}",
                     path)

    else:
        path = pathlib.Path(os.getcwd())
        log.start_up(log_dotted,
                     "Set config path to current working directory: {}",
                     path)

    # ---
    # Sanity checks for path.
    # ---
    if not path.exists():
        msg = "Configuration path doesn't exist."
        error = ConfigError(msg,
                            data={
                                'path': str(path),
                                'exists': path.exists(),
                                'is_file': path.is_file(),
                                'is_dir': path.is_dir(),
                            })
        raise log.exception(error,
                            msg + f" path: {path}")

    if not path.is_dir() and not path.is_file():
        msg = "Configuration path must be a file or directory."
        error = ConfigError(msg,
                            data={
                                'path': str(path),
                                'exists': path.exists(),
                                'is_file': path.is_file(),
                                'is_dir': path.is_dir(),
                            })
        raise log.exception(error,
                            msg + f" path: {path}")

    # ---
    # Get config.
    # ---
    # Already checked that it's either file or dir, so:
    if path.is_dir():
        log.start_up(log_dotted,
                     "Path is a directory; look for config file "
                     "by glob: {} {}",
                     path,
                     _CONFIG_FILE_NAME_GLOBS)

        # Look for files matching the glob. Claim the first one and ignore any
        # others.
        claim = None
        for glob in _CONFIG_FILE_NAME_GLOBS:
            for match in path.glob(glob):
                if not match.is_file():
                    continue
                claim = match
                log.start_up(
                    log_dotted,
                    "Found config file '{}' by glob '{}' in directory '{}'.",
                    claim,
                    glob,
                    path,
                    _CONFIG_FILE_NAME_GLOBS,
                    log_success=log.SuccessType.SUCCESS)
                break

            if claim:
                break

        # Nothing found? Something wrong?
        if not claim or not claim.exists() or not claim.is_file():
            msg = "No config file found in supplied directory."
            error = ConfigError(msg,
                                data={
                                    'dir': str(path),
                                    'globs': _CONFIG_FILE_NAME_GLOBS,
                                    'claim': claim,
                                })
            raise log.exception(
                error,
                msg + f" dir: {str(path)}, claim: {str(claim)}")

        # Got a file to claim; set it as our path now.
        path = claim.resolve()
        log.start_up(
            log_dotted,
            "Config file path resolved to: {}",
            path,
            _CONFIG_FILE_NAME_GLOBS,
            log_success=log.SuccessType.NEUTRAL)

    # Path is a file. Not much needs done.
    else:
        path = path.resolve()
        log.start_up(log_dotted,
                     "Path is a file; resolved to: {}",
                     path,
                     log_success=log.SuccessType.NEUTRAL)

    log.start_up(log_dotted,
                 "Final path to config file: {}",
                 path,
                 log_success=log.SuccessType.SUCCESS)
    return path
