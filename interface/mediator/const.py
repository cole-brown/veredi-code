# coding: utf-8

'''
Constants for Mediator, Messages, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Mapping


import enum
import re


from veredi.logger               import log
from veredi.base.enum            import (FlagCheckMixin,
                                         FlagSetMixin,
                                         FlagEncodeValueMixin)


_MT_ENCODE_FIELD_NAME: str = 'v.mt'
'''Can override in sub-classes if needed. E.g. 'eid' for entity id.'''


# -----------------------------------------------------------------------------
# Messages
# -----------------------------------------------------------------------------

@enum.unique
class MsgType(FlagCheckMixin, FlagSetMixin, FlagEncodeValueMixin, enum.Flag):
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

    ENVELOPE = enum.auto()
    '''
    This is an Envelope object. Use its addresses and encode its data as you
    see fit.
    '''

    GAME_AUTO = enum.auto()
    '''
    The mediator should figure this one out and it should be one of the
    GAME_MSGS types.
    '''

    # ------------------------------
    # Encodable API (Codec Support)
    # ------------------------------

    @classmethod
    def dotted(klass: 'MsgType') -> str:
        '''
        Unique dotted name for this class.
        '''
        return 'veredi.interface.mediator.msgtype'

    @classmethod
    def _type_field(klass: 'MsgType') -> str:
        '''
        A short, unique name for encoding an instance into a field in a dict.
        '''
        return 'v.mt'

    # Rest of Encodable is provided by FlagEncodeValueMixin.


# Hit a brick wall trying to get an Encodable enum's dotted through to
# Encodable. :| Register manually?
#
# Register ourself manually with the Encodable registry.
MsgType.register_manually()
