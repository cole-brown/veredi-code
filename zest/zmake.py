# coding: utf-8

'''
Helper for unit test data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any
import pathlib

from .                         import zpath, zonfig
from veredi                    import run
from veredi.base               import label
from veredi.data.config.config import Configuration


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
    if test_type is zpath.TestType.FUNCTIONAL:
        print("\n")
        print("zmake.config: FUNCTIONAL TEST! \nINPUTS:")
        print(f"  rules:       {rules}")
        print(f"  game_id:     {game_id}")
        print(f"  config_path: {config_path}")

    rules = zonfig.rules(test_type, rules)

    config_id = zpath.config_id(test_type, game_id)

    path = config_path
    if not path:
        path = zpath.config_filename(test_type)

    path = zpath.config(path, test_type)
    if test_type is zpath.TestType.FUNCTIONAL:
        print("\n")
        print("zmake.config: FUNCTIONAL TEST! \nFINAL VALUES:")
        print(f"  rules:       {rules}")
        print(f"  game_id:     {game_id}")
        print(f"  config_id:   {config_id}")
        print(f"  path:        {path}")
    config = run.configuration(rules, config_id, path)

    return config
