# coding: utf-8

'''
Helper for unit test data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union
import pathlib

from .                         import zpath
from veredi                    import run
from veredi.data.config.config import Configuration


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

def config(test_type:     zpath.TestType                 = zpath.TestType.UNIT,
           config_path:   Union[pathlib.Path, str, None] = None
           ) -> Configuration:
    '''
    Creates a configuration with the requested `config_path` config file path.
    If the `config_path` is Falsy, uses 'zest/config/config.testing.yaml'.
    '''
    path = config_path
    if not path:
        path = pathlib.Path('config.testing.yaml')

    path = zpath.config(path, test_type)
    config = run.configuration(path)

    return config
