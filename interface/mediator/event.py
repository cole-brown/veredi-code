# coding: utf-8

'''
Mediation events.

ToClient for sending messages to a user.
FromClient for received user messages.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any
import enum

from veredi.base.context           import VerediContext
from veredi.game.ecs.base.identity import EntityId
from veredi.game.ecs.event         import Event

from ..output.envelope             import Envelope


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Events
# -----------------------------------------------------------------------------

class MediatorEvent(Event):
    '''
    Base class for mediation events.
    '''

    def __init__(self,
                 entity_id: EntityId,
                 type:      Union[int, enum.Enum],
                 context:   VerediContext,
                 payload:   Any) -> None:
        self.set(entity_id, type, context, payload)

    def set(self,
            entity_id: EntityId,
            type:      Union[int, enum.Enum],
            context:   VerediContext,
            payload:   Any) -> None:
        super().set(entity_id, type, context)
        self.payload = payload

    def reset(self) -> None:
        super().reset()
        self.payload_id = None

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def _str_name(self, name: Optional[str] = None):
        name = name or self.__class__.__name__
        return f"{name}[eid:{self.id},t:{self.type}]: {self.payload}"

    def __repr_name__(self):
        return "MedEvent"


# -----------------------------------------------------------------------------
# Send Events: Server-to-Client Mediation Events
# -----------------------------------------------------------------------------

class GameToMediatorEvent(MediatorEvent):
    '''
    Event for Mediator sending to an outside source. For example, server
    sending something to a client will receive this event from the
    EventManager and prep it for sending to the client via the MediatorServer.
    '''

    def __init__(self,
                 envelope: Envelope) -> None:
        # Get values for initializing this instance.
        entity_id = envelope._event.id
        type = envelope._event.type
        context = envelope._event.context

        # Envelope itself goes into 'payload', I guess.
        super().__init__(entity_id, type, context, envelope)

    def __repr_name__(self):
        return "Game2MedEvent"


# -----------------------------------------------------------------------------
# Receive Events: Client-to-Server Mediation Events
# -----------------------------------------------------------------------------

class MediatorToGameEvent(MediatorEvent):
    '''
    Event for Mediator receiving from an outside source. For example, the
    MediatorServer receiving something from a client will cause the
    MediatorSystem to create this event to send to the EventManager.
    '''

    def __repr_name__(self):
        return "Med2GameEvent"