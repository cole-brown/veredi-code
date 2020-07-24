# coding: utf-8

'''
Interface for Different Mediation Implementations (e.g. WebSockets)
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from abc import abstractmethod

from .mediator import Mediator


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Game-to-Client Interface
# -----------------------------------------------------------------------------

class MediatorServer(Mediator):
    '''
    Server Interface/Base (Abstract) Class for Different Mediation
    Implementations. e.g. WebSockets
    '''

    @abstractmethod
    def start(self) -> None:
        '''
        The server should start accepting connections, calls from the clients,
        etc. It should be fully armed and operational after this call.
        '''
        ...
