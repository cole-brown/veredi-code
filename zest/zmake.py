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

# Config Stuff
from veredi.data.config.config   import Configuration
from veredi.data.config          import hierarchy
from veredi.data.repository.base import BaseRepository
from veredi.data.codec.base      import BaseCodec

# Meeting Stuff
from veredi.game.ecs.const       import DebugFlag
from veredi.game.ecs.base.system import Meeting
from veredi.game.ecs.time        import TimeManager
from veredi.game.ecs.event       import EventManager
from veredi.game.ecs.component   import ComponentManager
from veredi.game.ecs.entity      import EntityManager


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
                         hierarchy.Document.CONFIG,
                         'data',
                         'game',
                         'repository',
                         'directory')

    return config


# ------------------------------------------------------------------------------
# Meeting of Managers
# ------------------------------------------------------------------------------

def meeting(test_type:         zpath.TestType             = zpath.TestType.UNIT,
            configuration:     Optional[Configuration]    = None,
            time_manager:      Optional[TimeManager]      = None,
            event_manager:     Optional[EventManager]     = None,
            component_manager: Optional[ComponentManager] = None,
            entity_manager:    Optional[EntityManager]    = None,
            debug_flags:       Optional[DebugFlag]        = None) -> None:

    config    = configuration     or config(test_type)
    time      = time_manager      or TimeManager()
    event     = event_manager     or EventManager(config)
    component = component_manager or ComponentManager(config,
                                                      event)
    entity    = entity_manager    or EntityManager(config,
                                                   event,
                                                   component)

    return Meeting(time, event, component, entity, debug_flags)
