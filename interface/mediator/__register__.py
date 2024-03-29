# coding: utf-8

'''
Module for auto-magical registration shenanigans.

This will be found and imported by run.registry in order to have whatever
Registries, Registrars, and Registrees this provides available at run-time.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.data.registration import codec, config


# ----------------------------------------------------------------------------
# Imports: Registration
# ----------------------------------------------------------------------------

from .const   import MsgType
from .message import Message, ConnectionMessage

from .system import MediatorSystem
from .mediator import Mediator
from . import websocket

# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

codec.register_enum(MsgType,
                    dotted='veredi.interface.mediator.message.type',
                    name_encode='v.mt',
                    enum_encode_type=codec.enum.FlagEncodeValue)
codec.register_enum(Message.SpecialId,
                    dotted='veredi.interface.mediator.message.sid',
                    name_encode='spid',
                    enum_encode_type=codec.enum.FlagEncodeValue)

codec.register(Message)
codec.register(ConnectionMessage)

config.register(MediatorSystem)

config.ignore(Mediator)
config.ignore(websocket.mediator.WebSocketMediator)

config.register(websocket.server.WebSocketServer)
config.register(websocket.client.WebSocketClient)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
