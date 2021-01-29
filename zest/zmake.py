# coding: utf-8

'''
Helper for unit test data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any
import pathlib

from veredi                    import run
from veredi.base               import label
from veredi.logger             import log
from veredi.data.config.config import Configuration

from .                         import zpath, zonfig


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

def config(test_type:     zpath.TestType                 = zpath.TestType.UNIT,
           rules:         Optional[label.LabelInput]     = None,
           game_id:       Optional[Any]                  = None,
           config_path:   Union[pathlib.Path, str, None] = None
           ) -> Configuration:
    '''
    Creates a configuration with the requested `config_path` config file path.
    If the `config_path` is Falsy, uses with input filename.

    Passes `rules` and `test_type` to zonfig.rules() to get final rules DotStr.

    If no `config_path`, gets a default filename via `zpath.config_filename()`.
    Uses `zpath.config()` to resolve the full config path from input/default.
    '''
    # TODO: group logging for: "if unit_test AND <group> will output..."
    log.debug(("zmake.config({test_type}): INPUTS: "
               f"rules: {rules}, "
               f"game_id: {game_id}, "
               f"config_path: {config_path}"))

    rules = zonfig.rules(test_type, rules)

    config_id = zpath.config_id(test_type, game_id)

    path = config_path
    if not path:
        path = zpath.config_filename(test_type)

    path = zpath.config(path, test_type)
    # TODO: group logging for: "if unit_test AND <group> will output..."
    log.debug(("zmake.config({test_type}): FINAL VALUES: "
               f"rules: {rules}, "
               f"game_id: {game_id}, "
               f"config_id: {config_id}, "
               f"path: {path}"))
    config = run.configuration(rules, config_id, path)

    return config
