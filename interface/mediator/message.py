# coding: utf-8

'''
Veredi Mediator Message.

For a server mediator (e.g. WebSockets) talking to a game.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, Mapping

from abc import ABC, abstractmethod
import multiprocessing
import multiprocessing.connection
import asyncio
import enum
import contextlib

import veredi.logger.log
from veredi.data.codec.base                    import Encodable
from veredi.data.exceptions                    import EncodableError
from veredi.base.identity                      import MonotonicId
from veredi.data.identity                      import UserId, UserKey
from veredi.interface.mediator.payload.logging import LogPayload


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

@enum.unique
class MsgType(Encodable, enum.Enum):
    '''
    A message between game and Mediator will be assigned one of these types.
    '''

    # ------------------------------
    # Testing / Non-Standard
    # ------------------------------

    IGNORE = 0
    '''Ignore me.'''

    PING = enum.auto()
    '''Requests a ping to the other end of the mediation (client/server).'''

    ECHO = enum.auto()
    '''
    Asks other end of mediation to just bounce back whatever it was given.
    '''
    ECHO_ECHO = enum.auto()
    '''
    Echo bounce-back.
    '''

    # TODO [2020-08-05]: IMPLEMENT THIS ONE!!!
    LOGGING = enum.auto()
    '''
    Instructions about logging:
      - Game can message Mediator on its side asking it to adjust logging.
      - Server game/mediator can ask client to:
          - Report current logging meta-data.
          - Adjust logging level.
          - Connect to logging server.
      - Client can obey or ignore as it sees fit.
    '''

    # ------------------------------
    # Normal Runtime Messages
    # ------------------------------

    CONNECT = enum.auto()
    '''
    Client connection request to the server. Should include user id, whatever
    else is needed to auth/register user.
    '''

    ACK_CONNECT = enum.auto()
    '''
    Special ack for connect - payload will indicate success or failure?
    '''

    ACK_ID = enum.auto()
    '''
    Acknowledge successful reception of a message with a context ID in case it
    gets a result response later.
    '''

    TEXT = enum.auto()
    '''The payload is text.'''

    # TODO [2020-08-05]: IMPLEMENT THIS ONE!!!
    ENCODED = enum.auto()
    '''The payload is already encoded somehow?'''

    # TODO [2020-08-05]: IMPLEMENT THIS ONE!!!
    CODEC = enum.auto()
    '''
    Please encode(/decode) this using your codec
    before sending(/after receiving).
    '''

    # ------------------------------
    # Encodable API (Codec Support)
    # ------------------------------

    def encode(self) -> Mapping[str, str]:
        '''
        Returns a representation of ourself as a dictionary.
        '''
        encoded = super().encode()
        encoded['msg_type'] = self.value
        return encoded

    @classmethod
    def decode(klass: 'MsgType', mapping: Mapping[str, str]) -> 'MsgType':
        '''
        Turns our encoded dict into a MsgType instance.
        '''
        klass.error_for(mapping, keys=['msg_type'])
        decoded = klass(mapping['msg_type'])
        return decoded


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Message(Encodable):
    '''
    Message object between game and mediator.

    Saves id as an int. Casts back to ID type in property return.
    '''

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

    def __init__(self,
                 msg_id:   Union[MonotonicId, SpecialId, int],
                 type:     'MsgType',
                 payload:  Optional[Any]     = None,
                 user_id:  Optional[UserId]  = None,
                 user_key: Optional[UserKey] = None) -> None:
        # init fields.
        self._msg_id:   MonotonicId      = msg_id
        self._type:     'MsgType'        = type
        self._user_id:  Optional[UserId] = user_id
        self._user_key: Optional[UserId] = user_key
        self._payload:  Optional[Any]    = payload

    # ------------------------------
    # Helpers
    # ------------------------------

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

    # ------------------------------
    # Properties
    # ------------------------------

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

    # ------------------------------
    # Codec Support
    # ------------------------------

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
        if mapping['user_id'] is not None:
            user_id = UserId.decode(mapping['user_id'])
        if mapping['user_key'] is not None:
            user_key = UserKey.decode(mapping['user_key'])

        decoded = klass(
            msg_id_dec,
            MsgType.decode(mapping['type']),
            # Let someone else figure out if payload needs decoding or not, and
            # by what.
            mapping['payload'],
            user_id,
            user_key
        )

        return decoded

    # ------------------------------
    # Logging
    # ------------------------------

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

    # ------------------------------
    # To String
    # ------------------------------

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
