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

from typing import Any, Awaitable, Iterable

from abc import ABC, abstractmethod
import multiprocessing
import multiprocessing.connection
import asyncio
# import signal

from veredi.logger             import log
from veredi.debug.const        import DebugFlag
from veredi.data.config.config import Configuration
from veredi.base.identity      import MonotonicId

# from .                         import exceptions
from .context                  import MediatorContext, MessageContext


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
                 shutdown_flag: multiprocessing.Event,
                 debug:         DebugFlag = None) -> None:
        self._debug: DebugFlag = debug
        '''Extra debugging output granularity.'''

        self._game: multiprocessing.connection.Connection = conn
        '''Our IPC connection to the game process.'''

        self._shutdown_process: multiprocessing.Event = shutdown_flag
        '''Event to check to see if we have been asked to shutdown.'''

        self._shutdown_asyncs:  asyncio.Event         = asyncio.Event()
        '''
        Async event that gets set once `self._shutdown_process` is set and
        noticed.
        '''

    # -------------------------------------------------------------------------
    # Debug
    # -------------------------------------------------------------------------

    def debug(self,
              msg: str,
              *args: Any,
              **kwargs: Any) -> None:
        '''
        Debug logs if our DebugFlag has the proper bits set for Mediator
        debugging.
        '''
        if self._debug and self._debug.has(DebugFlag.MEDIATOR_BASE):
            kwargs = log.incr_stack_level(kwargs)
            log.debug(msg,
                      *args,
                      **kwargs)

    # -------------------------------------------------------------------------
    # Abstracts
    # -------------------------------------------------------------------------

    @abstractmethod
    def _init_background(self):
        '''
        Insert the mediator context data into the background.
        '''
        ...

    @property
    @abstractmethod
    def _background(self):
        '''
        Get background data for init_background()/background.mediator.set().
        '''
        ...

    @abstractmethod
    def make_med_context(self) -> MediatorContext:
        '''
        Make a context with our context data, our codec's, etc.
        '''
        ...

    @abstractmethod
    def make_msg_context(self, id: MonotonicId) -> MessageContext:
        '''
        Make a context for a message.
        '''
        ...

    @abstractmethod
    def start(self) -> None:
        '''
        Start our socket listening.
        '''
        ...

    # -------------------------------------------------------------------------
    # Asyncio / Multiprocessing Functions
    # -------------------------------------------------------------------------

    async def _a_main(self, *aws: Awaitable) -> Iterable[Any]:
        '''
        Runs `aws` list of async tasks/futures concurrently, returns the
        aggregate list of return values for those tasks/futures.
        '''
        ret_vals = await asyncio.gather(*aws)
        return ret_vals

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
