# coding: utf-8

'''
Helper for unit test data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, Optional
import pathlib

from .                                 import zpath
from veredi                            import run

from veredi.data                       import background
from veredi.debug.const                import DebugFlag

# Config Stuff
from veredi.data.config.config         import Configuration
from veredi.data.repository.base       import BaseRepository
from veredi.data.serdes.base           import BaseSerdes
from veredi.data.config.hierarchy      import Document

# Meeting Stuff
from veredi.game.ecs.time              import TimeManager
from veredi.game.ecs.event             import EventManager
from veredi.game.ecs.component         import ComponentManager
from veredi.game.ecs.entity            import EntityManager
from veredi.game.ecs.system            import SystemManager
from veredi.game.ecs.meeting           import Meeting
from veredi.game.data.manager          import DataManager
from veredi.game.data.identity.manager import IdentityManager


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
