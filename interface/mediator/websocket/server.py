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
from typing import Optional, Any, Callable, Awaitable, Iterable, Mapping, Tuple


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
from veredi.base.identity        import MonotonicId
from veredi.data.config.config   import Configuration
from veredi.data.codec.base      import BaseCodec
from veredi.data.config.registry import register

from ..server                    import MediatorServer
from ..exceptions                import async_handle_exception
from .base                       import VebSocket
from ..message                   import Message, MsgType
from ..context                   import MediatorServerContext, MessageContext


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# The '/Actual/' "Talk to the Client" Bit
# -----------------------------------------------------------------------------

class VebSocketServer(VebSocket):
    '''
    Veredi Web Socket asyncio shenanigan class, server edition.
    '''

    def __init__(self,
                 codec:      BaseCodec,
                 context_fn: Callable[[], MediatorServerContext],
                 host:       str,
                 path:       Optional[str] = None,
                 port:       Optional[int] = None,
                 secure:     bool          = True,
                 close:      asyncio.Event = None) -> None:
        super().__init__(codec, host, path, port, secure, close)

        log.debug(f"host: {str(type(self._host))}({self._host}), "
                  f"port: {str(type(self._port))}({self._port}), "
                  f"secure: {str(type(secure))}({secure})")

        log.debug(f"VebSocketServer.serve: created {self.uri}...")

        self._make_context = context_fn

        # bad: self._server = websockets.serve(hello, "localhost", 8765)
        # bad: self._server = websockets.serve(hello, "::1", 8765)
        # works: self._server = websockets.serve(hello, "127.0.0.1", 8765)
        #   - but issues with things running in the 'wrong' asyncio event loop.
        # so... bad?: init-ing here?
        #   - It gets in the wrong asyncio event loop somehow.
        self._server = None

        self._connections: Mapping[MonotonicId, Tuple] = {}

    # -------------------------------------------------------------------------
    # Our Server Functions
    # -------------------------------------------------------------------------

    async def serve(self, process_data_fn) -> None:
        '''
        Start our socket listening. Returns data from client to receive_fn.
        '''
        self._process_data = process_data_fn

        # Create it here, then... don't await it. Let self._a_wait_close() wait
        # on both server and our close flag.
        log.debug(f"VebSocketServer.serve: starting server {self.uri}...")
        server = await websockets.serve(self.handler, self._host, self._port)
        log.debug(f"VebSocketServer.serve: serving {self.uri}...")
        await self._a_wait_close(server)

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

    async def handler(self,
                      websocket: websockets.WebSocketServerProtocol,
                      path:      str) -> None:
        '''
        Handle receiving some data from a client over provided websocket.

        `websocket` is the websocket connection to the client.

        `path` is a url-like path. Only one I've gotten so far in tests
        is root ("/").
        '''
        log.debug(f"VebSocketServer.handler: websocket: {websocket}")
        log.debug(f"VebSocketServer.handler:      path: {path}")

        # Get data from this socket we've been given, I guess...
        try:
            log.debug("VebSocketServer.handler: getting data...")
            raw = await websocket.recv()
            log.debug(f"svr: <--  :  raw: {raw}")
            recv = self.decode(raw, self._make_context())
            log.debug(f"svr: <--  : recv: {recv}")
        except websockets.ConnectionClosedOK:
            #  Connection got closed. Ok.
            return None

        # Call handler to process it.
        result = None
        if self._process_data and callable(self._process_data):
            result = await self._process_data(recv, path)

        # Send result back if we got one.
        if result:
            send = self.encode(result, self._make_context())
            # log.debug(f"svr:  -->: raw: {send}")
            print(f"svr:  -->: raw: {send}")
            await websocket.send(send)


# -----------------------------------------------------------------------------
# The "Mediator-to-Client" Bit
# -----------------------------------------------------------------------------

@register('veredi', 'interface', 'mediator', 'websocket', 'server')
class WebSocketServer(MediatorServer):
    '''
    Mediator for serving over WebSockets.
    '''

    def __init__(self,
                 config:        Configuration,
                 conn:          multiprocessing.connection.Connection,
                 shutdown_flag: multiprocessing.Event) -> None:
        # Base class init first.
        super().__init__(config, conn, shutdown_flag)

        # Grab our data from the config...
        self._codec: BaseCodec = config.make(None,
                                             'server',
                                             'mediator',
                                             'codec')

        self._host:  str       = config.get('server',
                                            'mediator',
                                            'hostname')

        self._port:  int       = int(config.get('server',
                                                'mediator',
                                                'port'))

        self._ssl:   str       = config.get('server',
                                            'mediator',
                                            'ssl')

        # ---
        # Now we can make our WebSocket stuff...
        # ---
        self._listener = VebSocketServer(self._codec,
                                         self.make_context,
                                         self._host,
                                         path=None,
                                         port=self._port,
                                         secure=self._ssl)
        self._rx_queue = asyncio.Queue()
        '''Queue for received data from clients.'''

        self._rx_qid = MonotonicId.generator()
        '''ID for queue items.'''

        # ---
        # Path Regexes to Functions
        # ---
        self._paths = {
            re.compile(r'^/$', re.IGNORECASE):     self._h_root,
            re.compile(r'^/ping$', re.IGNORECASE): self._h_ping,
            re.compile(r'^/echo$', re.IGNORECASE): self._h_echo,
            re.compile(r'^/text$', re.IGNORECASE): self._h_text,
        }

    # -------------------------------------------------------------------------
    # Mediator API
    # -------------------------------------------------------------------------

    def make_context(self) -> MediatorServerContext:
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
                                     self._client_watcher(),
                                     self._game_watcher()))
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

    async def _a_main(self, *aws: Awaitable) -> Iterable[Any]:
        '''
        Runs client async tasks/futures concurrently, returns the aggregate
        list of return values for those tasks/futures.
        '''
        ret_vals = await asyncio.gather(*aws)
        return ret_vals

    async def _shutdown_watcher(self) -> None:
        '''
        Watches `self._shutdown_flag`. Will call stop() on our asyncio loop
        when the shutdown flag is set.
        '''
        await super()._shutdown_watcher()

        # Tell our websocket server to finish up.
        log.debug("Tell our WebSocket to stop.")
        self._listener.close()

        # # Tell ourselves to stop.
        # log.debug("Tell ourselves to stop.")
        # We should have our coroutines watching the shutdown flag.

    async def _game_watcher(self):
        '''
        Loop waiting for messages from our multiprocessing.connection to
        communicate to a client.
        '''
        while True:
            # Die if requested.
            if self._shutdown:
                break

            # Check for something in connection to send; don't block.
            if not self._game.poll():
                await asyncio.sleep(0.1)
                continue

            log.debug("server._game_watcher has message.")
            # Have something to send; receive it from game connection so
            # we can send it.
            msg, ctx = self._game.recv()
            log.critical("server._game_watcher: recvd for sending: "
                         f"msg: {msg}, ctx: {ctx}")

            # TODO: stuff out of context, like something to ident client.
            log.critical("TODO: FINISH THIS FUNC!!!")

            # # ---
            # # Send Handlers by MsgType
            # # ---
            # if msg.type == MsgType.PING:
            #     log.debug("server._game_watcher: pinging...")
            #     reply = await self._ping(msg)
            #     log.debug(f"server._game_watcher: ping'd: {reply}")
            #     self._game.send(reply)

            # elif msg.type == MsgType.ECHO:
            #     log.debug("server._game_watcher: echoing...")
            #     reply = await self._echo(msg)
            #     log.debug(f"server._game_watcher: echo'd: {reply}")
            #     self._game.send(reply)

            # elif msg.type == MsgType.TEXT:
            #     log.debug("server._game_watcher: texting...")
            #     reply = await self._text(msg)
            #     log.debug(f"server._game_watcher: text'd: {reply}")
            #     self._game.send(reply)

            # else:
            #     log.error(f"Unhandled message type {msg.type} for "
            #               f"message: {msg}. Ignoring.")

    async def _client_watcher(self) -> None:
        '''
        Deals with sending data in our queue out to the game over our
        multiprocessing connection to it.
        '''
        # Don't block...
        while True:
            if self._shutdown:
                # Finish out of this coroutine if we should die.
                return

            if self._rx_queue.empty():
                await asyncio.sleep(0.1)

            # Else get one thing and send it off this round.
            try:
                msg, ctx = self._rx_queue.get_nowait()
                if not msg or not ctx:
                    continue
            except asyncio.QueueEmpty:
                # get_nowait() got nothing. That's fine; go back to waiting.
                continue

            # Transfer from 'received from client queue' to
            # 'sent to game connection'.
            print(f"send to game conn: {(msg, ctx)}")
            self._game.send((msg, ctx))

            # Skip this - we used get_nowait(), not get().
            # self._rx_queue.task_done()

    # -------------------------------------------------------------------------
    # WebSocket Asyncio Functions
    # -------------------------------------------------------------------------

    async def _serve(self):
        '''
        Read from client, send reply, close connection.
        '''
        await self._listener.serve(self._handle)
        log.debug("Server._serve: Done.")

    def _path_handler(self, path: str) -> Callable:
        '''
        Takes a path and returns:
          - None: Path is unknown.
          - A 2-tuple of:
            - The re.Match object for the path matching.
            - The handler for that path.
        '''
        for regex, func in self._paths.items():
            match = regex.fullmatch(path)
            if match:
                return match, func

        return None, None

    async def _handle(self, msg: Message, path: str) -> None:
        '''
        TODO: better docstr
        '''
        match, handler = self._path_handler(path)
        if not handler:
            # TODO [2020-07-29]: Log info about client too.
            log.error("Unhandled path: ", path)
            return None

        return await handler(path, match, msg)

    # -------------------------------------------------------------------------
    # Specific Path Handlers
    # -------------------------------------------------------------------------

    async def _h_ping(self,
                      match: re.Match,
                      path: str,
                      msg: Message) -> None:
        '''
        Handle a ping.
        '''
        return None

    async def _h_echo(self,
                      match: re.Match,
                      path: str,
                      msg: Message) -> Message:
        '''
        Handle an echo.
        '''
        return msg

    async def _h_text(self,
                      match: re.Match,
                      path: str,
                      msg: Message) -> Message:
        '''
        Handle a message with text payload.
        '''
        qid = self._rx_qid.next()
        ctx = MessageContext(self.dotted, qid)
        # log.debug(f"queuing: msg: {msg}, ctx: {ctx}")
        print(f"queuing: msg: {msg}, ctx: {ctx}")
        await self._rx_queue.put((msg, ctx))
        send = Message(msg.id, MsgType.ACK_ID, qid)
        print(f"sending ack: {send}")
        return send

    async def _h_root(self,
                      match: re.Match,
                      path: str,
                      msg: Message) -> None:
        '''
        Handle a request to root path ("/").
        '''
        raise NotImplementedError("TODO: THIS.")
        return None
