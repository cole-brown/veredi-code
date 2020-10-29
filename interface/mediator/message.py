# coding: utf-8

'''
Veredi Mediator Message.

For a server mediator (e.g. WebSockets) talking to a game.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, NewType, Mapping)
if TYPE_CHECKING:
    from veredi.interface.mediator.context import UserConnToken


from abc import ABC, abstractmethod
import multiprocessing
import multiprocessing.connection
import asyncio
import enum
import contextlib


import veredi.logger.log
from veredi.security               import abac
from veredi.data.codec.encodable   import Encodable
from veredi.data.exceptions        import EncodableError
from veredi.base.identity          import MonotonicId
from veredi.data.identity          import UserId, UserKey
from veredi.game.ecs.base.identity import EntityId


from ..user                        import User
from .const                        import MsgType
from .payload.base                 import BasePayload
from .payload.logging              import LogPayload


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# ------------------------------
# Types
# ------------------------------
MsgIdTypes = NewType('MsgIdTypes',
                     Union[None, MonotonicId, 'Message.SpecialId', int])


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Message(Encodable):
    '''
    Message object between game and mediator.

    Saves id as an int. Casts back to ID type in property return.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    @enum.unique
    class SpecialId(Encodable, enum.IntEnum):
        '''
        Super Special Message IDs for Super Special Messages!
        '''

        INVALID = 0
        '''Ignore me.'''

        CONNECT = enum.auto()
        '''
        Client -> Server: Hello / Auth / Register-Me-Please.
        Server -> Client: Result.

        OR Server -> Game: This client has connected.
        '''

        # ------------------------------
        # Encodable API (Codec Support)
        # ------------------------------

        def encode(self) -> Mapping[str, int]:
            '''
            Returns a representation of ourself as a dictionary.
            '''
            encoded = super().encode()
            encoded['spid'] =  self.value
            return encoded

        @classmethod
        def decode(klass: 'Message.SpecialId',
                   mapping: Mapping[str, int]) -> 'Message.SpecialId':
            '''
            Turns our encoded dict into an enum value..
            '''
            klass.error_for(mapping, keys=['spid'])
            decoded_value = mapping['spid']
            return klass(decoded_value)

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        self._msg_id:     MsgIdTypes = None
        '''
        ID for message itself. Can be initialized as None, but messages must be
        sent with a non-None message id.
        '''

        self._type:       'MsgType'          = MsgType.IGNORE
        '''
        Message's Type. Determines how Mediators handle the message itself and
        its payload.
        '''

        self._entity_id:  Optional[EntityId] = None
        '''
        The specific entity related to the message, if there is one.

        E.g. if a skill roll happens, it will be assigned the EntityId of the
        entity used to roll the skill.

        Or if some sort of not-tied-to-an-entity message, it will be None.
        '''

        self._user_id:    Optional[UserId]   = None
        '''
        The UserId this message will be sent to. Can be None if not set yet, or
        if broadcast maybe?
        # TODO: is this None, or something else, for broadcast?
        '''

        self._user_key:   Optional[UserId]   = None
        '''
        The UserKey this message will be sent to. Should only be set if
        _user_id is also set. Can be None if not set yet, or if broadcast
        maybe?
        # TODO: is this None, or something else, for broadcast?
        '''

        self._payload:    Optional[Any]      = None
        '''
        The actual important part of the message: what's in it.
        '''

    def __init__(self,
                 msg_id:    Union[MonotonicId, SpecialId, int, None],
                 type:      'MsgType',
                 payload:   Optional[Any]      = None,
                 entity_id: Optional[EntityId] = None,
                 user_id:   Optional[UserId]   = None,
                 user_key:  Optional[UserKey]  = None) -> None:
        self._define_vars()

        self._msg_id    = msg_id
        self._type      = type
        self._entity_id = entity_id
        self._user_id   = user_id
        self._user_key  = user_key
        self._payload   = payload

    # -------------------------------------------------------------------------
    # General MsgType Init Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def connected(klass:   'Message',
                  msg:     'Message',
                  id:      UserId,
                  key:     UserKey,
                  success: bool,
                  payload: Union[Any, str, None] = None) -> 'Message':
        '''
        Creates a MsgType.ACK_CONNECT message reply for success/failure of
        connection.
        '''
        if payload:
            raise NotImplementedError("TODO: Need to take success/fail "
                                      "payload generation out of here, "
                                      "I think...")

        if success:
            return klass(msg.msg_id, MsgType.ACK_CONNECT,
                         payload={'text': 'Connected.',
                                  'code': True},
                         user_id=id,
                         user_key=key)

        return klass(msg.msg_id, MsgType.ACK_CONNECT,
                     payload={'text': 'Failed to connect.',
                              'code': False},
                     user_id=id,
                     user_key=key)

    @classmethod
    def codec(klass:   'Message',
              msg:     'Message',
              payload: Union[Any, str]) -> 'Message':
        '''
        Create a 'codec' Message from this message by using `msg` for all
        fields (except `self._payload`, `self._type`), then `payload` for the
        new Message instance's payload (string if encoded, whatever if
        decoded).
        '''
        return klass(msg.msg_id, MsgType.CODEC,
                     payload=payload,
                     user_id=msg.user_id,
                     user_key=msg.user_key)

    @classmethod
    def echo(klass: 'Message',
             msg:   'Message') -> 'Message':
        '''
        Create an echo reply for this message.
        '''
        # Return same message but with type changed to ECHO_ECHO.
        return klass(msg.msg_id, MsgType.ECHO_ECHO,
                     payload=msg.payload,
                     user_id=msg.user_id,
                     user_key=msg.user_key)

    # -------------------------------------------------------------------------
    # Logging MsgType Init Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def log(klass:       'Message',
            msg_id:      Union[MonotonicId, int],
            user_id:     Optional[UserId],
            user_key:    Optional[UserKey],
            log_payload: LogPayload) -> 'Message':
        '''
        Creates a LOGGING message with the supplied data.
        '''
        msg = Message(msg_id, MsgType.LOGGING,
                      user_id=user_id,
                      user_key=user_key,
                      payload=log_payload)
        return msg

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def msg_id(self) -> Union[MonotonicId, SpecialId]:
        '''
        Return our msg_id as a MonotonicId or SpecialId.
        '''
        return self._msg_id
        # # If a SpecialId type of message, return it as SpecialId.
        # if self.type == MsgType.CONNECT or self.type == MsgType.ACK_CONNECT:
        #     return Message.SpecialId(self._id)

        # return MonotonicId(self._id, allow=True)

    @property
    def type(self) -> 'MsgType':
        '''
        Return our message type.
        '''
        return self._type

    @property
    def entity_id(self) -> Optional[EntityId]:
        '''
        Return our message's EntityId, if any.
        '''
        return self._entity_id

    @entity_id.setter
    def entity_id(self, value: Optional[EntityId]) -> None:
        '''
        Sets or clears the message's EntityId.
        '''
        self._entity_id = value

    @property
    def user_id(self) -> Optional[UserId]:
        '''
        Return our message's UserId, if any.
        '''
        return self._user_id

    @user_id.setter
    def user_id(self, value: Optional[UserId]) -> None:
        '''
        Sets or clears the message's UserId.
        '''
        self._user_id = value

    @property
    def user_key(self) -> Optional[UserId]:
        '''
        Return our message's UserKey, if any.
        '''
        return self._user_key

    @user_key.setter
    def user_key(self, value: Optional[UserId]) -> None:
        '''
        Sets or clears the message's UserKey.
        '''
        self._user_key = value

    @property
    def payload(self) -> Optional[Any]:
        '''
        Return our message payload.
        '''
        return self._payload

    @payload.setter
    def payload(self, value: str) -> None:
        '''
        Replace payload with its encoded/decoded equal. Should only really be
        used by e.g. CODEC messages for replacing an object/str with its
        encoded str/decoded object.
        '''
        self._payload = value

    @property
    def path(self) -> Optional[str]:
        '''
        Returns a path str or None, based on MsgType.

        # TODO [2020-07-29]: Also based on other things? Payload...
        '''
        if self._type == MsgType.PING:
            return 'ping'
        elif (self._type == MsgType.ECHO
              or self._type == MsgType.ECHO_ECHO):
            return 'echo'
        elif self._type == MsgType.TEXT:
            return 'text'
        elif (self._type == MsgType.ENCODED
              or self._type == MsgType.CODEC):
            return 'encoded'
        elif self._type == MsgType.LOGGING:
            return 'logging'

        return None

    # -------------------------------------------------------------------------
    # Encodable API
    # -------------------------------------------------------------------------

    def encode(self) -> Mapping[str, str]:
        '''
        Returns a representation of ourself as a dictionary.
        '''
        # Get the base dict from Encodable.
        encoded = super().encode()

        payload = self.payload
        if isinstance(payload, Encodable):
            payload = payload.encode()

        # Add all our actual fields.
        encoded.update({
            'msg_id':   self._msg_id.encode(),
            'type':     self._type.encode(),
            'payload':  payload,
            'user_id':  (self._user_id.encode()
                         if self._user_id
                         else None),
            'user_key': (self._user_key.encode()
                         if self._user_key
                         else None),
        })

        return encoded

    @classmethod
    def decode(klass: 'Message', mapping: Mapping[str, str]) -> 'Message':
        '''
        Returns a representation of ourself as a dictionary.
        '''
        klass.error_for(mapping, keys=[
            'msg_id',
            'type',
            'payload',
            'user_id',
            'user_key',
        ])

        msg_id = mapping['msg_id']
        msg_id_dec = None
        try:
            msg_id_dec = MonotonicId.decode(msg_id)
        except EncodableError:
            try:
                msg_id_dec = klass.SpecialId.decode(msg_id)
            except EncodableError:
                msg_id_dec = msg_id
                veredi.logger.log.warning("Unknown Message Id type? Not sure "
                                          f"about decoding... {msg_id}")

        # Let these be None if they were encoded as None?..
        user_id = None
        user_key = None
        entity_id = None
        if 'user_id' in mapping and mapping['user_id'] is not None:
            user_id = UserId.decode(mapping['user_id'])
        if 'user_key' in mapping and mapping['user_key'] is not None:
            user_key = UserKey.decode(mapping['user_key'])
        if 'entity_id' in mapping and mapping['entity_id'] is not None:
            entity_id = EntityId.decode(mapping['entity_id'])

        decoded = klass(
            msg_id_dec,
            MsgType.decode(mapping['type']),
            # Let someone else figure out if payload needs decoding or not, and
            # by what.
            payload=mapping['payload'],
            entity_id=entity_id,
            user_id=user_id,
            user_key=user_key,
        )

        return decoded

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self):
        return (
            f"{self.__class__.__name__}"
            f"[{self.msg_id}, "
            f"{self.type}, "
            f"{self.user_id}, "
            f"{self.user_key}]("
            f"{type(self.payload)}: "
            f"{str(self.payload)})"
        )

    def __repr__(self):
        return (
            "<Msg["
            f"{repr(self.msg_id)},"
            f"{repr(self.type)}, "
            f"{self.user_id}, "
            f"{self.user_key}]"
            f"({repr(self.payload)})>"
        )


# -----------------------------------------------------------------------------
# Message for Connecting/Disconnecting Users
# -----------------------------------------------------------------------------

class ConnectionMessage(Message):
    '''
    Mediator -> Game message for a connecting or disconnecting client.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 connected:  bool,
                 user_id:    Optional[UserId],
                 user_key:   Optional[UserKey],
                 connection: 'UserConnToken') -> None:
        # Type will be CONNECT or DISCONNECT, depending.
        msg_type = (MsgType.CONNECT
                    if connected else
                    MsgType.DISCONNECT)

        # Init base class with our data. `connection` token will be the
        # payload.
        super().__init__(ConnectionMessage.SpecialId.CONNECT,
                         msg_type,
                         connection, None,
                         user_id, user_key)

    @classmethod
    def connected(klass:      'ConnectionMessage',
                  user_id:    UserId,
                  user_key:   Optional[UserKey],
                  connection: 'UserConnToken'
                  ) -> 'ConnectionMessage':
        '''
        Create a "connected" version of a ConnectionMessage.
        '''
        return ConnectionMessage(True, user_id, user_key, connection)

    @classmethod
    def disconnected(klass:      'ConnectionMessage',
                     user_id:    Optional[UserId],
                     user_key:   Optional[UserKey],
                     connection: 'UserConnToken'
                     ) -> 'ConnectionMessage':
        '''
        Create a "disconnected" version of a ConnectionMessage.
        '''
        return ConnectionMessage(False, user_id, user_key, connection)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def connection(self) -> 'UserConnToken':
        '''
        Get connection token from message.
        '''
        return self.payload

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def user(self) -> User:
        '''
        Create a User instance with our Connection information.
        '''
        return User(self.user_id, self.user_key, self.connection)
