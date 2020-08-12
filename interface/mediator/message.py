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

from veredi.data.codec.base    import Encodable
from veredi.base.identity      import MonotonicId, SerializableId
import veredi.logger.log


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
          - Adjust logging level.
          - Connect to logging server.
      - Client can obey or ignore as it sees fit.
    '''

    # ------------------------------
    # Normal Runtime Messages
    # ------------------------------

    CONNECT = enum.auto()
    '''
    Client connection request to the server. Should include user key, whatever
    else is needed to auth/register user.
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
        encoded = {
            'msg-type': self.value,
        }
        return encoded

    @classmethod
    def decode(klass: 'MsgType', value: Mapping[str, str]) -> 'MsgType':
        '''
        Turns our encoded dict into a MsgType instance.
        '''
        decoded = klass(value['msg-type'])
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
    class SpecialId(enum.IntEnum):
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

    def __init__(self,
                 id:      Union[MonotonicId, SpecialId, int],
                 type:    'MsgType',
                 payload: Optional[Any]            = None,
                 key:     Optional[SerializableId] = None) -> None:
        # init fields.
        self._id:      int                      = int(id)
        self._type:    'MsgType'                = type
        self._key:     Optional[SerializableId] = key
        self._payload: Optional[Any]            = payload

    # ------------------------------
    # Helpers
    # ------------------------------

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
        return klass(msg.id, MsgType.CODEC, payload)

    @classmethod
    def echo(klass: 'Message',
             msg:   'Message') -> 'Message':
        '''
        Create an echo reply for this message.
        '''
        # Return same message but with type changed to ECHO_ECHO.
        return klass(msg.id, MsgType.ECHO_ECHO, msg.payload)

    # ------------------------------
    # Properties
    # ------------------------------

    @property
    def id(self) -> int:
        '''
        Return our id int as a MonotonicId.
        '''
        return MonotonicId(self._id, allow=True)

    @property
    def type(self) -> 'MsgType':
        '''
        Return our message type.
        '''
        return self._type

    @property
    def key(self) -> Optional['SerializableId']:
        '''
        Return our message's key, if any.
        '''
        return self._key

    @key.setter
    def key(self, value: Optional['SerializableId']) -> None:
        '''
        Sets or clears the message's key.
        '''
        return self._key

    @property
    def payload(self) -> Optional[Any]:
        '''
        Return our message payload.
        '''
        return self._payload

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
        msg = self.payload
        if isinstance(msg, Encodable):
            msg = msg.encode()

        # ---
        # Required
        # ---
        encoded = {
            'id': self._id,
            'type': self._type.encode(),
            'payload': msg,
        }

        # ---
        # Optional
        # ---
        if self._key:
            encoded['key'] = self.key.encode()

        return encoded

    @classmethod
    def decode(klass: 'Message', value: Mapping[str, str]) -> 'Message':
        '''
        Returns a representation of ourself as a dictionary.
        '''
        # ---
        # Required
        # ---
        decoded = klass(
            value['id'],
            MsgType.decode(value['type']),
            value['payload'],
        )

        # ---
        # Optional
        # ---
        if 'key' in value:
            decoded.key = UserId.decode(value['key'])

        return decoded

    # ------------------------------
    # Logging
    # ------------------------------

    @classmethod
    def log(klass:     'Message',
            id:        Union[MonotonicId, int],
            log_level: veredi.logger.log.Level) -> 'Message':
        '''
        Creates a LOGGING message with the supplied data.
        '''
        msg = Message(id, MsgType.LOGGING,
                      payload={
                          'logging': {
                              'level': log_level,
                          },
                      })
        return msg

    def log_level(self) -> Optional[veredi.logger.log.Level]:
        '''
        If this message has anything under 'logging.level', return it.
        '''
        try:
            return self.messagage.get('logging', {}).get('level', None)
        except:
            return None

    # ------------------------------
    # To String
    # ------------------------------

    def __str__(self):
        return (
            f"{self.__class__.__name__}"
            f"[{self.id}, "
            f"{self.type}]("
            f"{str(self.payload)}): "
        )

    def __repr__(self):
        return (
            "<Msg["
            f"{repr(self.id)},"
            f"{repr(self.type)}]"
            f"({repr(self.payload)})>"
        )
