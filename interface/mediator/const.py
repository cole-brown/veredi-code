# coding: utf-8

'''
Constants for Mediator, Messages, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Mapping

import enum


from veredi.base.enum            import (FlagCheckMixin,
                                         FlagSetMixin)
from veredi.data.codec.encodable import Encodable


# -----------------------------------------------------------------------------
# Messages
# -----------------------------------------------------------------------------

@enum.unique
class MsgType(FlagCheckMixin, FlagSetMixin, Encodable, enum.Flag):
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

    DISCONNECT = enum.auto()
    '''
    Client connection is closing/has closed. Should include user id, whatever
    else is needed to unregister user.
    '''

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

    GAME_AUTO = enum.auto()
    '''
    The mediator should figure this one out and it should be one of the
    GAME_MSGS types.
    '''

    GAME_MSGS = TEXT | ENCODED | CODEC
    '''
    Expected message types from the game.
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
