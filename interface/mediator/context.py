# coding: utf-8

'''
Context for Mediators.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional

from veredi.base.context  import EphemerealContext
from veredi.base.identity import MonotonicId


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Mediator Contexts
# -----------------------------------------------------------------------------

class MediatorContext(EphemerealContext):
    '''
    Context for mediators. For indicating what kind of mediations, codec, etc
    is in use.
    '''

    def __init__(self, dotted: str) -> None:
        super().__init__(dotted, 'mediator')

    def __repr_name__(self):
        return 'MedCtx'


class MediatorServerContext(MediatorContext):
    '''
    Context for mediators on the server side. For indicating what kind of
    mediations, codec, etc is in use.
    '''

    def __init__(self, dotted: str) -> None:
        super().__init__(dotted)


class MediatorClientContext(MediatorContext):
    '''
    Context for mediators on the client side. For indicating what kind of
    mediations, codec, etc is in use.
    '''

    def __init__(self, dotted: str) -> None:
        super().__init__(dotted)


# -----------------------------------------------------------------------------
# Message Contexts
# -----------------------------------------------------------------------------

class MessageContext(EphemerealContext):
    '''
    Context for mediation<->game interactions. I.e. Messages.
    '''

    def __init__(self, dotted: str, id: MonotonicId) -> None:
        super().__init__(dotted, 'message')
        self.sub['id'] = id

    @property
    def id(self) -> Optional[MonotonicId]:
        return self.sub.get('id', None)

    def __repr_name__(self):
        return 'MessCtx'
