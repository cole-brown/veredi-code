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

THIS_DIR = pathlib.Path(__file__).resolve().parent


# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

def config(filepath:     Union[pathlib.Path, str, None] = None,
           config_repo:  Optional[BaseRepository]       = None,
           config_codec: Optional[BaseCodec]            = None) -> Configuration:
    '''
    Creates a configuration with the requested config file path.
    If name is Falsy, uses 'zest/config/config.testing.yaml'.
    '''
    path = filepath
    if not path:
        path = pathlib.Path('config.testing.yaml')

    path = zpath.config(path)
    return Configuration(path, config_repo, config_codec)
