# coding: utf-8

'''
Module for auto-magical registration shenanigans.

This will be found and imported by run.registry in order to have whatever
Registries, Registrars, and Registrees this provides available at run-time.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.data.registration import config, codec
# <and/or any other registry helper modules>


# ----------------------------------------------------------------------------
# Imports: Registration
# ----------------------------------------------------------------------------

# <import whatever modules/classes/funcs needed for registration>
# from .const   import MsgType
# from .message import Message, ConnectionMessage

# from .system import MediatorSystem
# from .mediator import Mediator
# from . import websocket


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

# <call a registrar's helper functions for registering/ignoring>

# codec.register(MsgType)
# codec.register(Message.SpecialId)
# codec.register(Message)
# codec.register(ConnectionMessage)

# config.register(MediatorSystem)

# config.ignore(Mediator)
# config.ignore(websocket.mediator.WebSocketMediator)

# config.register(websocket.server.WebSocketServer)
# config.register(websocket.client.WebSocketClient)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports. Just a registration thing.
]
