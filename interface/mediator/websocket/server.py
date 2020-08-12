# coding: utf-8

'''
Veredi module for allowing communication via WebSockets.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Type Hinting Imports
# ---
from typing import (Optional, Union, Any, NewType,
                    Callable, Dict, Set)


# ---
# Python Imports
# ---
import asyncio
import websockets
import multiprocessing
import multiprocessing.connection
import re


# ---
# Veredi Imports
# ---
from veredi.logger               import log
from veredi.debug.const          import DebugFlag
from veredi.base.identity        import MonotonicId
from veredi.data                 import background
from veredi.data.config.config   import Configuration
from veredi.data.codec.base      import BaseCodec
from veredi.data.config.registry import register

from .mediator                   import WebSocketMediator
from .exceptions                 import WebSocketError
from .base                       import VebSocket, TxRxProcessor
from ..message                   import Message, MsgType
from ..context                   import MediatorServerContext, MessageContext


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO [2020-08-01]: Make this an actual ID type? Get from game?
UserId = NewType('UserId',
                 Union[int, MonotonicId])
'''A way to track users and their WebSocket connections.'''


# -----------------------------------------------------------------------------
# The '/Actual/' "Talk to the Client" Bit
# -----------------------------------------------------------------------------

class VebSocketServer(VebSocket):
    '''
    Veredi Web Socket asyncio shenanigan class, server edition.
    '''

    SHORT_NAME = 'base'
    ''' Should be 'client' or 'server', depending. '''

    def __init__(self,
                 codec:          BaseCodec,
                 med_context_fn: Callable[[], MediatorServerContext],
                 msg_context_fn: Callable[[], MessageContext],
                 host:           str,
                 path:           Optional[str]              = None,
                 port:           Optional[int]              = None,
                 secure:         Optional[Union[str, bool]] = True,
                 debug_fn:       Optional[Callable]         = None) -> None:
        super().__init__(codec, med_context_fn, msg_context_fn,
                         host,
                         path=path,
                         port=port,
                         secure=secure,
                         debug_fn=debug_fn)

        self.debug(f"host: {str(type(self._host))}({self._host}), "
                   f"port: {str(type(self._port))}({self._port}), "
                   f"secure: {str(type(secure))}({secure})")

        self.debug(f"created {self.uri}...")

        # bad: self._server = websockets.serve(hello, "localhost", 8765)
        # bad: self._server = websockets.serve(hello, "::1", 8765)
        # works: self._server = websockets.serve(hello, "127.0.0.1", 8765)
        #   - but issues with things running in the 'wrong' asyncio event loop.
        # so... bad?: init-ing here?
        #   - It gets in the wrong asyncio event loop somehow.
        self._server: websockets.WebSocketServer = None

        # TODO [2020-08-05]: start using _clients instead of _sockets_open?
        self._clients: Dict[UserId, websockets.WebSocketServerProtocol] = {}
        self._sockets_open: Set[websockets.WebSocketServerProtocol] = set()

        self._paths_ignored: Set[re.Pattern] = set()

    # -------------------------------------------------------------------------
    # Serve
    # -------------------------------------------------------------------------

    async def serve_parallel(
            self,
            produce_fn: TxRxProcessor,
            consume_fn: TxRxProcessor
    ) -> None:
        '''
        Start WebSocket Server listening on `self._host` and `self._port`.
        Clients will be expected to connect somehow first - maybe with a
        friendly hello() - then the `consume_fn` callback will be used for
        receiving data from the client and the `produce_fn` callback will be
        used for sending data back to the client.

        We'll try to keep the connection to the client around for as long as we
        can; we guarentee nothing.
        '''
        self._data_produce = produce_fn
        self._data_consume = consume_fn

        # Create it here, then... don't await it. Let self._a_wait_close() wait
        # on both server and our close flag.
        self.debug(f"starting server {self.uri}...")
        server = await websockets.serve(self.handler_ppc,
                                        self._host,
                                        self._port)
        self.debug(f"serving {self.uri}...")
        await self._a_wait_close(server)

    # -------------------------------------------------------------------------
    # Helper Functions
    # -------------------------------------------------------------------------

    def ignore_path(self, path_re: re.Pattern, remove: bool = False) -> None:
        '''
        Add/remove an ignored path for client socket registration.

        `path_re.fullmatch` is used for making the match, so...
        '''
        if remove:
            self._paths_ignored.remove(path_re)
            return

        self._paths_ignored.add(path_re)

    def register_for_path(self, path: str) -> bool:
        '''
        Returns True if we should register the client socket who just connected
        to this path.

        Returns False if not (for e.g. PING, ECHO).
        '''
        # Check each of our ignores, return False for "Don't Register!" if we
        # match one.
        for regex in self._paths_ignored:
            match = regex.fullmatch(path)
            if match:
                return False

        # Ok; register them.
        return True

    def register(self,
                 websocket: websockets.WebSocketServerProtocol
                 ) -> None:
        '''
        Add this websocket to our collection of clients.
        '''
        # TODO [2020-08-01]: Where do I get a UID from?
        # Need, like, maybe... user key and secret key, like other APIs have?
        # Web Clients can get it from HTML website before they switch on the
        # websocket?

        # clients[uid] = websocket

        self._sockets_open.add(websocket)

    def unregister(self,
                   websocket: websockets.WebSocketServerProtocol
                   ) -> None:
        '''
        Remove this websocket from our collection of clients.
        '''
        # TODO [2020-08-01]: Where do I get a UID from?
        # Need, like, maybe... user key and secret key, like other APIs have?
        # Web Clients can get it from HTML website before they switch on the
        # websocket?

        # self._clients.pop(uid)

        self._sockets_open.remove(websocket)

    async def _a_wait_close(self, server: websockets.WebSocketServer) -> None:
        '''
        A future that just waits for our close flag or
        websockets.WebSocketServer's close future to be set.

        Can be used in a 'loop forever' context to die when instructed.
        '''
        while True:
            if (self._close.is_set()
                    or server.closed_waiter.done()):
                break
            # Await something so other async tasks can run? IDK.
            await asyncio.sleep(0.1)

        # Shutdown has been signaled to us somehow, but we're just some minion
        # so we only need to put ourselves in order.
        server.close()
        self._close.set()

    # -------------------------------------------------------------------------
    # Two-Way Communication Handler
    # -------------------------------------------------------------------------
    #
    # Consumer and producer in parallel.

    async def handler_ppc(self,
                          websocket: websockets.WebSocketServerProtocol,
                          path:      str) -> None:
        '''
        Handles "parallel produce(tx)/consume(rx) on same websocket, keeping it
        around until client leaves or something.

        `websocket` is the websocket connection to the client.

        `path` is a url-like path. Only one I've gotten so far in tests
        is root ("/").

        https://websockets.readthedocs.io/en/stable/intro.html#both
        '''
        self.debug(f"websocket: {websocket}")
        self.debug(f"     path: {path}")

        # Register client as connected.
        if self.register_for_path(path):
            self.debug("VebSocketServer.handler_ppc: registering user...")
            self.register(websocket)

        # Make both consume and produce handlers for this client. Run them in
        # parallel. The first one that finishes signifies an end to our
        # connection over this websocket.
        consume = asyncio.ensure_future(self._ppc_consume(
            websocket,
            self._msg_make_context(path)))
        consume.add_done_callback(self._ppc_done_handle)

        produce = asyncio.ensure_future(self._ppc_produce(
            websocket,
            self._msg_make_context(path)))
        produce.add_done_callback(self._ppc_done_handle)

        # Client has to do this, but we're already using _a_wait_close() for
        # waiting on the socket listener so do not do this 'poison pill' on
        # server.
        # # And this one is just to exit when asked to close().
        # poison = asyncio.ensure_future(self._a_wait_close())
        # poison.add_done_callback(self._ppc_done_handle)

        self.debug("Running produce/consume for user on socket...")
        done, pending = await asyncio.wait(
            [produce, consume],
            return_when=asyncio.FIRST_COMPLETED)

        # Whoever didn't finish first gets the axe.
        for task in pending:
            task.cancel()

        # And we need to forget this client.
        self.unregister(websocket)


# -----------------------------------------------------------------------------
# The "Mediator-to-Client" Bit
# -----------------------------------------------------------------------------

@register('veredi', 'interface', 'mediator', 'websocket', 'server')
class WebSocketServer(WebSocketMediator):
    '''
    Mediator for serving over WebSockets.
    '''

    def __init__(self,
                 config:        Configuration,
                 conn:          multiprocessing.connection.Connection,
                 shutdown_flag: multiprocessing.Event,
                 debug:         DebugFlag = None) -> None:
        # Base class init first.
        super().__init__(config, conn, shutdown_flag, 'server', debug)

        # ---
        # Now we can make our WebSocket stuff...
        # ---
        self._socket = VebSocketServer(self._codec,
                                       self.make_med_context,
                                       self.make_msg_context,
                                       self._host,
                                       path=None,
                                       port=self._port,
                                       secure=self._ssl,
                                       debug_fn=self.debug)

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
                                    DebugFlag.MEDIATOR_SERVER)):
            msg = f"{self._name}: " + msg
            kwargs = log.incr_stack_level(kwargs)
            log.debug(msg,
                      *args,
                      **kwargs)

    def update_logging(self, msg: Message) -> None:
        '''
        Ignore this on server; client doesn't get to tell us what to do.
        '''
        return None

    # -------------------------------------------------------------------------
    # Mediator API
    # -------------------------------------------------------------------------

    def make_med_context(self) -> MediatorServerContext:
        '''
        Make a context with our context data, our codec's, etc.
        '''
        ctx = MediatorServerContext(self.dotted)
        ctx.sub['type'] = 'websocket.server'
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
        The server should start accepting connections, calls from the clients,
        etc. It should be fully armed and operational after this call.

        Kicks of async co-routine for listening for connections.
        '''
        try:
            # Kick it off into asyncio's hands.
            asyncio.run(self._a_main(self._shutdown_watcher(),
                                     self._serve(),
                                     self._med_queue_watcher(),
                                     self._client_watcher()))

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
                "Caught exception running MediatorServer coroutines:\n{}",
                trace)

    # -------------------------------------------------------------------------
    # Asyncio / Multiprocessing Functions
    # -------------------------------------------------------------------------

    async def _shutdown_watcher(self) -> None:
        '''
        Watches `self._shutdown_process`. Will call stop() on our asyncio loop
        when the shutdown flag is set.
        '''
        await super()._shutdown_watcher()

        # Tell our websocket server to finish up.
        self.debug("Tell our WebSocket to stop.")
        self._socket.close()

        # # Tell ourselves to stop.
        # self.debug("Tell ourselves to stop.")
        # We should have our coroutines watching the shutdown flag.

    async def _client_watcher(self) -> None:
        '''
        Deals with sending data in our queue out to the game over our
        multiprocessing connection to it.
        '''
        # Don't block...
        while True:
            if self.any_shutdown():
                # Finish out of this coroutine if we should die.
                return

            if not self._med_to_game_has_data():
                await asyncio.sleep(0.1)

            # Else get one thing and send it off this round.
            try:
                msg, ctx = self._med_to_game_get()
                if not msg or not ctx:
                    continue
            except asyncio.QueueEmpty:
                # get_nowait() got nothing. That's fine; go back to waiting.
                continue

            # Transfer from 'received from client queue' to
            # 'sent to game connection'.
            self.debug(f"Send to game conn: {(msg, ctx)}")
            self._game_pipe_put(msg, ctx)

            # Skip this - we used get_nowait(), not get().
            # self._rx_queue.task_done()

    # -------------------------------------------------------------------------
    # WebSocket Server
    # -------------------------------------------------------------------------

    async def _serve(self) -> None:
        '''
        Read from client, send reply, close connection.
        '''
        uri = self._socket.uri
        self.debug(f"Starting to serve: {uri}")
        # await self._socket.serve_basic(self._handle_basic)
        await self._socket.serve_parallel(self._handle_produce,
                                          self._handle_consume)
        self.debug(f"Done serving: {uri}")

    async def _htx_connect(self,
                           msg: Message) -> Optional[Message]:
        '''
        Send auth/registration result back down to the client.
        '''
        return await self._htx_generic(msg, 'connect')

    async def _hrx_connect(self,
                           match: re.Match,
                           path:  str,
                           msg:   Message) -> Optional[Message]:
        '''
        Handle auth/registration request from a client.
        '''
        log.critical("server: TODO THIS.", match, path, msg)
        return None
