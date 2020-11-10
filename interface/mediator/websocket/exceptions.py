# coding: utf-8

'''
Exceptions for WebSockets, VebSockets, and WebSocket Mediators.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from ..exceptions import MediatorError


# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------

class WebSocketError(MediatorError):
    '''
    Some sort of WebSocket Mediation error.
    '''
    ...


class ConnectionError(MediatorError):
    '''
    Mediator had problem connecting to other Mediator.
    '''
    ...
