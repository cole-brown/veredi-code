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
from veredi.base.identity      import MonotonicId


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

    INVALID = 0
    '''Ignore me.'''

    PING = enum.auto()
    '''Requests a ping to the other end of the mediation (client/server).'''

    ECHO = enum.auto()
    '''
    Asks other end of mediation to just bounce back whatever it was given.
    '''

    # ------------------------------
    # Normal Runtime Messages
    # ------------------------------

    ACK_ID = enum.auto()
    '''
    Acknowledge successful reception of a message with a context ID in case it
    gets a result response later.
    '''

    TEXT = enum.auto()
    '''The payload is text.'''

    ENCODED = enum.auto()
    '''The payload is already encoded somehow?'''

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

    def __init__(self,
                 id:      Union[MonotonicId, int],
                 type:    'MsgType',
                 message: Optional[Any] = None) -> None:
        self._id:      int           = int(id)
        self._type:    'MsgType'     = type
        self._message: Optional[Any] = message

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
    def message(self) -> Optional[Any]:
        '''
        Return our message value.
        '''
        return self._message

    @property
    def path(self) -> Optional[str]:
        '''
        Returns a path str or None, based on MsgType.

        # TODO [2020-07-29]: Also based on other things? Payload...
        '''
        if self._type == MsgType.PING:
            return 'ping'
        elif self._type == MsgType.ECHO:
            return 'echo'
        elif self._type == MsgType.TEXT:
            return 'text'
        elif (self._type == MsgType.ENCODED
              or self._type == MsgType.CODEC):
            return 'encoded'

        return None

    # ------------------------------
    # Codec Support
    # ------------------------------

    def encode(self) -> Mapping[str, str]:
        '''
        Returns a representation of ourself as a dictionary.
        '''
        msg = self._message
        if isinstance(msg, Encodable):
            msg = self._message.encode()

        encoded = {
            'id': self._id,
            'type': self._type.encode(),
            'message': msg,
        }
        return encoded

    @classmethod
    def decode(klass: 'Message', value: Mapping[str, str]) -> 'Message':
        '''
        Returns a representation of ourself as a dictionary.
        '''
        decoded = klass(
            value['id'],
            MsgType.decode(value['type']),
            value['message'],
        )
        return decoded

    # ------------------------------
    # To String
    # ------------------------------

    def __str__(self):
        return (
            f"{self.__class__.__name__}"
            f"[{self.id}, "
            f"{self.type}]("
            f"{str(self.message)}): "
        )

    def __repr__(self):
        return (
            "<Msg["
            f"{repr(self.id)},"
            f"{repr(self.type)}]"
            f"({repr(self.message)})>"
        )
