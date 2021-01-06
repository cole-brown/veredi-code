# coding: utf-8

'''
Set up the game engine.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, Optional


from veredi.logger                             import log
from veredi.base import label
from veredi.data                       import background
from veredi.debug.const                import DebugFlag

# Configuration Stuff
from veredi.data.config.config                 import Configuration
from veredi.data.exceptions                    import ConfigError

# Meeting Stuff
from veredi.game.ecs.time              import TimeManager
from veredi.game.ecs.event             import EventManager
from veredi.game.ecs.component         import ComponentManager
from veredi.game.ecs.entity            import EntityManager
from veredi.game.ecs.system            import SystemManager
from veredi.game.data.manager          import DataManager
from veredi.game.data.identity.manager import IdentityManager
from veredi.game.ecs.meeting           import Meeting

# Game Stuff
from veredi.game.engine                import Engine


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_DOTTED = "veredi.run.engine"


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def managers(configuration:     Configuration,
             time_manager:      Optional[TimeManager]      = None,
             event_manager:     Optional[EventManager]     = None,
             component_manager: Optional[ComponentManager] = None,
             entity_manager:    Optional[EntityManager]    = None,
             system_manager:    Optional[SystemManager]    = None,
             data_manager:      Optional[DataManager]      = None,
             identity_manager:  Optional[IdentityManager]  = None,
             debug_flags:       Optional[DebugFlag]        = None) -> Meeting:
    '''
    Creates a Meeting of EcsManagers.

    Any/all managers may be provided as arguments. If a manager is not
    provided, one will be created using the `configuration`, which must be
    provided.
    '''
    log_dotted = label.join(_DOTTED, 'managers')
    log_success = log.SuccessType.IGNORE
    log.start_up(log_dotted,
                 "Creating Meeting of EcsManagers...",
                 log_success=log_success)

    # ---
    # Sanity.
    # ---
    if not configuration:
        msg = "Configuration must be provided."
        error = ConfigError(msg,
                            data={
                                'configuration': str(configuration),
                            })
        raise log.exception(error, msg)

    # ---
    # Create Managers.
    # ---
    # Create any managers that weren't passed in.

    # Time
    time          = time_manager      or TimeManager(debug_flags=debug_flags)
    log.start_up(log_dotted, "Created TimeManager.",
                 log_success=log_success)

    # Event
    event         = event_manager     or EventManager(configuration,
                                                      debug_flags)
    log.start_up(log_dotted, "Created EventManager.",
                 log_success=log_success)

    # Component
    component     = component_manager or ComponentManager(configuration,
                                                          event,
                                                          debug_flags)
    log.start_up(log_dotted, "Created ComponentManager.",
                 log_success=log_success)

    # Entity
    entity        = entity_manager    or EntityManager(configuration,
                                                       event,
                                                       component,
                                                       debug_flags)
    log.start_up(log_dotted, "Created EntityManager.",
                 log_success=log_success)

    # System
    system        = system_manager    or SystemManager(event,
                                                       debug_flags)
    log.start_up(log_dotted, "Created SystemManager.",
                 log_success=log_success)

    # Data
    data          = data_manager      or DataManager(configuration,
                                                     time,
                                                     event,
                                                     component,
                                                     debug_flags)
    log.start_up(log_dotted, "Created DataManager.",
                 log_success=log_success)

    # Identity
    identity      = identity_manager  or IdentityManager(configuration,
                                                         time,
                                                         event,
                                                         entity,
                                                         debug_flags)
    log.start_up(log_dotted, "Created IdentityManager.",
                 log_success=log_success)

    # ---
    # Finish up.
    # ---

    # And now we can create the Manager's Meeting itself.
    meeting = Meeting(time,
                      event,
                      component,
                      entity,
                      system,
                      data,
                      identity,
                      debug_flags)
    log.start_up(log_dotted,
                 "Created Meeting of Managers.",
                 log_success=log_success)

    # Save to background and return.
    mtg_bg_data, mtg_bg_owner = meeting.get_background()
    background.manager.set(meeting.dotted(),
                           meeting,
                           mtg_bg_data,
                           mtg_bg_owner)
    log.start_up(log_dotted,
                 "Set managers into background context.",
                 log_success=log_success)

    log_success = log.SuccessType.SUCCESS
    log.start_up(log_dotted,
                 "Done Creating Meeting of EcsManagers.",
                 log_success=log_success)
    return meeting


def engine(configuration: Configuration,
           meeting:       Meeting,
           # Optional Debug Stuff:
           debug_flags:   Optional[DebugFlag] = None,
           ) -> Engine:
    '''
    Create and configure a game engine using the other supplied parameters.
    '''
    log_dotted = label.join(_DOTTED, 'engine')
    log_success = log.SuccessType.IGNORE
    log.start_up(log_dotted,
                 "Building the Engine...",
                 log_success=log_success)

    # ---
    # Sanity.
    # ---
    if not configuration:
        msg = "Configuration must be provided."
        error = ConfigError(msg,
                            data={
                                'configuration': str(configuration),
                                'meeting': str(meeting),
                            })
        raise log.exception(error, msg)

    if not meeting:
        # This shouldn't happen - should raise an error before here, right?
        msg = "Managers' Meeting must be provided."
        error = ConfigError(msg,
                            data={
                                'configuration': str(configuration),
                                'meeting': str(meeting),
                            })
        raise log.exception(error, msg)

    # ---
    # Create engine.
    # ---
    log.start_up(log_dotted,
                 "Initializing the Engine...",
                 log_success=log_success)
    owner = None
    campaign_id = None
    engine = Engine(owner,
                    campaign_id,
                    configuration,
                    meeting,
                    debug_flags)

    log_success = log.SuccessType.SUCCESS
    log.start_up(log_dotted,
                 "Done building the Engine.",
                 log_success=log_success)
    return engine
