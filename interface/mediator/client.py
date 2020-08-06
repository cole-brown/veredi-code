# coding: utf-8

'''
Interface for Different Mediation Implementations (e.g. WebSockets)
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

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

    ...

    # # -----------------------------------------------------------------------
    # # From Base Class:
    # # -----------------------------------------------------------------------
    # # (Probably. But see it for an up-to-date list.

    # @abstractmethod
    # def init_background(self):

    # @abstractmethod
    # @property
    # def _background(self):

    # @abstractmethod
    # def make_med_context(self) -> MediatorContext:

    # @abstractmethod
    # def make_msg_context(self, id: MonotonicId) -> MessageContext:

    # @abstractmethod
    # def start(self) -> None:
