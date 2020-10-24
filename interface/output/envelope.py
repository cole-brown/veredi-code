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
                    Set, List, Dict, NamedTuple, Iterable)
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
from veredi.data                   import background

from veredi.logger                 import log
from veredi.base.identity          import SerializableId

from veredi.game.ecs.base.identity import EntityId
from veredi.data.identity          import UserId, UserKey

from .event                        import OutputEvent, Recipient
from ..user                        import User

from ..mediator.message            import Message, MsgType
from ..mediator.payload.base       import BasePayload


# -----------------------------------------------------------------------------
# Envelope Address
# -----------------------------------------------------------------------------

class Address(NamedTuple):
    '''
    Info for translating from OutputType to Users of a specific output format
    (which is dictated by `access_level`).
    '''
    recipient:   Recipient
    access_level: 'abac.Subject'
    user:         List[User]


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
        self._recipients: Recipient = Recipient.INVALID
        '''All (validated) Recipients that we will be trying to send to.'''

        self._addresses: Dict[Recipient, Address] = {}
        '''Storage for Recipient -> user info.'''

        # # TODO: Hold multiple messages or just create on demand?
        # self._payloads: Dict[Recipient, Message] = {}
        # '''Message Payloads by each Recipient.'''
        #
        # self._message: Dict[Recipient, Message] = {}
        # '''Messages by each Recipient.'''

    def __init__(self,
                 event: OutputEvent
                 # TODO: SecurityContext?
                 ) -> None:

        self._define_vars()

        self._event = event

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def context(self) -> Optional['VerediContext']:
        '''
        Returns the envelope's intended recipient flags. These are what the
        data source told us were acceptable recipients for the data.
        '''
        return self._event.context

    @property
    def desired_recipients(self) -> Optional[Recipient]:
        '''
        Returns the envelope's intended recipient flags. These are what the
        data source told us were acceptable recipients for the data.
        '''
        return self._event.desired_recipients

    @property
    def valid_recipients(self) -> Optional[Recipient]:
        '''
        Returns the envelope's validated recipient flags. These are what we
        have had verified/authorized by an external source and been reported
        the results of.
        '''
        return self._recipients

    @valid_recipients.setter
    def valid_recipients(self, value: Recipient) -> None:
        '''
        Sets the envelope's validated recipient flags. These are expected to be
        verified/authorized by an external source before this is set.
        '''
        self._recipients = value

    @property
    def data(self) -> Optional[Any]:
        '''
        Returns the envelope's raw data (not Message or Payload - just the data
        that will be used to build payloads and then messages).
        '''
        return self._event.output

    @property
    def source_id(self) -> EntityId:
        '''
        Returns the EntityId of the envelope's raw data's "owner" - the primary
        entity who should know all the Top Secret things about the data if
        there are any.
        '''
        return self._event.source_id

    @property
    def id(self) -> SerializableId:
        '''
        Returns the OutputEvent's `serial_id`. Probably an id pass all the way
        from input.
        '''
        return self._event.serial_id

    # -------------------------------------------------------------------------
    # Addresses
    # -------------------------------------------------------------------------

    def address(self, recipient: Recipient) -> Optional[Address]:
        '''
        Returns Address entry for recipient, or None if not found.
        '''
        # ---
        # Sanity Checks
        # ---
        if not recipient.is_solo:
            err_msg = ("Recipient must be a single receipient value."
                       f"Got: '{recipient}'")
            error = ValueError(err_msg, recipient)
            raise log.exception(error,
                                None,
                                err_msg)

        return self._addresses.get(recipient, None)

    def set_address(self,
                    recipient:    Recipient,
                    access_level: 'abac.Subject',
                    users:        Iterable[User]) -> None:
        '''
        Set/overwrite an address for the recipient.
        '''
        # ---
        # Sanity Checks
        # ---
        if not recipient.is_solo:
            err_msg = ("Recipient must be a single receipient value."
                       f"Got: '{recipient}'")
            error = ValueError(err_msg, recipient)
            raise log.exception(error,
                                None,
                                err_msg)

        address = Address(recipient, access_level, users)
        self._addresses[recipient] = address

    # -------------------------------------------------------------------------
    # Messages
    # -------------------------------------------------------------------------

    def message(self,
                recipient: Recipient,
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
            err_msg = ("Recipient must be a single receipient value."
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
