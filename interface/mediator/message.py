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


import enum
import re


import veredi.logger.log
from veredi.security               import abac
from veredi.base.enum              import FlagEncodeValueMixin
from veredi.data.codec.encodable   import (Encodable,
                                           EncodableRegistry,
                                           EncodedComplex,
                                           EncodedSimple)
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

class Message(Encodable, dotted='veredi.interface.mediator.message.message'):
    '''
    Message object between game and mediator.

    Saves id as an int. Casts back to ID type in property return.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # ------------------------------
    # Constants: Encodable
    # ------------------------------

    _ENCODE_NAME: str = 'message'
    '''Name for this class when encoding/decoding.'''

    @enum.unique
    class SpecialId(FlagEncodeValueMixin, enum.IntEnum):
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

        @classmethod
        def dotted(klass: 'MsgType') -> str:
            '''
            Unique dotted name for this class.
            '''
            return 'veredi.interface.mediator.message.specialid'

        @classmethod
        def _type_field(klass: 'MsgType') -> str:
            '''
            A short, unique name for encoding an instance into a field in
            a dict.
            '''
            return 'spid'

        # Rest of Encodabe funcs come from FlagEncodeValueMixin.

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
    def payload_decoded(self) -> Union['Encodable', Any, None]:
        '''
        Tries to decode the message payload. Returns decoded value if it could
        decode, or just returns payload itself if it could not decode.
        '''
        # TODO: foo: Do we need this? I think not?

        # self._payload = value
        pass

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

    @property
    def path(self) -> Optional[str]:
        '''
        Returns a path str or None, based on MsgType.

        # TODO [2020-10-27]: delete this.
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

    @classmethod
    def _type_field(klass: 'Message') -> str:
        return klass._ENCODE_NAME

    def _encode_simple(self) -> EncodedSimple:
        '''
        Don't support simple for Messages.
        '''
        msg = (f"{self.__class__.__name__} doesn't support encoding to a "
               "simple string.")
        raise NotImplementedError(msg)

    @classmethod
    def _decode_simple(klass: 'Message',
                       data: EncodedSimple) -> 'Message':
        '''
        Don't support simple by default.
        '''
        msg = (f"{klass.__name__} doesn't support decoding from a "
               "simple string.")
        raise NotImplementedError(msg)

    def _encode_complex(self) -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''

        # Tell our payload to encode... or use as-is if not an Encodable.
        encoded_payload = self.payload
        if isinstance(self.payload, Encodable):
            encoded_payload = self.payload.encode_with_registry()

        # Put our data into a dict for encoding.
        encoded = {
            'msg_id':    Encodable.encode_or_none(self._msg_id),
            'type':      MsgType.encode_or_none(self._type),
            'entity_id': EntityId.encode_or_none(self._entity_id),
            'user_id':   UserId.encode_or_none(self._user_id),
            'user_key':  UserKey.encode_or_none(self._user_key),
            'payload':   encoded_payload,
            'security':  abac.Subject.encode_or_none(self._security_subject),
        }

        # print(f"message.encode_complex: {encoded}")
        return encoded

    @classmethod
    def _decode_complex(klass: 'Message',
                        data: EncodedComplex) -> 'Message':
        '''
        Decode ourself from an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        klass.error_for(data,
                        keys=[
                            'msg_id', 'type',
                            'entity_id', 'user_id', 'user_key',
                            'security',
                            'payload',
                        ])

        # msg_id could be a few different types.
        msg_id = EncodableRegistry.decode(data['msg_id'])
        # print(f"Message.decode_complex: msg_id: {type(msg_id)} {msg_id}")

        # These are always their one type.
        _type = MsgType.decode(data['type'])
        # print(f"Message.decode_complex: type: {type(_type)} {_type}")
        entity_id = EntityId.decode(data['entity_id'])
        user_id = UserId.decode(data['user_id'])
        # print(f"Message.decode_complex: user_id: {type(user_id)} {user_id}")
        user_key = UserKey.decode(data['user_key'])
        security = abac.Subject.decode(data['security'])
        # print(f"Message.decode_complex: security: {type(security)} {security}")

        # Payload can be encoded or just itself. So try to decode, then
        # fallback to use its value as is.
        payload = Encodable.decode_with_registry(
            data['payload'],
            fallback=data['payload'])

        return klass(msg_id, _type,
                     payload=payload,
                     entity_id=entity_id,
                     user_id=user_id,
                     user_key=user_key,
                     subject=security)

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

class ConnectionMessage(Message,
                        dotted='veredi.interface.mediator.message.connection'):
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


# Hit a brick wall trying to get an Encodable enum's dotted through to
# Encodable. :| Register manually with the Encodable registry.
Message.SpecialId.register_manually()
