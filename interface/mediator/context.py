# coding: utf-8

'''
Context for Mediators.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Type, NewType, Mapping

from veredi.base.context  import EphemerealContext
from veredi.base.identity import MonotonicId


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

UserConnToken = NewType('UserConnToken', int)
'''
Don't need anything fancy - just want type hinting basically.
'''


# -----------------------------------------------------------------------------
# Mediator Contexts
# -----------------------------------------------------------------------------

class MediatorContext(EphemerealContext):
    '''
    Context for mediators. For indicating what kind of mediations, codec, etc
    is in use.
    '''

    def __init__(self,
                 dotted: str,
                 path:   Optional[str]               = None,
                 type:   Optional[str]               = None,
                 codec:  Optional[Mapping[str, str]] = None,
                 conn:   Optional[UserConnToken]     = None
                 ) -> None:
        super().__init__(dotted, 'mediator')
        self.sub['path'] = path
        self.sub['type'] = type
        self.sub['codec'] = codec
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
    mediations, codec, etc is in use.
    '''

    def __repr_name__(self):
        return 'MedSvrCtx'


class MediatorClientContext(MediatorContext):
    '''
    Context for mediators on the client side. For indicating what kind of
    mediations, codec, etc is in use.
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
        return MessageContext(ctx.dotted,
                              id=id,
                              path=ctx.path)

    # ------------------------------
    # Properties
    # ------------------------------

    @property
    def id(self) -> Optional[MonotonicId]:
        return self.sub.get('id', None)

    @property
    def path(self) -> Optional[MonotonicId]:
        return self.sub.get('path', None)

    def __repr_name__(self):
        return 'MessCtx'