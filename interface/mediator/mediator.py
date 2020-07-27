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

from veredi.logger                import log
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

    SHUTDOWN_TIMEOUT_SEC = 5.0

    def __init__(self,
                 config:        Configuration,
                 conn:          multiprocessing.connection.Connection,
                 shutdown_flag: multiprocessing.Event) -> None:
        self._conn: multiprocessing.connection.Connection = conn
        '''Our IPC connection to the game process.'''

        # self._aio: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        # '''The asyncio event loop.'''

        self._shutdown_process: multiprocessing.Event = shutdown_flag
        '''Event to check to see if we have been asked to shutdown.'''

        self._shutdown_asyncs:  asyncio.Event         = asyncio.Event()
        '''
        Async event that gets set once `self._shutdown_process` is set and
        noticed.
        '''

    # -------------------------------------------------------------------------
    # Abstracts
    # -------------------------------------------------------------------------

    @abstractmethod
    def start(self) -> None:
        '''
        Start our socket listening.
        '''
        ...

    # @abstractmethod
    # def stop(self) -> None:
    #     '''
    #     Stop our async coroutines so we can shut down.
    #     '''
    #     ...

    # -------------------------------------------------------------------------
    # Asyncio / Multiprocessing Functions
    # -------------------------------------------------------------------------

    # def _main(self):
    #     '''
    #     Primary function for our mediator process.
    #     '''
    #     # Polling option, if we have significant work to do in our process:
    #     # while not self._shutdown_process.is_set():
    #     #
    #     # Timeout option, if we're letting async stuff take care of everything?
    #     while not self._shutdown_process.wait(self.SHUTDOWN_TIMEOUT_SEC):
    #         # Do 'main' stuff here if needed.
    #         continue

    #     # And shut ourselves down?
    #     self.stop()
    #     log.debug("Goodbye.")

    async def _shutdown_watcher(self) -> None:
        '''
        Watches `self._shutdown_process`. Will call stop() on our asyncio loop
        when the shutdown flag is set.
        '''
        # # Wait forever on our shutdown flag...
        # self._shutdown_process.wait(None)
        # # ...and stop the asyncio loop when it gets set.
        # self._aio.stop()
        # # That will stop our listener and let us finish out of self._main().

        while True:
            if self._shutdown:
                break
            # Await something so other async tasks can run? IDK.
            await asyncio.sleep(0.1)

        # Shutdown has been signaled to us somehow; make sure we signal to
        # other processes/awaitables.
        self._shutdown = True

    @property
    def _shutdown(self) -> bool:
        '''
        Returns true if we should shutdown this process.
        '''
        return (
            self._shutdown_process.is_set()
            or self._shutdown_asyncs.is_set()
        )

    @_shutdown.setter
    def _shutdown(self, value: bool) -> None:
        '''
        Sets all shutdown flags. Cannot unset.
        '''
        # Can't unset, so error:
        if not value:
            flags = (self._shutdown_process.is_set(),
                     self._shutdown_asyncs.is_set())
            msg = "Can't unset shutdown flags. process: {}, asyncs: {}"
            msg = msg.format(*flags)
            raise log.exception(ValueError(msg, *flags),
                                None,
                                msg)

        # Can set; set both.
        self._shutdown_process.set()
        self._shutdown_asyncs.set()

    # async def _watch_for_shutdown(self):
    #     '''
    #     async function to look for the shutdown flag and stop the async event
    #     loop.
    #     '''
    #     retval = self._shutdown_process.wait(self.SHUTDOWN_TIMEOUT_SEC)
    #     if retval:
    #         self._aio.stop()
    #
    #     return retval
