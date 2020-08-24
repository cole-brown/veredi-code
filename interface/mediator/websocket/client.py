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


# ---
# Veredi Imports
# ---
from veredi.logger               import log
from veredi.debug.const          import DebugFlag
from veredi.base.identity        import MonotonicId
from veredi.data.identity        import UserId
from veredi.data                 import background
from veredi.data.config.config   import Configuration
from veredi.data.codec.base      import BaseCodec
from veredi.data.config.registry import register

from ..message                   import Message, MsgType
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
                 codec:          BaseCodec,
                 med_context_fn: Callable[[], MediatorClientContext],
                 msg_context_fn: Callable[[], MessageContext],
                 host:           str,
                 path:           Optional[str]           = None,
                 port:           Optional[int]           = None,
                 secure:         Optional[bool]          = True,
                 debug_fn:       Optional[Callable]      = None) -> None:
        super().__init__(codec, med_context_fn, msg_context_fn,
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
        self.debug(f"Client connecting to {self.uri}...")

        self._data_produce = produce_fn
        self._data_consume = consume_fn

        async with websockets.connect(self.uri) as websocket:
            self.debug(f"Client connected to {self.uri}. "
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
            self.debug("Client running produce/consume...")
            done, pending = await asyncio.wait(
                [produce, consume, poison],
                return_when=asyncio.FIRST_COMPLETED)

            self.debug(f"Client done with connection to {self.uri}. "
                       "Cancelling still pending tasks "
                       "produce/consume tasks...")
            # Whoever didn't finish first gets the axe.
            for task in pending:
                task.cancel()

        self._socket = None
        self.debug("Client connection done.")


# -----------------------------------------------------------------------------
# Client (Veredi)
# -----------------------------------------------------------------------------

@register('veredi', 'interface', 'mediator', 'websocket', 'client')
class WebSocketClient(WebSocketMediator):
    '''
    Mediator for... client-ing over WebSockets.
    '''

    def __init__(self,
                 config:         Configuration,
                 conn:           multiprocessing.connection.Connection,
                 shutdown_flag:  multiprocessing.Event,
                 user_id:        Optional[UserId]                      = None,
                 user_key:       Optional[UserId]                      = None,
                 debug:          Optional[DebugFlag]                   = None,
                 unit_test_pipe: multiprocessing.connection.Connection = None
                 ) -> None:
        # Base class init first.
        super().__init__(config, conn, shutdown_flag, 'client',
                         debug=debug,
                         unit_test_pipe=unit_test_pipe)

        self._id: Optional[UserId] = user_id
        '''Our auth id for talking to server.'''
        self._key: Optional[UserId] = user_key
        '''Our auth key for talking to server.'''

        # ---
        # Now we can make our WebSocket stuff...
        # ---
        self._connect_request: asyncio.Event = asyncio.Event()
        '''
        Flag to indicate our server connection asyncio task should connect to
        server and start running the producer/consumer pipelines.
        '''

        self._connected: bool = True
        '''
        Have we managed to connect to server yet?

        Note: Not really "are we connected right now". Just "has the server
        confirmed our CONNECT with an ACK_CONNECT at some point in the past?"
        '''

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
              msg: str,
              *args: Any,
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
            log.debug(msg,
                      *args,
                      **kwargs)

    # -------------------------------------------------------------------------
    # Mediator API
    # -------------------------------------------------------------------------

    def make_med_context(self,
                         connection: websockets.WebSocketCommonProtocol = None
                         ) -> MediatorClientContext:
        '''
        Make a context with our context data, our codec's, etc.
        '''
        ctx = MediatorClientContext(self.dotted)
        ctx.sub['type'] = 'websocket.client'
        ctx.sub['codec'] = self._codec.make_context_data()
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
                None,
                "Caught exception running MediatorClient coroutines:\n{}",
                trace)

    # -------------------------------------------------------------------------
    # Asyncio / Multiprocessing Functions
    # -------------------------------------------------------------------------

    async def _shutdown_watcher(self) -> None:
        '''
        Watches `self._shutdown_process`. Will call stop() on our asyncio loop
        when the shutdown flag is set.
        '''
        # Parent's watcher is non-blocking so we can be simple about this:
        await super()._shutdown_watcher()

        # If we have a server conn, ask it to close too.
        if self._socket:
            self._socket.close()

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
                if not msg or not ctx:
                    await self._continuing()
                    continue
            except asyncio.QueueEmpty:
                # get_nowait() got nothing. That's fine; go back to waiting.
                await self._continuing()
                continue

            # Transfer from 'received from server queue' to
            # 'sent to game connection'.
            self.debug(f"Send to game conn: {(msg, ctx)}")
            self._game_pipe_put(msg, ctx)

            # Skip this - we used get_nowait(), not get().
            # self._rx_queue.task_done()
            await self._continuing()

    async def _server_watcher(self) -> None:
        '''
        AsyncIO awaitable. Will sleep until client wants to connect to server,
        then will await our :meth:`_server_connection` connection's
        :meth:`connect_parallel` for sending/receiving messages.

        Opens connection to the server, then can send and receive in parallel
        in the :meth:`_handle_produce` and :meth:`_handle_consume` functions.
        '''
        self.debug("Starting an endless loop...")

        # Wait for someone to want to talk to server...
        while True:
            # Check exit condition.
            if self.any_shutdown():
                self.debug("Obeying shutdown request...")
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
                await self._continuing()
                continue
            self._clear_connect()

            # Ok. Bring server connection online.
            self.debug("Starting connection to server...")

            if self._socket:
                raise log.exception(None,
                                    WebSocketError,
                                    "WebSocket to server exists but we were "
                                    "expecting it not to. {}",
                                    self._socket)

            # TODO: path for my user? With user id, user key?
            self.debug("Creating connection to server...")
            self._socket = self._server_connection()

            # TODO: get connect message working
            self.debug("Queueing connect message...")
            connect_msg, connect_ctx = self._connect_message()
            await self._med_tx_put(connect_msg, connect_ctx)

            self.debug("Starting connection handlers...")
            await self._socket.connect_parallel(self._handle_produce,
                                                self._handle_consume)
            self.debug("Done with connection to server.")

            # And back to waiting on the connection request flag.
            self._socket = None
            await self._continuing()

    def _connect_message(self, ctx: Optional[MessageContext] = None) -> None:
        '''
        Queue up a connection message to server for auth/user registration.
        '''
        ctx = ctx or self.make_msg_context(Message.SpecialId.CONNECT)
        msg = Message(Message.SpecialId.CONNECT,
                      MsgType.CONNECT,
                      # TODO: different payload? add user_key?
                      payload=self._id,
                      user_id=self._id,
                      user_key=None)
        return msg, ctx

    def _request_connect(self) -> None:
        '''
        Flags :meth:`_server_watcher` with a request to get it all going.
        '''
        # TODO: path for my user? With user id, user key?
        self.debug("Requesting connection to server...")
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
        return await self._htx_generic(msg, ctx, conn, 'connect')

    async def _hrx_connect(self,
                           match: re.Match,
                           path: str,
                           msg: Message,
                           context: Optional[MediatorClientContext]
                           ) -> Optional[Message]:
        '''
        Receive connect ack/response from server.
        '''
        payload = msg.payload
        self.debug(f"Received connect response: {type(payload)}: {payload}")

        # TODO: Whatever builds connect payload should also check it here...
        if 'code' in payload and payload['code'] is True:
            if self._debug and not self._debug.has(DebugFlag.LOG_SKIP):
                log.info("{self._name}: Connected to server! "
                         f"match: {match}, path: {path}, msg: {msg}")
            self._connected = True
        else:
            log.error("{self._name}: Failed to connect to server! "
                      f"match: {match}, path: {path}, msg: {msg}")
            self._connected = False

            # Should we close here? Think so... But currently that'll just have
            # mediator keep trying. Need mediator or game to give up or
            # something.
            # TODO [2020-08-13]: Give up if too many failed connects?
            # TODO [2020-08-13]: Give up if a 'give up' fail code?
            self._socket.close()
            self._socket = None

        return await self._hrx_generic(match, path, msg, context,
                                       # Don't ack the ack back.
                                       send_ack=False,
                                       log_type='connect')

    async def _hook_produce(self,
                            msg: Optional[Message],
                            websocket: websockets.WebSocketCommonProtocol
                            ) -> Optional[Message]:
        '''
        Add our user's id/key to the message to be sent to the server.
        '''
        if not msg:
            return msg

        # This is all we need at the moment...
        msg.user_id = self._id
        # TODO: key too...
        # msg.user_key = self._key
        return msg

    async def _hook_consume(self,
                            msg: Optional[Message],
                            websocket: websockets.WebSocketCommonProtocol
                            ) -> Optional[Message]:
        '''
        Check all received messages from server?
        '''
        if not msg:
            return msg

        # Just log it and return...
        if msg.user_id != self._id:
            log.warning("Client received msg id that doesn't match expected."
                        f"Expected: {str(self._id)}, Got: {str(msg.user_id)}. "
                        f"Msg: {msg}")
        return msg

    def _server_connection(self,
                           path: Optional[str] = None) -> VebSocketClient:
        '''
        Get a new WebSocket connection to our server.
        '''
        socket = VebSocketClient(self._codec,
                                 self.make_med_context,
                                 self.make_msg_context,
                                 self._host,
                                 path=path,
                                 port=self._port,
                                 secure=self._ssl,
                                 debug_fn=self.debug)
        return socket