# coding: utf-8

'''
Veredi Game (Test) Client.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Type Hinting Imports
# ---
from typing import Optional, Any, Callable


# ---
# Python Imports
# ---
import websockets
import asyncio
import multiprocessing
import multiprocessing.connection
import re
from contextlib import contextmanager


# ---
# Veredi Imports
# ---
from veredi.logs                 import log
from veredi.debug.const          import DebugFlag
from veredi.base.identity        import MonotonicId
from veredi.base.context         import VerediContext
from veredi.base.strings         import label
from veredi.data.identity        import UserId
from veredi.data                 import background
from veredi.data.config.config   import Configuration
from veredi.data.serdes.base     import BaseSerdes
from veredi.data.codec           import Codec

from ..const                     import MsgType
from ..message                   import Message
from .mediator                   import WebSocketMediator
from .base                       import VebSocket, TxProcessor, RxProcessor
from ..context                   import (MediatorClientContext,
                                         MessageContext,
                                         UserConnToken)
from .exceptions                 import WebSocketError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# The '/Actual/' "Talk to the Client" Bit
# -----------------------------------------------------------------------------

class VebSocketClient(VebSocket):
    '''
    Veredi Web Socket asyncio shenanigan class, client edition.
    '''

    SHORT_NAME = 'client'
    ''' Should be 'client' or 'server', depending. '''

    def __init__(self,
                 serdes:         BaseSerdes,
                 codec:          Codec,
                 med_context_fn: Callable[[], MediatorClientContext],
                 msg_context_fn: Callable[[], MessageContext],
                 host:           str,
                 path:           Optional[str]           = None,
                 port:           Optional[int]           = None,
                 secure:         Optional[bool]          = True,
                 debug_fn:       Optional[Callable]      = None) -> None:
        super().__init__(serdes, codec,
                         med_context_fn, msg_context_fn,
                         host,
                         path=path,
                         port=port,
                         secure=secure,
                         debug_fn=debug_fn)
        self.debug(f"created client socket: {self.uri}")

    # -------------------------------------------------------------------------
    # Keep Connection Alive. Send/Receive in Parallel.
    # -------------------------------------------------------------------------

    async def connect_parallel(
            self,
            produce_fn: TxProcessor,
            consume_fn: RxProcessor
    ) -> None:
        '''
        Connect to the server. Spin up asyncio tasks for messages
        received (`consume_fn`) and for messages to send (`produce_fn`).
        Watches those until something completes/exits, and then cleans
        itself up.

        Also watches the ``_close`` asyncio.Event flag to see if it should kill
        itself early (instruct it via :meth:`close`).
        '''
        self.debug(f"connect_parallel: Client connecting to {self.uri}...")

        self._data_produce = produce_fn
        self._data_consume = consume_fn

        async with websockets.connect(self.uri) as websocket:
            self.debug(f"connect_parallel: Client connected to {self.uri}. "
                       f"connection: {websocket}")
            # websocket: WebSocketClientProtocol
            self._socket = websocket

            # Make both consume and produce handlers. Run them in parallel. The
            # first one that finishes signifies an end to our connection over
            # this websocket.
            consume = asyncio.ensure_future(self._ppc_consume(
                websocket,
                self._msg_make_context(self.path_rooted)))
            consume.add_done_callback(self._ppc_done_handle)
            produce = asyncio.ensure_future(self._ppc_produce(
                websocket,
                self._msg_make_context(self.path_rooted)))
            produce.add_done_callback(self._ppc_done_handle)
            # And this one is just to exit when asked to close().
            poison = asyncio.ensure_future(self._a_wait_close())
            poison.add_done_callback(self._ppc_done_handle)
            self.debug("connect_parallel: Client running produce/consume...")
            done, pending = await asyncio.wait(
                [produce, consume, poison],
                return_when=asyncio.FIRST_COMPLETED)

            self.debug("connect_parallel: "
                       f"Client done with connection to {self.uri}. "
                       "Cancelling still pending tasks "
                       "produce/consume tasks...")
            # Whoever didn't finish first gets the axe.
            for task in pending:
                task.cancel()

        self._socket = None
        self.debug("connect_parallel: Client connection done.")


# -----------------------------------------------------------------------------
# Client (Veredi)
# -----------------------------------------------------------------------------

class WebSocketClient(WebSocketMediator,
                      name_dotted='veredi.interface.mediator.websocket.client',
                      name_string='client'):
    '''
    Mediator for... client-ing over WebSockets.
    '''

    _MAX_CONNECT_ATTEMPT_FAILS: int = 10
    '''
    Maximum number of errors/failures to connect to server before just
    giving up.
    '''

    def _define_vars(self) -> None:
        '''
        Set up our vars with type hinting, docstrs.
        '''
        super()._define_vars()

        # ---
        # Client's Auth Info
        # ---
        self._id: Optional[UserId] = None
        '''Our auth id for talking to server.'''

        self._key: Optional[UserId] = None
        '''Our auth key for talking to server.'''

        # ---
        # Client WebSocket stuff...
        # ---
        self._connect_request: asyncio.Event = asyncio.Event()
        '''
        Flag to indicate our server connection asyncio task should connect to
        server and start running the producer/consumer pipelines.
        '''

        self._connected: bool = False
        '''
        Have we managed to connect to server yet?

        Note: Not really "are we connected right now". Just "has the server
        confirmed our CONNECT with an ACK_CONNECT at some point in the past?"
        '''

        self._connect_attempts: int = 0
        '''
        If connect itself has error, we don't want to just infinitely spam. So
        count connection attempts and give up eventually.
        '''

    def __init__(self,
                 context: VerediContext) -> None:
        # Base class init first.
        super().__init__(context)

        # NOTE: For increased logging on only client from the get-go:
        # log.set_group_level(log.Group.DATA_PROCESSING, log.Level.INFO)
        # log.set_group_level(log.Group.PARALLEL, log.Level.DEBUG)
        # log.critical("Client set data_proc to {}.",
        #              log.get_group_level(log.Group.DATA_PROCESSING))
        # log.data_processing(self.dotted,
        #                     "Client set data_proc to {}.",
        #                     log.get_group_level(log.Group.DATA_PROCESSING))

        # TODO [2020-09-12]: Remove this and get or generate auth id/key some
        # other way.
        subctx = context.sub
        if 'id' in subctx:
            self._id = subctx['id']
            self._key = subctx['key']

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def connected(self):
        '''
        Have we managed to connect to server yet?

        Note: Not really "are we connected right now". Just "has the server
        confirmed our CONNECT with an ACK_CONNECT at some point in the past?"
        '''
        return self._connected

    # -------------------------------------------------------------------------
    # Debug
    # -------------------------------------------------------------------------

    def debug(self,
              msg:      str,
              *args:    Any,
              **kwargs: Any) -> None:
        '''
        Debug logs if our DebugFlag has the proper bits set for Mediator
        debugging.
        '''
        if (self._debug
                and self._debug.any(DebugFlag.MEDIATOR_BASE,
                                    DebugFlag.MEDIATOR_CLIENT)):
            msg = f"{self._name}: " + msg
            kwargs = log.incr_stack_level(kwargs)
            self._log_data_processing(self.dotted,
                                      msg,
                                      *args,
                                      **kwargs,
                                      log_minimum=log.Level.DEBUG)

    # -------------------------------------------------------------------------
    # Mediator API
    # -------------------------------------------------------------------------

    def make_med_context(self,
                         connection: websockets.WebSocketCommonProtocol = None
                         ) -> MediatorClientContext:
        '''
        Make a context with our context data, our serdes, etc.
        '''
        ctx = MediatorClientContext(self.dotted)
        ctx.sub['type'] = 'websocket.client'
        serdes_ctx, _ = self._serdes.background
        codec_ctx, _ = self._codec.background
        ctx.sub['serdes'] = serdes_ctx
        ctx.sub['codec'] = codec_ctx
        return ctx

    def make_msg_context(self, id: MonotonicId) -> MessageContext:
        '''
        Make a context for a message.
        '''
        ctx = MessageContext(self.dotted, id)
        return ctx

    def start(self) -> None:
        '''
        Start our socket listening.
        '''
        self.debug("start: Starting clientt...")

        # Kick it off into asyncio's hands.
        try:
            asyncio.run(self._a_main(self._shutdown_watcher(),
                                     self._queue_watcher(),
                                     self._med_queue_watcher(),
                                     self._server_watcher(),
                                     self._test_watcher()))

        except websockets.exceptions.ConnectionClosedOK:
            pass

        except Exception as error:
            # TODO [2020-07-28]: Should we shut it all down, or keep going?
            self.shutdown = True
            import traceback
            trace = traceback.format_exc()
            log.exception(
                error,
                "Caught exception running MediatorClient coroutines:\n{}",
                trace)

        self.debug("start: Done.")

    # -------------------------------------------------------------------------
    # Asyncio / Multiprocessing Functions
    # -------------------------------------------------------------------------

    async def _shutdown_watcher(self) -> None:
        '''
        Watches `self._shutdown_process`. Will call stop() on our asyncio loop
        when the shutdown flag is set.
        '''
        # Parent's watcher is non-blocking so we can be simple about this:
        self.debug("_shutdown_watcher: Wait on parent._shutdown_watcher()...")
        await super()._shutdown_watcher()

        # If we have a server conn, ask it to close too.
        if self._socket:
            self.debug("_shutdown_watcher: "
                       "Tell our WebSocket to stop.")
            self._socket.close()
        else:
            self.debug("_shutdown_watcher: "
                       "We have no WebSocket to stop?")

        self.debug("_shutdown_watcher: "
                   "Done.")

    async def _queue_watcher(self) -> None:
        '''
        Loop waiting on messages in our _rx_queue to send down to the game.
        '''
        while True:
            # Die if requested.
            if self.any_shutdown():
                break

            # Check for something in connection to send; don't block.
            if not self._med_to_game_has_data():
                await self._continuing()
                continue

            # Else get one thing and send it off this round.
            try:
                msg, ctx = self._med_to_game_get()
                self.debug("_queue_watcher (_med_to_game_queue->game_pipe): "
                           "_med_to_game_queue has message to process: "
                           "msg: {}, ctx: {}",
                           msg, ctx)
                if not msg or not ctx:
                    self.debug("_to_game_watcher (_med_to_game_queue->game_pipe): "
                               "Got nothing for message to process? "
                               "Need both message and context! "
                               "msg: {}, ctx: {}",
                               msg, ctx)
                    await self._continuing()
                    continue
            except asyncio.QueueEmpty:
                # get_nowait() got nothing. That's fine; go back to waiting.
                await self._continuing()
                continue

            # Transfer from 'received from server queue' to
            # 'sent to game connection'.
            self.debug("_to_game_watcher (_med_to_game_queue->game_pipe): "
                       "Send to game pipe: {}, {}",
                       msg, ctx)
            self._game_pipe_put(msg, ctx)

            self.debug("_to_game_watcher (_med_to_game_queue->game_pipe): "
                       "Done processing message: {}, {}",
                       msg, ctx)

            # Skip this - we used get_nowait(), not get().
            # self._rx_queue.task_done()
            await self._continuing()
            continue

    @contextmanager
    def _connect_manager(self) -> 'WebSocketClient':
        '''
        Manages attempts at connecting to the server.
        Manages: self._connect_request flag, self._connect_attempts
        '''
        # ------------------------------
        # Checks and Prep for Attempt.
        # ------------------------------
        self.debug("_connect_manager: Starting connection to server...")

        # We're trying to connect now, so we don't need our connect request
        # flag set anymore.
        self._clear_connect()

        # Error check: time to give up?
        if self._connect_attempts > self._MAX_CONNECT_ATTEMPT_FAILS:
            # Raise error to get out of context manager.
            msg = (f"{self.__class__.__name__}: Failed to connect to "
                   f"the server! Failed {str(self._connect_attempts + 1)} "
                   "attempts.")
            error = ConnectionError(msg, None)
            raise log.exception(error, msg)

        # Increment our attempts counter, as we are now attempting.
        self._connect_attempts += 1

        # ------------------------------
        # Do an attempt.
        # ------------------------------
        try:
            self.debug("_connect_manager: "
                       "Yielding for Client->Server Connection Attempt {}/{} ",
                       self._connect_attempts,
                       self._MAX_CONNECT_ATTEMPT_FAILS)

            # "Do the code now."
            yield self

        # Always reraise all exceptions - we're in a `with` context.
        except Exception as error:
            log.exception(error,
                          "Client->Server Connection Attempt {}/{} "
                          "failed with error: {}",
                          self._connect_attempts,
                          self._MAX_CONNECT_ATTEMPT_FAILS,
                          error)
            raise

        # ------------------------------
        # Done with management. Clean up.
        # ------------------------------
        # Don't clear attempts counter yet... We're done asking to connect.
        # Server needs to reply for us to actually connect successfully.
        # return self._connection_attempt_success()
        self.debug("_connect_manager: "
                   "Done managing Client->Server Connection Attempts. "
                   "final: {}/{}",
                   self._connect_attempts,
                   self._MAX_CONNECT_ATTEMPT_FAILS)

    def _connection_attempt_success(self) -> None:
        '''
        Connection was successful. Clean up connection attempts data.
        '''
        self.debug("_connection_attempt_success: "
                   "Connection attempt successful!"
                   "final: {}/{}",
                   self._connect_attempts,
                   self._MAX_CONNECT_ATTEMPT_FAILS)

        # ------------------------------
        # Set as connected.
        # ------------------------------
        self.debug("_connection_attempt_success: Setting as connected...")
        self._connected = True
        self._connect_attempts = 0

        # ------------------------------
        # Done.
        # ------------------------------
        self.debug("_connection_attempt_success: "
                   "Connection Successful: "
                   "Done setting/resetting connection vars.")

    def _connection_attempt_failure(self) -> None:
        '''
        Couldn't connect. Give up.
        '''
        self.debug("_connection_attempt_failure: "
                   "Connection attempt _-FAILED-_!"
                   "final: {}/{}",
                   self._connect_attempts,
                   self._MAX_CONNECT_ATTEMPT_FAILS)

        # TODO [2020-08-13]: Give up if a 'give up' fail message/code comes
        # from... somewhere?

        # ------------------------------
        # Set as not connected.
        # ------------------------------
        self.debug("_connection_attempt_failure: Setting as NOT connected...")
        self._connected = False
        # Leave attempt counter as is... Force something to be done about
        # previous failure before allowinng another try.
        # self._connect_attempts = 0

        # Close socket if it exists.
        if self._socket:
            self.debug("_connection_attempt_failure: Closing socket...")
            self._socket.close()
            self._socket = None
        else:
            self.debug("_connection_attempt_failure: No socket to close.")

        # ------------------------------
        # Drop data queued.
        # ------------------------------
        self.debug("_connection_attempt_failure: "
                   "Connection Failed: Dropping messages in pipes/queues.")
        self._game_pipe_clear()
        self._med_to_game_clear()
        self._med_tx_clear()
        self._med_rx_clear()
        self._test_pipe_clear()

        # ------------------------------
        # Done.
        # ------------------------------
        self.debug("_connection_attempt_failure: "
                   "Connection Failed: Done.")

    async def _server_watcher(self) -> None:
        '''
        AsyncIO awaitable. Will sleep until client wants to connect to server,
        then will await our :meth:`_server_connection` connection's
        :meth:`connect_parallel` for sending/receiving messages.

        Opens connection to the server, then can send and receive in parallel
        in the :meth:`_handle_produce` and :meth:`_handle_consume` functions.
        '''
        # Wait for someone to want to talk to server...
        while True:
            # Check exit condition.
            if self.any_shutdown():
                if self._socket:
                    self._socket.close()
                    self._socket = None
                return

            # If game has data to send and we're not running, try
            # maybe running?
            if self._game_has_data():
                self._request_connect()

            # Check... enter condition.
            if not self._desire_connect():
                if self._game_has_data():
                    self.debug("_server_watcher: "
                               "Client has data to send but doesn't desire "
                               "a connection to server?!")
                await self._continuing()
                continue
            self.debug("_server_watcher: "
                       "Client has data to send to server. Connecting...")

            # ------------------------------
            # Connection Manager for tracking failures.
            # ------------------------------
            with self._connect_manager():
                self.debug("_server_watcher: Obtained connection manager.")
                # All the 'connecting' code should be under the `with` so it's
                # all managed and success/failure noticed.

                if self._socket:
                    raise log.exception(WebSocketError,
                                        "WebSocket to server exists but we "
                                        "were expecting it not to. {}",
                                        self._socket)

                # TODO: path for my user? With user id, user key?
                self.debug("_server_watcher: "
                           "Creating connection to server...")
                self._socket = self._server_connection()
                self.debug("_server_watcher: "
                           "Created connection to server: {}",
                           self._socket)

                # TODO: get connect message working
                self.debug("_server_watcher: "
                           "Creating connect message...")
                connect_msg, connect_ctx = self._connect_message()
                self.debug("_server_watcher: "
                           "Queueing connect message... {}, {}",
                           connect_msg, connect_ctx)
                await self._med_tx_put(connect_msg, connect_ctx)

                self.debug("_server_watcher: "
                           "Starting connection handlers...")
                await self._socket.connect_parallel(self._handle_produce,
                                                    self._handle_consume)
                self.debug("_server_watcher: "
                           "Done with connection to server.")

            self.debug("_server_watcher: "
                       "Done with connection manager and connection.")

            # And back to waiting on the connection request flag.
            self._socket = None
            await self._continuing()
            continue

    def _connect_message(self, ctx: Optional[MessageContext] = None) -> None:
        '''
        Queue up a connection message to server for auth/user registration.
        '''
        self.debug("_connect_message: "
                   "Creating connection message {}: {}",
                   ("from provided context" if ctx else "and a context"),
                   ctx)

        ctx = ctx or self.make_msg_context(Message.SpecialId.enum.CONNECT)
        self.debug("_connect_message: "
                   "Creating connection message with context: {}",
                   ctx)
        msg = Message(Message.SpecialId.enum.CONNECT,
                      MsgType.enum.CONNECT,
                      # TODO: different payload? add user_key?
                      payload=self._id,
                      user_id=self._id,
                      user_key=self._key)
        self.debug("_connect_message: "
                   "Created connection message: {}",
                   msg)
        return msg, ctx

    def _request_connect(self) -> None:
        '''
        Flags :meth:`_server_watcher` with a request to get it all going.
        '''
        # TODO: path for my user? With user id, user key?
        self.debug("_request_connect: Requesting connection to server...")
        self._connect_request.set()

    def _desire_connect(self) -> None:
        '''
        Checks `_connect_request` (no block/no wait) to see if we want to
        connect to server.
        '''
        return self._connect_request.is_set()

    def _clear_connect(self) -> None:
        '''
        Clears `_connect_request` flag.
        '''
        self.debug("_clear_connect: "
                   "Done with connection request flag for now.")
        return self._connect_request.clear()

    # -------------------------------------------------------------------------
    # WebSocket Functions
    # -------------------------------------------------------------------------

    async def _htx_connect(self,
                           msg:  Message,
                           ctx:  Optional[MediatorClientContext],
                           conn: UserConnToken) -> Optional[Message]:
        '''
        Send a connection auth/registration request to the server.
        '''
        self.debug("_htx_connect: conn: {}, msg: {}, ctx: {}",
                   conn, msg, ctx)
        return await self._htx_generic(msg, ctx, conn, log_type='connect')

    async def _hrx_connect(self,
                           match:   re.Match,
                           path:    str,
                           msg:     Message,
                           context: Optional[MediatorClientContext]
                           ) -> Optional[Message]:
        '''
        Receive connect ack/response from server.
        '''
        self.debug("_hrx_connect: Received connect response: {}: {}",
                   type(msg.payload), msg.payload)

        # Have Message check that this msg is a ACK_CONNECT and tell us if it
        # succeeded or not.
        success, reason = msg.verify_connected()
        if success:
            self.debug("_hrx_connect: Verified message: {}",
                       msg)
            self._connection_attempt_success()
        else:
            log.error("{self._name}: Failed to connect to server! "
                      f"match: {match}, path: {path}, msg: {msg},"
                      f"Connection failure: {reason}")
            self._connection_attempt_failure()

        self.debug("_hrx_connect: Connection successful.")
        return await self._hrx_generic(match, path, msg, context,
                                       # Don't ack the ack back.
                                       send_ack=False,
                                       log_type='connect')

    async def _hook_produce(self,
                            msg:       Optional[Message],
                            websocket: websockets.WebSocketCommonProtocol
                            ) -> Optional[Message]:
        '''
        Add our user's id/key to the message to be sent to the server.
        '''
        self.debug("_hook_produce saw msg on socket {}: {}",
                   websocket, msg)
        if not msg:
            self.debug("_hook_produce ignoring null message "
                       "on socket {}: {}",
                       websocket, msg)
            return msg

        # This is all we need at the moment...
        msg.user_id = self._id
        msg.user_key = self._key
        self.debug("_hook_produce added user-id/key ({}, {}) to message "
                   "on socket {}: {}",
                   self._id, self._key,
                   websocket, msg)
        return msg

    async def _hook_consume(self,
                            msg:       Optional[Message],
                            websocket: websockets.WebSocketCommonProtocol
                            ) -> Optional[Message]:
        '''
        Check all received messages from server?
        '''
        self.debug("_hook_consume saw msg on socket {}: {}",
                   websocket, msg)
        if not msg:
            self.debug("_hook_consume ignoring null message "
                       "on socket {}: {}",
                       websocket, msg)
            return msg

        # ------------------------------
        # Check User Fields
        # ------------------------------
        valid = True
        # ---
        # User-Id
        # ---
        if msg.user_id != self._id:
            valid = False
            log.warning("_hook_consume: "
                        "Client received user-id that doesn't match expected. "
                        "expected: {}, got: {}. "
                        "msg: {}",
                        self._id, msg.user_id, msg)
        else:
            self.debug("_hook_consume: "
                       "Client received msg for our user-id: ",
                       msg)
        # ---
        # User-Key
        # ---
        if msg.user_key != self._key:
            valid = False
            log.warning("_hook_consume: "
                        "Client received user-key that doesn't match expected. "
                        "expected: {}, got: {}. "
                        "msg: {}",
                        self._key, msg.user_key, msg)
        else:
            self.debug("_hook_consume: "
                       "Client received msg for our user-key: ",
                       msg)

        # TODO: Not sure if we need to actually do anything about
        # `valid == False` here...

        self.debug("_hook_consume: Done.")
        return msg

    def _server_connection(self,
                           path: Optional[str] = None) -> VebSocketClient:
        '''
        Get a new WebSocket connection to our server.
        '''
        self.debug("_server_connection: Creating socket for connection...")
        socket = VebSocketClient(self._serdes,
                                 self._codec,
                                 self.make_med_context,
                                 self.make_msg_context,
                                 self._host,
                                 path=path,
                                 port=self._port,
                                 secure=self._ssl,
                                 debug_fn=self.debug)
        self.debug("_server_connection: Created socket for connection: {}",
                   socket)
        return socket
