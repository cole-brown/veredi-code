# coding: utf-8

'''
Envelope for an output message. Might not contain a message (yet) - might
just contain info for making a message, or for finding/storing a future
message.

Envelope (when ready) will be passed from OutputSystem to MediatorSystem
(probably) via event.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Typing
# ---
from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type, Callable,
                    Set, List, Dict, NamedTuple)
if TYPE_CHECKING:
    from decimal                   import Decimal

    from veredi.base.context       import VerediContext
    from veredi.game.ecs.component import ComponentManager
    from veredi.game.ecs.entity    import EntityManager
    from veredi.game.ecs.manager   import EcsManager
    from veredi.security           import abac


# ---
# Code
# ---
from veredi.data                         import background

from veredi.logger                       import log
from veredi.base.const                   import VerediHealth
from veredi.data.config.registry         import register
from veredi.data.serdes.string           import StringSerdes

# Game / ECS Stuff
from veredi.game.ecs.event               import EventManager
from veredi.game.ecs.time                import TimeManager

from veredi.game.ecs.const               import (SystemTick,
                                                 SystemPriority)

from veredi.game.ecs.base.system         import System
from veredi.game.ecs.base.component      import Component
from veredi.game.ecs.base.identity       import EntityId
from veredi.game.data.identity.component import IdentityComponent
from veredi.data.identity                      import UserId, UserKey

# Input-Related Stuff?
# from ..input.context                     import InputContext
# from ..input                             import sanitize
# from ..input.parse                       import Parcel
# from ..input.command.commander           import Commander
# from ..input.history.history             import Historian
# from ..input.event                       import CommandInputEvent
# from ..input.component                   import InputComponent

# Output-Related Stuff
from .event                              import OutputEvent, OutputTarget

# Message Things
from ..mediator.message import Message, MsgType
from ..mediator.payload.base import BasePayload


# -----------------------------------------------------------------------------
# Envelope Address
# -----------------------------------------------------------------------------

class Address(NamedTuple):
    '''
    Info for translating from OutputType to specific User.
    '''
    entity_id:    Optional[EntityId]
    user_id:      UserId
    user_key:     UserKey
    access_level: 'abac.Subject'


# -----------------------------------------------------------------------------
# Message Envelope
# -----------------------------------------------------------------------------

class Envelope:
    '''
    A container for a message, with some meta-data about the message.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self):
        '''
        Instance vars with type hinting, doc strings, etc.
        '''
        # ------------------------------
        # Basic/Initial Info
        # ------------------------------
        self._event: OutputEvent = None

        # ------------------------------
        # Final Info
        # ------------------------------
        self._recipients: OutputTarget = OutputTarget.INVALID
        '''All (validated) OutputTargets that we will be trying to send to.'''

        self._addresses: Dict[OutputTarget, Address] = {}
        '''Storage for OutputTarget -> user info.'''

        # # TODO: Hold multiple messages or just create on demand?
        # self._payloads: Dict[OutputTarget, Message] = {}
        # '''Message Payloads by each OutputTarget.'''
        #
        # self._message: Dict[OutputTarget, Message] = {}
        # '''Messages by each OutputTarget.'''

    def __init__(self,
                 data_recipients_allowed: OutputTarget,
                 data_entity_id:          EntityId,
                 data:                    Optional[Any]
                 # TODO: SecurityContext?
                 ) -> None:

        self._define_vars(self)

        self._data_recipients = data_recipients_allowed
        self._data_for_payload = data

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def event_recipients(self) -> Optional[OutputTarget]:
        '''
        Returns the envelope's intended recipient flags. These are what the
        data source told us were acceptable recipients for the data.
        '''
        return self._event._recipients

    @property
    def valid_recipients(self) -> Optional[OutputTarget]:
        '''
        Returns the envelope's validated recipient flags. These are what we
        have had verified/authorized by an external source and been reported
        the results of.
        '''
        return self._recipients

    @property
    def data(self) -> Optional[Any]:
        '''
        Returns the envelope's raw data (not Message or Payload - just the data
        that will be used to build payloads and then messages).
        '''
        return self._data_for_payload

    @data.setter
    def data(self, value: Optional[Any]) -> None:
        '''
        Sets the envelope's raw data (not Message or Payload - just the data
        that will be used to build payloads and then messages).
        '''
        return self._data_for_payload

    # -------------------------------------------------------------------------
    # Addresses
    # -------------------------------------------------------------------------

    def address(self, recipient: OutputTarget) -> Optional[Address]:
        '''
        Returns Address entry for recipient, or None if not found.
        '''
        # ---
        # Sanity Checks
        # ---
        if not recipient.is_solo:
            err_msg = ("OutputTarget must be a single receipient value."
                       f"Got: '{recipient}'")
            error = ValueError(err_msg, recipient)
            raise log.exception(error,
                                None,
                                err_msg)

        return self._addresses.get(recipient, None)

    def set_address(self,
                    recipient: OutputTarget,
                    access_level: 'abac.Subject',
                    entity_id: Optional[EntityId],
                    user_id:   UserId,
                    user_key:  Optional[UserKey]) -> None:
        '''
        Set/overwrite an address for the recipient.
        '''
        # ---
        # Sanity Checks
        # ---
        if not recipient.is_solo:
            err_msg = ("OutputTarget must be a single receipient value."
                       f"Got: '{recipient}'")
            error = ValueError(err_msg, recipient)
            raise log.exception(error,
                                None,
                                err_msg)

        address = Address(entity_id, user_id, user_key, access_level)
        self._addresses[recipient] = address

    # -------------------------------------------------------------------------
    # Payloads
    # -------------------------------------------------------------------------

    def set_payload(self,
                    recipient: OutputTarget,
                    payload: Union[BasePayload, Any]) -> None:
        '''
        Set a `payload` for one or more `recipients`.
        Will just get ignored if
        '''
        raise NotImplementedError

    def payload(self,
                recipient: OutputTarget) -> Union[None, BasePayload, Any]:
        '''
        Get a `payload` for one or more `recipients`.

        Returns None if it has no payload for (all of) the `recipients` - that
        is, the individual recipient flags are considered to be AND'd together
        so if /all/ of them are not already in the envelope's
        `self.recipients`, None will be returned.
        '''
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Messages
    # -------------------------------------------------------------------------

    def message(self,
                recipient: OutputTarget,
                entity_id: Optional[EntityId],
                user_id:   UserId,
                user_key:  Optional[UserKey],
                msg_type:  MsgType) -> Optional[Message]:
        '''
        Returns the envelope's message for the requested recipient.
        Returns None if no message for that recipient.
        '''
        # ---
        # Sanity Checks
        # ---
        if not recipient.is_solo:
            err_msg = ("OutputTarget must be a single receipient value."
                       f"Got: '{recipient}'")
            error = ValueError(err_msg, recipient)
            raise log.exception(error,
                                None,
                                err_msg)

        if not user_id:
            err_msg = ("Must have a UserId value."
                       f"Got: '{user_id}'")
            error = ValueError(err_msg, user_id)
            raise log.exception(error,
                                None,
                                err_msg)

        if not msg_type.is_solo:
            err_msg = ("MsgType must be a single value."
                       f"Got: '{msg_type}'")
            error = ValueError(err_msg, msg_type)
            raise log.exception(error,
                                None,
                                err_msg)

        if (msg_type is not MsgType.GAME_AUTO
                and not MsgType.GAME_MSGS.has(msg_type)):
            err_msg = ("MsgType must be either MsgType.GAME_AUTO or one of "
                       "MsgType.GAME_MSGS' types. GAME_MSGS: "
                       f"'{MsgType.GAME_MSGS}'. Got: '{msg_type}'")
            error = ValueError(err_msg, msg_type)
            raise log.exception(error,
                                None,
                                err_msg)

        # ------------------------------
        # Build Payload
        # ------------------------------
        payload = self.payload(recipient)

        # ------------------------------
        # Build Message
        # ------------------------------
        message = Message(None,
                          msg_type,
                          payload,
                          entity_id,
                          user_id,
                          user_key)
        return message


    # def block about ordering
    #     # ------------------------------
    #     # Send to Targets /in order/.
    #     # ------------------------------
    #     # Order is: whoever can get the most info about the output should get
    #     # it first. Presumable that will be the GM(s), then the owner, then
    #     # everyone else.
    #
    #     # Highest Priority/Most(ish) Data: GM (The game master for the game
    #     # session, who is probably also the game owner.)
    #     if (envelope.target_type.has(OutputTarget.GM)
    #             and envelope.payload_type.has(OutputTarget.GM)
    #             and not sent_to.has(OutputTarget.GM)):
    #         self._send_gm(envelope)
    #         sent_to = sent_to.set(OutputTarget.GM)
    #
    #     # Second Priority/Much Data: User (entity's owner/controller player for
    #     # the game session).
    #     if (envelope.target_type.any(OutputTarget.USER)
    #             and envelope.payload_type.has(OutputTarget.USER)
    #             and not sent_to.has(OutputTarget.USER)):
    #         self._send_user(envelope)
    #         sent_to = sent_to.set(OutputTarget.USER)
    #
    #     # Last Priority: GM, Users, and anyone else connected to the game...
    #     if (envelope.target_type.any(OutputTarget.BROADCAST)
    #             and envelope.payload_type.has(OutputTarget.BROADCAST)
    #             and not sent_to.has(OutputTarget.BROADCAST)):
    #         self._send_broadcast(envelope)
    #         sent_to = sent_to.set(OutputTarget.BROADCAST)
