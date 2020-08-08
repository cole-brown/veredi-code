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

from typing import (TYPE_CHECKING,
                    Optional, Any, Awaitable, Iterable)
if TYPE_CHECKING:
    import re

from veredi.base.null import Null

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
from .message                  import Message, MsgType


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

        self._med_rx_queue = asyncio.Queue()
        '''
        Queue for received data from server intended for us, the mediator.
        '''

        self._rx_queue = asyncio.Queue()
        '''Queue for received data from server to be passed to the game.'''

        self._rx_qid = MonotonicId.generator()
        '''ID for _rx_queue items.'''

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

    def update_logging(self, msg: Message) -> None:
        '''
        Adjusts our logging.
        '''
        if (not msg
                or msg.type != MsgType.LOGGING
                or not isinstance(msg.message, dict)):
            return

        data = msg.message.get('logging', Null())

        # Should we update our logging level?
        update_level = data.get('level', Null())
        if update_level:
            update_level = log.Level(update_level)
            log.set_level(update_level)
            log.info(f"Updated {self.__class__.__name__}'s logging to: "
                     f"{update_level}")

        # We'll have others eventually. Like 'start up log_client and connect
        # to this WebSocket or Whatever to send logs there now please'.

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

    def _game_has_data(self) -> bool:
        '''Returns True if queue from game has data to send to server.'''
        return self._game.poll()

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

    async def _med_queue_watcher(self) -> None:
        '''
        Loop waiting on messages in our `_med_rx_queue` to change something
        about our logging.
        '''
        while True:
            # Die if requested.
            if self._shutdown:
                break

            # Check for something in connection to send; don't block.
            if self._med_rx_queue.empty():
                await asyncio.sleep(0.1)
                continue

            # Else get one thing and send it off this round.
            try:
                msg = self._med_rx_queue.get_nowait()
                if not msg:
                    continue
            except asyncio.QueueEmpty:
                # get_nowait() got nothing. That's fine; go back to waiting.
                continue

            # Deal with this msg to us?
            if msg.type == MsgType.LOGGING:
                self.update_logging(msg)

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

