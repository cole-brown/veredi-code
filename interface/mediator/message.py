# coding: utf-8

'''
Veredi Mediator Message.

For a server mediator (e.g. WebSockets) talking to a game.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type, NewType, Tuple)
if TYPE_CHECKING:
    from veredi.interface.mediator.context import UserConnToken


import enum


from veredi.logs                   import log
from veredi.security               import abac
from veredi.data.codec             import (Codec,
                                           Encodable,
                                           EncodedComplex,
                                           EncodedSimple)
from veredi.data.exceptions        import EncodableError
from veredi.base.identity          import MonotonicId
from veredi.data.identity          import UserId, UserKey
from veredi.game.ecs.base.identity import EntityId


from ..user                        import UserPassport
from .const                        import MsgType
from .payload.base                 import BasePayload
from .payload.bare                 import BarePayload
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

class Message(Encodable,
              name_dotted='veredi.interface.mediator.message.message',
              name_string='message'):
    '''
    Message object between game and mediator.

    Saves id as an int. Casts back to ID type in property return.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

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

        OR Server -> Game: This client has connected.
        '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        self._msg_id: MsgIdTypes = None
        '''
        ID for message itself. Can be initialized as None, but messages must be
        sent with a non-None message id.
        '''

        self._type: 'MsgType' = MsgType.IGNORE
        '''
        Message's Type. Determines how Mediators handle the message itself and
        its payload.
        '''

        self._entity_id: Optional[EntityId] = None
        '''
        The specific entity related to the message, if there is one.

        E.g. if a skill roll happens, it will be assigned the EntityId of the
        entity used to roll the skill.

        Or if some sort of not-tied-to-an-entity message, it will be None.
        '''

        self._user_id: Optional[UserId] = None
        '''
        The UserId this message will be sent to. Can be None if not set yet, or
        if broadcast maybe?
        # TODO: isthis None, or something else, for broadcast?
        '''

        self._user_key: Optional[UserId] = None
        '''
        The UserKey this message will be sent to. Should only be set if
        _user_id is also set. Can be None if not set yet, or if broadcast
        maybe?
        # TODO: is this None, or something else, for broadcast?
        '''

        self._payload: Optional[Any] = None
        '''
        The actual important part of the message: what'sin it.
        '''

        self._security_subject: Optional[abac.Subject] = None
        '''
        The actual important part of the message: what's in it.
        '''

    def __init__(self,
                 msg_id:    Union[MonotonicId, SpecialId, int, None],
                 type:      'MsgType',
                 payload:   Optional[Any]          = None,
                 entity_id: Optional[EntityId]     = None,
                 user_id:   Optional[UserId]       = None,
                 user_key:  Optional[UserKey]      = None,
                 subject:   Optional[abac.Subject] = None) -> None:
        self._define_vars()

        self._msg_id           = msg_id
        self._type             = type
        self._entity_id        = entity_id
        self._user_id          = user_id
        self._user_key         = user_key
        self._payload          = payload
        self._security_subject = subject

    # -------------------------------------------------------------------------
    # General MsgType Init Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def echo(klass: Type['Message'],
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
    # ACK_CONNECT: Connected (response to client) Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def connected(klass:   Type['Message'],
                  msg:     'Message',
                  id:      UserId,
                  key:     UserKey,
                  success: bool) -> 'Message':
        '''
        Creates a MsgType.ACK_CONNECT message reply for success/failure of
        connection.
        '''
        if success:
            return klass(msg.msg_id, MsgType.ACK_CONNECT,
                         payload=BarePayload({'text': 'Connected.',
                                              'code': True}),
                         user_id=id,
                         user_key=key)

        return klass(msg.msg_id, MsgType.ACK_CONNECT,
                     payload=BarePayload({'text': 'Failed to connect.',
                                          'code': False}),
                     user_id=id,
                     user_key=key)

    def verify_connected(self) -> Tuple[bool, Optional[str]]:
        '''
        Verifies this is an ACK_CONNECTED message and that it was a successful
        connection.

        Returns Tuple[bool, Optional[str]]:
          - bool: success/failure
          - str:
            - if success: None
            - if failure: Failure reason
        '''
        if self.type != MsgType.ACK_CONNECT:
            return (False,
                    f"Message is not MsgType.ACK_CONNECT. Is {self.type}")

        # Correct type of message, now check the payload.
        if not isinstance(self.payload, BarePayload):
            return (False,
                    "Message's payload is unexpected type. Expecting "
                    f"BarePayload, got: {type(self.payload)}")

        # Correct payload - check for success.
        try:
            # Do we have the 'code' field we need to determine success?
            if not self.payload.data or 'code' not in self.payload.data:
                return (False,
                        "Cannot understand BarePayload's data: "
                        f"{self.payload.data}")

            # Was it a failure?
            elif self.payload.data['code'] is not True:
                return (False,
                        "Connection failed with code "
                        f"'{self.payload.data['code']}' and reason: "
                        f"{self.payload.data['text']}")

            # The One Good Return. 'code' was True/success, so return success.
            else:
                return (True, None)

        # Unexpected things happened. Probably 'code' doesn't exist or data
        # isn't a dict.
        except (TypeError, KeyError):
            return (False,
                    "Connection success unknown - received exception when "
                    "trying to check. Payload has unexpected data format "
                    f"probably: {self.payload}")

        # Not expecting to get here unless BarePayload or Message.connected()
        # has changed and this hasn't...
        return (False,
                "You're not supposed to be able to get this far here. "
                f"What's wrong? {self.payload}")

    # -------------------------------------------------------------------------
    # Payload Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def payload_basic(klass:   Type['Message'],
                      payload: str) -> BarePayload:
        '''
        Creates and returns a bare payload for the message string.
        '''
        return BarePayload(payload)

    # -------------------------------------------------------------------------
    # Logging MsgType Init Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def log(klass:       Type['Message'],
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
        Replace payload with its (encoded/decoded/serialized/deserialized)
        equal.

        TODO: Should payload be straight up replaced? Keep original somewhere?
        '''
        self._payload = value

    @property
    def security_subject(self) -> Optional[abac.Subject]:
        '''
        Return our security.abac.Subject value.
        '''
        # TODO [2020-10-27]: What should 'None' do? Fail message
        # eventually, probably. Shouldn't send without security involved.
        # Security should be set to 'debug' or something if undesired for
        # whatever reason.
        return self._security_subject

    # -------------------------------------------------------------------------
    # Encodable API
    # -------------------------------------------------------------------------

    def encode_simple(self, codec: 'Codec') -> EncodedSimple:
        '''
        Don't support simple for Messages.
        '''
        msg = (f"{self.klass} doesn't support encoding to a "
               "simple string.")
        raise NotImplementedError(msg)

    @classmethod
    def decode_simple(klass: Type['Message'],
                      data:  EncodedSimple,
                      codec: 'Codec') -> 'Message':
        '''
        Don't support simple by default.
        '''
        msg = (f"{klass.__name__} doesn't support decoding from a "
               "simple string.")
        raise NotImplementedError(msg)

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        # Tell our payload to encode... or use as-is if not an Encodable.
        encoded_payload = self.payload
        if isinstance(self.payload, Encodable):
            encoded_payload = codec.encode(self.payload)

        # Put our data into a dict for encoding.
        encoded = {
            'msg_id':    codec.encode(self._msg_id),
            'type':      codec.encode(self._type),
            'entity_id': codec.encode(self._entity_id),
            'user_id':   codec.encode(self._user_id),
            'user_key':  codec.encode(self._user_key),
            'payload':   encoded_payload,
            'security':  codec.encode(self._security_subject),
        }

        return encoded

    @classmethod
    def decode_complex(klass: Type['Message'],
                       data:  EncodedComplex,
                       codec: 'Codec',
                       instance: Optional['Message'] = None) -> 'Message':
        '''
        Decode ourself from an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        try:
            klass.error_for(data,
                            keys=[
                                'msg_id', 'type',
                                'entity_id', 'user_id', 'user_key',
                                'security',
                                'payload',
                            ])

            # msg_id could be a few different types.
            msg_id = codec.decode(None, data['msg_id'])

            # These are always their one type.
            _type = codec.decode(MsgType, data['type'])
            entity_id = codec.decode(EntityId, data['entity_id'])
            user_id = codec.decode(UserId, data['user_id'])
            user_key = codec.decode(UserKey, data['user_key'])
            security = codec.decode(abac.Subject, data['security'])

            # Payload can be encoded or just itself. So try to decode, then
            # fallback to use its value as is.
            payload = codec.decode(None,
                                   data['payload'],
                                   fallback=data['payload'])

            return klass(msg_id, _type,
                         payload=payload,
                         entity_id=entity_id,
                         user_id=user_id,
                         user_key=user_key,
                         subject=security)
        except Exception as error:
            log.exception(error,
                          "Caught exception decoding Message.")
            raise

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self):
        return (
            f"{self.klass}"
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

class ConnectionMessage(
        Message,
        name_dotted='veredi.interface.mediator.message.connection',
        name_string='message.connection'):
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
    def connected(klass:      Type['ConnectionMessage'],
                  user_id:    UserId,
                  user_key:   Optional[UserKey],
                  connection: 'UserConnToken'
                  ) -> 'ConnectionMessage':
        '''
        Create a "connected" version of a ConnectionMessage.
        '''
        return ConnectionMessage(True, user_id, user_key, connection)

    @classmethod
    def disconnected(klass:      Type['ConnectionMessage'],
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

    def user(self) -> UserPassport:
        '''
        Create a UserPassport instance with our Connection information.
        '''
        return UserPassport(self.user_id, self.user_key, self.connection)
