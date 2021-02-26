# coding: utf-8

'''
Context for Mediators.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, Type, NewType, Mapping, List

from veredi.logs                   import log
from veredi.base.context           import EphemerealContext
from veredi.base.identity          import MonotonicId
from veredi.game.ecs.base.identity import EntityId

from .const                        import MsgType


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

UserConnToken = NewType('UserConnToken', int)
'''
Don't need anything fancy - just want type hinting basically.
'''

USER_CONN_INVALID = UserConnToken(0)
'''
Invalid connection token for initializing or resetting variables or whatever.
'''


# -----------------------------------------------------------------------------
# Mediator Contexts
# -----------------------------------------------------------------------------

class MediatorContext(EphemerealContext):
    '''
    Context for mediators. For indicating what kind of mediations, serdes, etc
    is in use.
    '''

    def __init__(self,
                 dotted: str,
                 path:   Optional[str]               = None,
                 type:   Optional[str]               = None,
                 serdes:  Optional[Mapping[str, str]] = None,
                 conn:   Optional[UserConnToken]     = None
                 ) -> None:
        super().__init__(dotted, 'mediator')
        self.sub['path'] = path
        self.sub['type'] = type
        self.sub['serdes'] = serdes
        self.sub['connection'] = conn

    @property
    def path(self) -> Optional[MonotonicId]:
        return self.sub.get('path', None)

    @property
    def connection(self) -> Optional[UserConnToken]:
        return self.sub.get('connection', None)

    @connection.setter
    def connection(self, value: Optional[UserConnToken]) -> None:
        self.sub['connection'] = value

    def __repr_name__(self):
        return 'MedCtx'


class MediatorServerContext(MediatorContext):
    '''
    Context for mediators on the server side. For indicating what kind of
    mediations, serdes, etc is in use.
    '''

    def __repr_name__(self):
        return 'MedSvrCtx'


class MediatorClientContext(MediatorContext):
    '''
    Context for mediators on the client side. For indicating what kind of
    mediations, serdes, etc is in use.
    '''

    def __repr_name__(self):
        return 'MedCliCtx'


# -----------------------------------------------------------------------------
# Message Contexts
# -----------------------------------------------------------------------------

class MessageContext(EphemerealContext):
    '''
    Context for mediation<->game interactions. I.e. Messages.
    '''

    # ------------------------------
    # Create
    # ------------------------------

    def __init__(self,
                 dotted: str,
                 id:     Optional[MonotonicId] = None,
                 path:   Optional[str] = None) -> None:
        super().__init__(dotted, 'message')
        self.sub['id'] = id
        self.sub['path'] = path

    @classmethod
    def from_mediator(klass: Type['MessageContext'],
                      ctx:   'MediatorContext',
                      id:     Optional[MonotonicId] = None
                      ) -> 'MessageContext':
        '''
        Initializes and returns a MessageContext from a MediatorContext.
        '''
        return MessageContext(ctx.dotted(),
                              id=id,
                              path=ctx.path)

    # ------------------------------
    # Properties: Mediator
    # ------------------------------

    @property
    def id(self) -> Optional[MonotonicId]:
        '''
        Message's ID.
        '''
        return self.sub.get('id', None)

    @property
    def path(self) -> Optional[MonotonicId]:
        '''
        Path message was received on.
        '''
        return self.sub.get('path', None)

    # ------------------------------
    # Properties: Game
    # ------------------------------

    @property
    def entity_ids(self) -> Optional[List[EntityId]]:
        '''
        List of EntityIds that the UserId/Key matches.
        '''
        return self.sub_get('entity_ids')

    @entity_ids.setter
    def entity_ids(self, value: Optional[List[EntityId]]) -> None:
        '''
        List of EntityIds that the UserId/Key matches.
        '''
        return self.sub_set('entity_ids', value)

    # ------------------------------
    # Getter/Setters: Message Types
    # ------------------------------

    def _msgtype_to_str(self, type: MsgType) -> str:
        '''
        Converts the MsgType `type` into its field key string.

        Raises a ValueError if an unsupported `type` is supplied.
        '''
        field = None
        if MsgType.TEXT:
            field = 'text'

        elif MsgType.ENCODED:
            field = 'encoded'

        # Other MsgTypes are invalid for the Game so we error on them.
        else:
            supported = {MsgType.TEXT, MsgType.ENCODED}
            msg = (f"Invalid MsgType. Can only support: {supported}. "
                   f"Got: {type}.")
            raise log.exception(ValueError(msg, type),
                                msg,
                                context=self)

        return field

    def get_msg_payload(self, type: MsgType) -> Optional[Any]:
        '''
        Gets the message sub-context of our sub-context, then looks for an
        entry in it based on MsgType `type`.
        '''
        field = self._msgtype_to_str(type)
        msg_ctx = self.sub_get('message')
        if not msg_ctx:
            return None
        return msg_ctx.get(field, None)

    def set_msg_payload(self, type: MsgType, value: Any) -> None:
        '''
        Sets the `value` into the proper place in the message sub-context of
        our sub-context.
        '''
        field = self._msgtype_to_str(type)
        msg_ctx = self.sub_get('message') or {}
        msg_ctx[field] = value
        return self.sub_set('message', msg_ctx)

    @property
    def msg_text(self) -> Optional[str]:
        '''
        If a text-based message, this will return the string.
        '''
        return self.get_msg_payload(MsgType.TEXT)

    @msg_text.setter
    def msg_text(self, value: Optional[str]) -> None:
        '''
        Set the text string of the text-based message.
        '''
        return self.set_msg_payload(MsgType.TEXT, value)

    @property
    def msg_encoded(self) -> Optional[str]:
        '''
        If a encoded-based message, this will return the string.
        '''
        return self.get_msg_payload(MsgType.ENCODED)

    @msg_encoded.setter
    def msg_encoded(self, value: Optional[str]) -> None:
        '''
        Set the value of the encoded-based message.
        '''
        return self.set_msg_payload(MsgType.ENCODED, value)

    # ------------------------------
    # Pythonic Functions
    # ------------------------------

    def __repr_name__(self):
        return 'MessCtx'
