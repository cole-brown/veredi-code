# coding: utf-8

'''
Veredi Server I/O Mediator.

For a server (e.g. WebSockets) talking to a game.

For input, the mediator takes in JSON and converts it into an InputEvent for
the InputSystem.

For output, the mediator receives an OutputEvent from the OutputSystem and
converts it into JSON for sending.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from abc import ABC, abstractmethod
import multiprocessing
import multiprocessing.connection
import asyncio

from veredi.data.config.config    import Configuration


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Mediator(ABC):
    '''
    Veredi Server I/O Mediator.

    For a server (e.g. REST) talking to a game.

    For input, the mediator takes in JSON and converts it into an InputEvent
    for the InputSystem.

    For output, the mediator receives an OutputEvent from the OutputSystem and
    converts it into JSON for sending.
    '''

    def __init__(self,
                 config:        Configuration,
                 conn:          multiprocessing.connection.Connection,
                 shutdown_flag: multiprocessing.Event = None) -> None:
        self._conn: multiprocessing.connection.Connection = conn
        '''Our IPC connection to the game process.'''

        self._aio: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        '''The asyncio event loop.'''

        self._do_shutdown: multiprocessing.Event = shutdown_flag
        '''Event to check to see if we have been asked to shutdown.'''

    @abstractmethod
    def start(self) -> None:
        '''
        Start our socket listening.
        '''
        ...
