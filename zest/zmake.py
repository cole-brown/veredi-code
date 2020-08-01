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
from veredi.data import background

# Config Stuff
from veredi.data.config.config    import Configuration
from veredi.data.repository.base  import BaseRepository
from veredi.data.codec.base       import BaseCodec
from veredi.data.config.hierarchy import Document

# Meeting Stuff
from veredi.game.ecs.const        import DebugFlag
from veredi.game.ecs.time         import TimeManager
from veredi.game.ecs.event        import EventManager
from veredi.game.ecs.component    import ComponentManager
from veredi.game.ecs.entity       import EntityManager
from veredi.game.ecs.system       import SystemManager
from veredi.game.ecs.meeting      import Meeting


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

def config(test_type:    zpath.TestType                 = zpath.TestType.UNIT,
           config_path:  Union[pathlib.Path, str, None] = None,
           config_repo:  Optional[BaseRepository]       = None,
           config_codec: Optional[BaseCodec]            = None,
           repo_dotted:  Optional[str]                  = None,
           repo_path:    Union[pathlib.Path, str, None] = None,
           repo_clean:   Optional[str]                  = None,
           ) -> Configuration:
    '''
    Creates a configuration with the requested config file path.
    If name is Falsy, uses 'zest/config/config.testing.yaml'.

    `repo_dotted` will be injected into config as the game repo registry name.
    `repo_path` will be injected into config as the game repo path.
    `repo_clean` will be injected into config as the game repo sanitize fn.
    '''
    path = config_path
    if not path:
        path = pathlib.Path('config.testing.yaml')

    path = zpath.config(path, test_type)
    config = Configuration(path, config_repo, config_codec)

    # Inject specific codec for unit test.
    if repo_dotted:
        config.ut_inject(repo_dotted,
                         Document.CONFIG,
                         'data',
                         'game',
                         'repository',
                         'type')

    if repo_path:
        config.ut_inject(str(repo_path),
                         Document.CONFIG,
                         'data',
                         'game',
                         'repository',
                         'directory')

    if repo_clean:
        config.ut_inject(repo_clean,
                         Document.CONFIG,
                         'data',
                         'game',
                         'repository',
                         'sanitize')

    return config


# -----------------------------------------------------------------------------
# Meeting of Managers
# -----------------------------------------------------------------------------

def meeting(
        test_type:         zpath.TestType             = zpath.TestType.UNIT,
        configuration:     Optional[Configuration]    = None,
        time_manager:      Optional[TimeManager]      = None,
        event_manager:     Optional[EventManager]     = None,
        component_manager: Optional[ComponentManager] = None,
        entity_manager:    Optional[EntityManager]    = None,
        system_manager:    Optional[EntityManager]    = None,
        debug_flags:       Optional[DebugFlag]        = None) -> None:
    '''
    Creates a Meeting of EcsManagers using inputs, or creating defaults for
    things that aren't provided.

    If no configuration, uses zmake.config(test_type)
    '''
    configuration = configuration     or config(test_type)
    time          = time_manager      or TimeManager()
    event         = event_manager     or EventManager(configuration)
    component     = component_manager or ComponentManager(configuration,
                                                          event)
    entity        = entity_manager    or EntityManager(configuration,
                                                       event,
                                                       component)
    system        = system_manager    or SystemManager(configuration,
                                                       time,
                                                       event,
                                                       component,
                                                       entity,
                                                       debug_flags)

    meeting = Meeting(time, event, component, entity, system, debug_flags)
    background.system.set_meeting(meeting)

    return meeting
