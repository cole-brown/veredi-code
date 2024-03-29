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
                    Optional, Union, Any, Awaitable, Iterable, Tuple, Literal)
if TYPE_CHECKING:
    import re

from veredi.base.null import Null

from abc import ABC, abstractmethod
import multiprocessing
import multiprocessing.connection
import asyncio
# import signal

from veredi.logs                import log
from veredi.logs.mixin          import LogMixin
from veredi.debug.const         import DebugFlag
from veredi.data                import background
from veredi.data.config.context import ConfigContext
from veredi.base.identity       import MonotonicId
from veredi.base.context        import VerediContext
from veredi.base.strings        import label
from veredi.base.strings.mixin  import NamesMixin
from veredi.parallel.multiproc  import SubToProcComm

# from .                        import exceptions
from .context                   import MediatorContext, MessageContext
from .const                     import MsgType
from .message                   import Message
from .payload.logging           import LogPayload, LogField


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_UT_ENABLE  = "unit-testing enable"
_UT_DISABLE = "unit-testing disable"


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Mediator(ABC, LogMixin, NamesMixin):
    '''
    Veredi Server I/O Mediator.

    Mediator sub-classes are expected to use kwargs:
      - Required:
        + name_dotted: Optional[label.LabelInput]
          - string/strings to create the Veredi dotted label.
        + name_string: Optional[str]
          - Any short string for describing class. Either short-hand or class's
            __name__ are fine.
      - Optional:
        + name_klass:        Optional[str]
          - If None, will be class's __name__.
        + name_string_xform: Optional[Callable[[str], str]] = None,
        + name_klass_xform:  Optional[Callable[[str], str]] = to_lower_lambda,

    Example:
      class JeffMediator(Mediator,
                         name_dotted=label.normalize('mediator', 'jeff'),
                         name_string='jeff')

    For a server (e.g. REST) talking to a game.

    For input, the mediator takes in JSON and converts it into an InputEvent
    for the InputSystem.

    For output, the mediator receives an OutputEvent from the OutputSystem and
    converts it into JSON for sending.
    '''

    SHUTDOWN_TIMEOUT_SEC = 5.0

    def _define_vars(self) -> None:
        '''
        Set up our vars with type hinting, docstrs.
        '''

        self._comms: SubToProcComm = None
        '''
        This sub-process to parent process connections, flags, debug info.
        '''

        self._debug: DebugFlag = None
        '''Extra debugging output granularity.'''

        # TODO [2020-09-11]: Remove all self._testing stuff - unused.
        self._testing: bool = False
        '''
        Whatever abnormal shenanigans are needed for unit testing are hidden
        behind this flag. For example, server shouldn't push
        MsgType.LOGGING reply messages into its _med_to_game_queue, but
        will if unit testing so that the unit test can inspect the client's
        response.
        '''

        # self._test_pipe: multiprocessing.connection.Connection = None
        # '''
        # A little backchannel for unit-testing IPC to tell us to do weird
        # stuff like toggle self._testing flag.
        # '''

        # self._game_pipe: multiprocessing.connection.Connection = None
        # '''Our IPC connection to the game process.'''

        # self._shutdown_process: multiprocessing.Event = None
        # '''Event to check to see if we have been asked to shutdown.'''

        self._shutdown_asyncs:  asyncio.Event = asyncio.Event()
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
        Queue for sending data from this mediator to a mediator on the other
        end (Client->Server or vice versa).
        '''

        self._med_to_game_queue = asyncio.Queue()
        '''
        Queue for received data from this mediator to be passed to the game.
        '''

    def __init__(self, context: VerediContext) -> None:
        # ------------------------------
        # Make our vars first.
        # ------------------------------
        self._define_vars()
        self._log_config(self.dotted)

        # ------------------------------
        # Get/check for required stuff.
        # ------------------------------

        # Must have context and subproc.
        if context:
            self._comms = ConfigContext.subproc(context)
        else:
            raise background.config.exception(
                context,
                "Cannot configure {} without a supplied context.",
                self.klass)

        if not self._comms:
            raise background.config.exception(
                context,
                "Cannot configure {} without SubToProcComm object in context.",
                self.klass)

        # # Get (required) config.
        # config = background.config.config(self.klass,
        #                                   self.dotted,
        #                                   context)

        # ------------------------------
        # Grab some things from comms.
        # ------------------------------

        # Leave all the 'communications' stuff in self._comms.
        # E.g. connections/pipes, multiproc event flags (shutdown flag), etc.

        # Pull debug up to class.
        self._debug = self._comms.debug_flags

    # -------------------------------------------------------------------------
    # Debug
    # -------------------------------------------------------------------------

    # TODO [2020-08-18]: Make a "debuggable" or "loggable" class/interface,
    # move this debug() there.
    # Also make the other debug level functions.
    # Also also make a 'print'.
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
            self._log_data_processing(self.dotted,
                                      msg,
                                      *args,
                                      **kwargs,
                                      log_minimum=log.Level.DEBUG)

    def logging_request(self, msg: Message) -> None:
        '''
        Deal with a logging request. Adjust our logging level, add/remote log
        handlers, ignore the whole thing... whatever you want.
        '''
        if (not msg
                or msg.type != MsgType.LOGGING
                or not isinstance(msg.payload, LogPayload)):
            self.debug("logging_request: wrong type or payload: {}",
                       msg)
            return

        # Should we update our logging level?
        payload_recv = msg.payload
        request = payload_recv.request
        if not request:
            self._log_data_processing(
                "logging_request: "
                "Received LoggingPayload with nothing in request? "
                "Cannot do anything with: {}",
                msg)
            return None

        report_action = False
        if LogField.LEVEL in request:
            report_action = True
            self._logging_req_level(request[LogField.LEVEL])

        # We'll have others eventually. Like 'start up log_client and connect
        # to this WebSocket or Whatever to send logs there now please'.

        # Default to not sending reply...
        send = None

        # If report requested or if we did something as requested, report back!
        # LogField.REPORT is bool, so check that it exists and also is
        # True.
        report_requested = (LogField.REPORT in request
                            and request[LogField.REPORT])
        if report_requested or report_action:
            # Reuse received; send 'em back their data?
            payload_send = payload_recv
            payload_send = self._logging_req_report(payload_send)

            send = Message.log(msg.msg_id,
                               msg.user_id, msg.user_key,
                               payload_send)

        return send

    def _logging_req_level(self,
                           level: Optional[log.Level]) -> None:
        '''
        Update our logging to level or ignore.
        '''
        if level is None:
            return

        self.debug("_logging_req_level: Updating logging level from "
                   "{} to {}.",
                   log.get_level(), level)
        log.set_level(level)

    def _logging_req_report(self,
                            response: LogPayload) -> LogPayload:
        '''
        Set logging report fields in `response` LogPayload.
        Returns `response`.
        '''
        response.create_report(level=log.get_level()
                               # TODO: get remotes into report at some point.
                               # remotes=...
                               )
        return response

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
        Make a context with our context data, our serdes', etc.
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
        return self._comms.has_data()

    def _game_pipe_get(self) -> Tuple[Message, MessageContext]:
        '''
        Gets data from game pipe for sending. Waits/blocks until it receives
        something.
        '''
        msg, ctx = self._comms.recv()
        self.debug("_game_pipe_get: "
                   "Got from game pipe for sending: msg: {}, ctx: {}",
                   msg, ctx)
        return msg, ctx

    def _game_pipe_put(self, msg: Message, ctx: MessageContext) -> None:
        '''Puts data into game pipe for game to receive.'''
        self.debug("_game_pipe_get: "
                   "Received into game pipe for game to process: "
                   "msg: {}, ctx: {}",
                   msg, ctx)
        self._comms.send(msg, ctx)

    def _game_pipe_clear(self) -> None:
        '''
        Removes all current data for us in our side of the game pipe
        connection.
        '''
        self.debug("_game_pipe_clear: Clearing game pipe...")

        # Read and ignore messages while it has some.
        while self._game_has_data():
            self._game_pipe_get()

    # ------------------------------
    # Mediator-RX -> Mediator-to-Game Queue
    # ------------------------------

    def _med_to_game_has_data(self) -> bool:
        '''Returns True if _med_to_game_queue has data to deal with.'''
        return not self._med_to_game_queue.empty()

    def _med_to_game_get(self) -> Tuple[Message, MessageContext]:
        '''Gets (no wait) data from _med_to_game_queue pipe for processing.'''
        msg, ctx = self._med_to_game_queue.get_nowait()
        self.debug("_med_to_game_get: "
                   "Got from _med_to_game_queue to give to game: "
                   "msg: {}, ctx: {}",
                   msg, ctx)
        return msg, ctx

    async def _med_to_game_put(self,
                               msg: Message,
                               ctx: MessageContext) -> None:
        '''
        Puts data into _med_to_game_put for us to... just receive again?...
        '''
        self.debug("_med_to_game_put: "
                   "Putting into _med_to_game_put pipe to give to game: "
                   "msg: {}, ctx: {}",
                   msg, ctx)
        await self._med_to_game_queue.put((msg, ctx))

    def _med_to_game_clear(self) -> None:
        '''
        Removes all current data for us from self._med_to_game_queue.
        '''
        self.debug("_med_to_game_clear: Clearing med_to_game pipe...")

        # Read and ignore messages while it has some.
        while self._med_to_game_has_data():
            self._med_to_game_get()

    # ------------------------------
    # Mediator -> Mediator Send Queue
    # ------------------------------

    def _med_tx_has_data(self) -> bool:
        '''Returns True if _med_tx_queue has data to send to server.'''
        return not self._med_tx_queue.empty()

    def _med_tx_get(self) -> Tuple[Message, MessageContext]:
        '''Gets (no wait) data from _med_tx_queue pipe for sending.'''
        msg, ctx = self._med_tx_queue.get_nowait()
        self.debug("_med_tx_get: "
                   "Got from med_tx pipe for sending: msg: {}, ctx: {}",
                   msg, ctx)
        return msg, ctx

    async def _med_tx_put(self, msg: Message, ctx: MessageContext) -> None:
        '''Puts data into _med_tx_queue for us to send to other mediator.'''
        self.debug("_med_tx_put: "
                   "Putting into med_tx pipe for med_tx to process: "
                   "msg: {}, ctx: {}",
                   msg, ctx)
        await self._med_tx_queue.put((msg, ctx))

    def _med_tx_clear(self) -> None:
        '''
        Removes all current data for us from self._med_tx_queue.
        '''
        self.debug("_med_tx_clear: Clearing med_tx_queue pipe...")

        # Read and ignore messages while it has some.
        while self._med_tx_has_data():
            self._med_tx_get()

    # ------------------------------
    # Mediator -> Mediator Receive Queue
    # ------------------------------

    def _med_rx_has_data(self) -> bool:
        '''Returns True if _med_rx_queue has data to deal with.'''
        return not self._med_rx_queue.empty()

    def _med_rx_get(self) -> Tuple[Message, MessageContext]:
        '''Gets (no wait) data from _med_rx_queue pipe for processing.'''
        msg, ctx = self._med_rx_queue.get_nowait()
        self.debug("_med_rx_get: Got from med_rx pipe for receiving: "
                   "msg: {}, ctx: {}",
                   msg, ctx)
        return msg, ctx

    async def _med_rx_put(self, msg: Message, ctx: MessageContext) -> None:
        '''Puts data into _med_rx_queue for us to... just receive again?...'''
        self.debug("_med_rx_put: Put into med_rx pipe for med_rx to process: "
                   "msg: {}, ctx: {}",
                   msg, ctx)
        await self._med_rx_queue.put((msg, ctx))

    def _med_rx_clear(self) -> None:
        '''
        Removes all current data for us from self._med_rx_queue.
        '''
        self.debug("_med_rx_clear: Clearing med_rx_queue pipe...")

        # Read and ignore messages while it has some.
        while self._med_rx_has_data():
            self._med_rx_get()

    # ------------------------------
    # Unit Test Case -> Mediator
    # ------------------------------

    def _test_pipe_exists(self) -> bool:
        '''
        Returns True if self._comms.ut_pipe is truthy.
        '''
        return self._comms._ut_exists()

    def _test_has_data(self) -> bool:
        '''
        No wait/block.
        Returns True if queue from unit test has data for us.
        '''
        if not self._test_pipe_exists():
            return False
        return self._comms._ut_has_data()

    def _test_pipe_get(self) -> Tuple[Optional[Message],
                                      Optional[MessageContext]]:
        '''
        Returns (None, None) immediately if no unit test pipe. Otherwise gets
        data from unit test pipe for sending. Waits/blocks until it receives
        something.
        '''
        if not self._test_pipe_exists():
            return None, None
        recv, ctx = self._comms._ut_recv()
        self.debug("_test_pipe_get: Got from unit test pipe for sending: "
                   "msg: {}, ctx: {}",
                   recv, ctx)
        return recv, ctx

    def _test_pipe_put(self, msg: Message, ctx: MessageContext) -> None:
        '''
        Ignored if unit test pipe doesn't exist. Otherwise puts data into unit
        test pipe for unit test to receive.
        '''
        if not self._test_pipe_exists():
            return
        self.debug("_test_pipe_put: "
                   "Putting into test pipe for unit test to process: "
                   "msg: {}, ctx: {}",
                   msg, ctx)
        self._comms._ut_send(msg, ctx)

    def _test_pipe_clear(self) -> None:
        '''
        Removes all current data for us from self._comms.ut_pipe.
        '''
        if not self._test_pipe_exists():
            # No test pipe - nothing to.
            return

        self.debug("_test_pipe_clear: Clearing unit-test pipe...")

        # Read and ignore messages while it has some.
        while self._test_has_data():
            self._test_pipe_get()

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
            continue

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
                self.debug("_med_queue_watcher: received: {}", msg)
                await self._continuing()
                continue

            # Deal with this msg to us?
            if msg.type == MsgType.LOGGING:
                self.debug("_med_queue_watcher: _med_rx_get got: {}", msg)
                reply = self.logging_request(msg)
                if reply:
                    await self._med_tx_put(msg, ctx)
                    # Done; continue and reloop.

            await self._continuing()
            continue

    async def _test_watcher(self) -> None:
        '''
        Looks for a unit testing message to take from unit testing pipe and
        handle. It is always for this mediator.
        '''
        while True:
            # Die if requested.
            if self.any_shutdown():
                break

            # Check for something in connection; don't block.
            if not self._test_has_data():
                await self._continuing()
                continue

            # Get that something, do something with it.
            try:
                msg, ctx = self._test_pipe_get()
                self._log_data_processing(self.dotted,
                                          "_test_watcher: "
                                          "{} got from test pipe:\n"
                                          "  data: {}\n"
                                          "   ctx: {}",
                                          self.name, msg, ctx)

            except EOFError as error:
                log.exception(error,
                              "_test_watcher: "
                              "Failed getting from test pipe; "
                              "ignoring and continuing.")
                # EOFError gets raised if nothing left to receive or other end
                # closed. Wait til we know what that means to our test/mediator
                # pair before deciding to take (drastic?) action here...

            if msg == _UT_ENABLE:
                self._testing = True
                self.debug("_test_watcher: Enabled unit testing flag.")

            elif msg == _UT_DISABLE:
                self._testing = True
                self.debug("_test_watcher: Disabled unit testing flag.")

            else:
                error_msg = ("_test_watcher: "
                             "{self.name} doesn't know what to do "
                             "with received testing message: {}")
                raise log.exception(
                    ValueError(error_msg.format(self.name, msg)),
                    error_msg,
                    self.name,
                    msg)

            # Done processing; sleep a bit then continue.
            await self._continuing()

    # ------------------------------
    # Shutdown Flags
    # ------------------------------

    def any_shutdown(self) -> bool:
        '''
        Returns true if we should shutdown this process.
        '''
        return (
            self._comms.shutdown.is_set()
            or self._shutdown_asyncs.is_set()
        )

    def set_all_shutdown(self) -> None:
        '''
        Sets all shutdown flags. Cannot unset.
        '''
        self._comms.shutdown.set()
        self._shutdown_asyncs.set()
