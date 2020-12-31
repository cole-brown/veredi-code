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
           config_path:   Union[pathlib.Path, str, None] = None,
           config_repo:   Optional[BaseRepository]       = None,
           config_serdes: Optional[BaseSerdes]           = None,
           repo_dotted:   Optional[str]                  = None,
           repo_path:     Union[pathlib.Path, str, None] = None,
           repo_clean:    Optional[str]                  = None,
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
    config = Configuration(path, config_repo, config_serdes)

    # Inject specific serdes for unit test.
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
        system_manager:    Optional[SystemManager]    = None,
        data_manager:      Optional[DataManager]      = None,
        identity_manager:  Optional[IdentityManager]  = None,
        debug_flags:       Optional[DebugFlag]        = None) -> None:
    '''
    Creates a Meeting of EcsManagers using inputs, or creating defaults for
    things that aren't provided.

    If no configuration, uses zmake.config(test_type)
    '''

    # Get a config of some sort... Managers need it.
    configuration = configuration     or config(test_type)

    # Create any managers that weren't passed in.
    time          = time_manager      or TimeManager(debug_flags=debug_flags)
    event         = event_manager     or EventManager(configuration,
                                                      debug_flags)
    component     = component_manager or ComponentManager(configuration,
                                                          event,
                                                          debug_flags)
    entity        = entity_manager    or EntityManager(configuration,
                                                       event,
                                                       component,
                                                       debug_flags)
    system        = system_manager    or SystemManager(event,
                                                       debug_flags)
    data          = data_manager      or DataManager(configuration,
                                                     time,
                                                     event,
                                                     component,
                                                     debug_flags)
    identity      = identity_manager  or IdentityManager(configuration,
                                                         time,
                                                         event,
                                                         entity,
                                                         debug_flags)

    # And now we can create the meeting itself.
    meeting = Meeting(time,
                      event,
                      component,
                      entity,
                      system,
                      data,
                      identity,
                      debug_flags)

    # Save to background and return.
    mtg_bg_data, mtg_bg_owner = meeting.get_background()
    background.manager.set(meeting.dotted(),
                           meeting,
                           mtg_bg_data,
                           mtg_bg_owner)

    return meeting
