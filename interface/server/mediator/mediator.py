# coding: utf-8

'''
Veredi Server I/O Mediator.

For a server (e.g. REST) talking to a game.

For input, the mediator takes in JSON and converts it into an InputEvent for
the InputSystem.

For output, the mediator receives an OutputEvent from the OutputSystem and
converts it into JSON for sending.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Type Hinting Imports
# ---
from typing import Union, Mapping


# ---
# Python Imports
# ---
import pathlib


# ---
# Veredi Imports
# ---
from veredi.logger                      import log
from veredi.data.exceptions                   import ConfigError
from veredi.data.config.config    import Configuration
from veredi.data.codec.base import BaseCodec


from veredi.game.engine                 import Engine  # , EngineLifeCycle
from veredi.game.ecs.const              import DebugFlag



from veredi.base.null                   import Null
from veredi.base.const                  import VerediHealth
from veredi.zest                        import zload
from veredi.zest.zpath                  import TestType
from veredi.game.ecs.const              import DebugFlag
from veredi.base.context                import VerediContext, UnitTestContext
from veredi.game.ecs.base.system        import System
from veredi.game.ecs.base.entity        import (Entity,
                                                EntityLifeCycle)
from veredi.game.ecs.base.identity      import EntityId
from veredi.game.ecs.base.component     import (Component,
                                                ComponentLifeCycle)
from veredi.game.ecs.event              import Event
from veredi.game.data.event             import DataLoadedEvent
from veredi.game.ecs.meeting            import Meeting

from veredi.interface.input.system      import InputSystem
from veredi.interface.input.command.reg import CommandRegistrationBroadcast

from veredi.interface.output.system     import OutputSystem


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Mediator:
    '''
    Veredi Server I/O Mediator.

    For a server (e.g. REST) talking to a game.

    For input, the mediator takes in JSON and converts it into an InputEvent
    for the InputSystem.

    For output, the mediator receives an OutputEvent from the OutputSystem and
    converts it into JSON for sending.
    '''

    def __init__(self,
                 config: Configuration) -> None:
        '''
        Initialize the mediator.
        '''
        self._codec: BaseCodec = config.make(None,
                                             'server',
                                             'mediator',
                                             'codec')
