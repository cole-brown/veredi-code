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
# Client-to-Game Interface
# -----------------------------------------------------------------------------

class MediatorClient(Mediator):
    '''
    Client Interface/Base (Abstract) Class for Different Mediation
    Implementations. e.g. WebSockets
    '''

    @abstractmethod
    def start(self) -> None:
        '''
        The client should start up whatever's needed to be able to send to and
        receive from the game server.
        '''
        ...
