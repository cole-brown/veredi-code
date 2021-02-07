# coding: utf-8

'''
Set-up and run a Veredi game server.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Tuple

import pathlib


from veredi.logger             import log
from veredi.base.strings       import label
from veredi.data.config.config import Configuration
# from veredi.data.exceptions  import ConfigError
from veredi.game.engine        import Engine
from veredi.debug.const        import DebugFlag

from .options                  import configuration
from .engine                   import managers, engine


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_DOTTED = "veredi.run.server"


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def server(path:        pathlib.Path = None,
           debug_flags: Optional[DebugFlag] = None
           ) -> Tuple[Configuration, Engine]:
    '''
    Start a Veredi Game Engine, ECS Managers, etc. Everything required to run a
    game server.

    Returns the configuration and the engine in a tuple.
    '''
    log_dotted = label.normalize(_DOTTED, 'server')
    log.start_up(log_dotted,
                 "Creating Veredi Server...")

    # ---
    # Find & parse config file.
    # ---
    log.start_up(log_dotted,
                 "Creating Configuration...")
    config = configuration(path)

    # ---
    # Set up ECS.
    # ---
    log.start_up(log_dotted,
                 "Creating Managers...")
    meeting = managers(config, debug_flags=debug_flags)

    # ---
    # Set game.
    # ---
    log.start_up(log_dotted,
                 "Creating Game...")
    game_engine = engine(config, meeting, debug_flags)

    # ---
    # Set up logging.
    # ---
    # TODO: log?
    # TODO: log_server?
    # TODO: log_client?

    # ---
    # Done.
    # ---
    log.start_up(log_dotted,
                 "Done Creating Veredi Server.",
                 log_success=log.SuccessType.SUCCESS)
    return config, game_engine
