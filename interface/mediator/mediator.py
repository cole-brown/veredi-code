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
                    Optional, Any, Awaitable, Iterable, Tuple)
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

        self._game_pipe: multiprocessing.connection.Connection = conn
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

        self._med_tx_queue = asyncio.Queue()
        '''
        Queue for injecting some send data from this mediator to the other end
        of mediation.
        '''

        self._med_to_game_queue = asyncio.Queue()
        '''Queue for received data from server to be passed to the game.'''

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

        # Should we update our logging level?
        update_level = msg.logging()
        if update_level:
            log.info(f"Updating {self.__class__.__name__}'s logging to "
                     f"{update_level} by request: {msg}")
            update_level = log.Level(update_level)
            log.set_level(update_level)
            log.info(f"Updated {self.__class__.__name__}'s logging to "
                     f"{update_level} by request: {msg}")

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
    # Check / Send / Recv for Pipes & Queues.
    # -------------------------------------------------------------------------

    # ------------------------------
    # Game -> Mediator Pipe
    # ------------------------------

    def _game_has_data(self) -> bool:
        '''
        No wait/block.
        Returns True if queue from game has data to send to server.
        '''
        return self._game_pipe.poll()

    def _game_pipe_get(self) -> Tuple[Message, MessageContext]:
        '''
        Gets data from game pipe for sending. Waits/blocks until it receives
        something.
        '''
        msg, ctx = self._game_pipe.recv()
        self.debug(f"Got from game pipe for sending: msg: {msg}, ctx: {ctx}")
        return msg, ctx

    def _game_pipe_put(self, msg: Message, ctx: MessageContext) -> None:
        '''Puts data into game pipe for game to receive.'''
        self.debug("Received into game pipe for game to process: "
                   f"msg: {msg}, ctx: {ctx}")
        self._game_pipe.send((msg, ctx))
        return msg, ctx

    # ------------------------------
    # Mediator-RX -> Mediator-to-Game Queue
    # ------------------------------

    def _med_to_game_has_data(self) -> bool:
        '''Returns True if _med_to_game_queue has data to deal with.'''
        return not self._med_to_game_queue.empty()

    def _med_to_game_get(self) -> Tuple[Message, MessageContext]:
        '''Gets (no wait) data from _med_to_game_queue pipe for processing.'''
        msg, ctx = self._med_to_game_queue.get_nowait()
        self.debug("Got from _med_to_game_queue for receiving: "
                   f"msg: {msg}, ctx: {ctx}")
        return msg, ctx

    async def _med_to_game_put(self,
                               msg: Message,
                               ctx: MessageContext) -> None:
        '''
        Puts data into _med_to_game_put for us to... just receive again?...
        '''
        self.debug("Received into _med_to_game_put pipe to give to game: "
                   f"msg: {msg}, ctx: {ctx}")
        await self._med_to_game_queue.put((msg, ctx))

    # ------------------------------
    # Mediator -> Mediator Send Queue
    # ------------------------------

    def _med_tx_has_data(self) -> bool:
        '''Returns True if _med_tx_queue has data to send to server.'''
        return not self._med_tx_queue.empty()

    def _med_tx_get(self) -> Tuple[Message, MessageContext]:
        '''Gets (no wait) data from _med_tx_queue pipe for sending.'''
        msg, ctx = self._med_tx_queue.get_nowait()
        self.debug(f"Got from med_tx pipe for sending: msg: {msg}, ctx: {ctx}")
        return msg, ctx

    async def _med_tx_put(self, msg: Message, ctx: MessageContext) -> None:
        '''Puts data into _med_tx_queue for us to send to other mediator.'''
        self.debug("Received into med_tx pipe for med_tx to process: "
                   f"msg: {msg}, ctx: {ctx}")
        await self._med_tx_queue.put((msg, ctx))

    # ------------------------------
    # Mediator -> Mediator Receive Queue
    # ------------------------------

    def _med_rx_has_data(self) -> bool:
        '''Returns True if _med_rx_queue has data to deal with.'''
        return not self._med_rx_queue.empty()

    def _med_rx_get(self) -> Tuple[Message, MessageContext]:
        '''Gets (no wait) data from _med_rx_queue pipe for processing.'''
        msg, ctx = self._med_rx_queue.get_nowait()
        self.debug("Got from med_rx pipe for receiving: "
                   f"msg: {msg}, ctx: {ctx}")
        return msg, ctx

    async def _med_rx_put(self, msg: Message, ctx: MessageContext) -> None:
        '''Puts data into _med_rx_queue for us to... just receive again?...'''
        self.debug("Received into med_rx pipe for med_rx to process: "
                   f"msg: {msg}, ctx: {ctx}")
        await self._med_rx_queue.put((msg, ctx))

    # -------------------------------------------------------------------------
    # Asyncio / Multiprocessing Functions
    # -------------------------------------------------------------------------

    async def _continuing(self) -> None:
        '''
        Call when about to continue in an asyncio loop.
        '''
        await asyncio.sleep(0.1)

    async def _sleep(self) -> None:
        '''
        Call when about to continue in an asyncio loop.
        '''
        await asyncio.sleep(0.1)

    async def _a_main(self, *aws: Awaitable) -> Iterable[Any]:
        '''
        Runs `aws` list of async tasks/futures concurrently, returns the
        aggregate list of return values for those tasks/futures.
        '''
        ret_vals = await asyncio.gather(*aws)
        return ret_vals

    async def _shutdown_watcher(self) -> None:
        '''
        Watches shutdown flags. Will call stop() on our asyncio loop
        when a shutdown flag is set.
        '''
        while True:
            if self.any_shutdown():
                break
            # Await something so other async tasks can run? IDK.
            await self._continuing()

        # Shutdown has been signaled to us somehow; make sure we signal to
        # other processes/awaitables.
        self.set_all_shutdown()

    async def _med_queue_watcher(self) -> None:
        '''
        Loop waiting on messages in our `_med_rx_queue` to change something
        about our logging.
        '''
        while True:
            # Die if requested.
            if self.any_shutdown():
                break

            # Check for something in connection to send; don't block.
            if not self._med_rx_has_data():
                await self._continuing()
                continue

            # Else get one thing and process it.
            msg, ctx = self._med_rx_get()
            if not msg:
                await self._continuing()
                continue

            # Deal with this msg to us?
            if msg.type == MsgType.LOGGING:
                self.update_logging(msg)

            await self._continuing()

    def any_shutdown(self) -> bool:
        '''
        Returns true if we should shutdown this process.
        '''
        return (
            self._shutdown_process.is_set()
            or self._shutdown_asyncs.is_set()
        )

    def set_all_shutdown(self) -> None:
        '''
        Sets all shutdown flags. Cannot unset.
        '''
        self._shutdown_process.set()
        self._shutdown_asyncs.set()
