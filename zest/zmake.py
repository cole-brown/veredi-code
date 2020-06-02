# coding: utf-8

'''
Helper for unit test data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, Optional
import pathlib

from . import zpath
from veredi.data.config.config import Configuration
from veredi.data.repository.base import BaseRepository
from veredi.data.codec.base import BaseCodec


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

def config(test_type:    zpath.TestType                 = zpath.TestType.UNIT,
           config_path:  Union[pathlib.Path, str, None] = None,
           config_repo:  Optional[BaseRepository]       = None,
           config_codec: Optional[BaseCodec]            = None,
           repo_path:    Union[pathlib.Path, str, None] = None) -> Configuration:
    '''
    Creates a configuration with the requested config file path.
    If name is Falsy, uses 'zest/config/config.testing.yaml'.
    '''
    path = config_path
    if not path:
        path = pathlib.Path('config.testing.yaml')

    path = zpath.config(path, test_type)
    config = Configuration(path, config_repo, config_codec)

    if repo_path:
        config.ut_inject(str(path),
                         ConfigDocument.CONFIG,
                         ConfigKey.GAME,
                         ConfigKey.REPO,
                         ConfigKey.DIR)

    return config
