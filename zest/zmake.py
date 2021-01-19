# coding: utf-8

'''
Helper for unit test data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any
import pathlib

from .                         import zpath
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
           rules:         Optional[label.Label]          = None,
           game_id:       Optional[Any]                  = None,
           config_path:   Union[pathlib.Path, str, None] = None
           ) -> Configuration:
    '''
    Creates a configuration with the requested `config_path` config file path.
    If the `config_path` is Falsy, uses 'zest/config/config.testing.yaml'.
    '''
    if not rules:
        rules = 'veredi.rules.d20.pf2'

    if not game_id:
        game_id = 'test-campaign'

    path = config_path
    if not path:
        path = pathlib.Path('config.testing.yaml')

    path = zpath.config(path, test_type)
    config = run.configuration(rules, game_id, path)

    return config
