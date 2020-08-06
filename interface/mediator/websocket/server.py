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
                    Callable, Awaitable, Iterable, Dict, Set)


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
from veredi.data.config.config   import Configuration
from veredi.data.codec.base      import BaseCodec
from veredi.data.config.registry import register

from ..server                    import MediatorServer
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

        # self._clients[uid] = websocket

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
class WebSocketServer(MediatorServer):
    '''
    Mediator for serving over WebSockets.
    '''

    def __init__(self,
                 config:        Configuration,
                 conn:          multiprocessing.connection.Connection,
                 shutdown_flag: multiprocessing.Event,
                 debug:         DebugFlag = None) -> None:
        # Base class init first.
        super().__init__(config, conn, shutdown_flag, debug)

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
                                         self.make_med_context,
                                         self.make_msg_context,
                                         self._host,
                                         path=None,
                                         port=self._port,
                                         secure=self._ssl,
                                         debug_fn=self.debug)
        self._rx_queue = asyncio.Queue()
        '''Queue for received data from clients.'''

        self._rx_qid = MonotonicId.generator()
        '''ID for queue items.'''

        # ---
        # Path Regexes to Functions
        # ---
        reic = re.IGNORECASE
        self._hp_paths_re = {
            re.compile(r'^/$',     reic): (self._htx_root, self._hrx_root),
            re.compile(r'^/ping$', reic): (self._htx_ping, self._hrx_ping),
            re.compile(r'^/echo$', reic): (self._htx_echo, self._hrx_echo),
            re.compile(r'^/text$', reic): (self._htx_text, self._hrx_text),
        }
        '''
        "Handle Parallel" Paths (separate handlers for sending, receiving).
        The "I have a path; what do I do?" version.
        '''

        self._hp_paths_type = {
            MsgType.INVALID:   (self._htx_root, self._hrx_root),
            MsgType.PING:      (self._htx_ping, self._hrx_ping),
            MsgType.ECHO:      (self._htx_echo, self._hrx_echo),
            MsgType.ECHO_ECHO: (self._htx_echo, self._hrx_echo),
            MsgType.TEXT:      (self._htx_text, self._hrx_text),
            MsgType.ACK_ID:    (self._htx_ack,  self._hrx_ack),
        }
        '''
        "Handle Parallel" Paths (separate handlers for sending, receiving).
        The "I have a message; what do I do?" version.
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
        if (self._debug
                and self._debug.any(DebugFlag.MEDIATOR_BASE,
                                    DebugFlag.MEDIATOR_SERVER)):
            kwargs = log.incr_stack_level(kwargs)
            log.debug(msg,
                      *args,
                      **kwargs)

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
        self.debug("Tell our WebSocket to stop.")
        self._listener.close()

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
            self.debug(f"Send to game conn: {(msg, ctx)}")
            self._game.send((msg, ctx))

            # Skip this - we used get_nowait(), not get().
            # self._rx_queue.task_done()

    async def _rx_enqueue(self,
                          msg: Message,
                          ctx: Optional[MessageContext] = None) -> None:
        '''
        Enqueues `msg` into the rx_queue with either the supplied or a default
        message context.
        '''
        qid = self._rx_qid.next()
        ctx = ctx or MessageContext(self.dotted, qid)
        self.debug(f"enqueuing: msg: {msg}, ctx: {ctx}")
        await self._rx_queue.put((msg, ctx))

    # -------------------------------------------------------------------------
    # WebSocket Server
    # -------------------------------------------------------------------------

    async def _serve(self) -> None:
        '''
        Read from client, send reply, close connection.
        '''
        uri = self._listener.uri
        self.debug(f"Starting to serve: {uri}")
        # await self._listener.serve_basic(self._handle_basic)
        await self._listener.serve_parallel(self._handle_produce,
                                            self._handle_consume)
        self.debug(f"Done serving: {uri}")

    # -------------------------------------------------------------------------
    # Parallel/Separate TX/RX Handlers
    # -------------------------------------------------------------------------

    async def _handle_produce(self) -> Optional[Message]:
        '''
        Handles a `VebSocketServer.serve_parallel` produce data callback.
        '''
        while True:
            # Die if requested.
            if self._shutdown:
                break

            # Check for something in connection to send; don't block.
            if not self._game.poll():
                await asyncio.sleep(0.1)
                continue

            self.debug("Game has message.")
            # Have something to send; receive it from game connection so
            # we can send it.
            msg, ctx = self._game.recv()
            self.debug(f"recvd for sending: msg: {msg}, ctx: {ctx}")

            if not msg:
                log.warning("No message for sending? "
                            f"Ignoring msg: {msg}, ctx: {ctx}")
                continue

            sender, _ = self._hp_paths_type.get(msg.type, None)
            if not sender:
                log.error("No handlers for msg type? "
                          f"Ignoring msg: {msg}, ctx: {ctx}")
                continue

            self.debug("sending...")
            return await sender(msg)

    async def _handle_consume(self,
                              msg: Message,
                              path: str) -> Optional[Message]:
        '''
        Handles a `VebSocketServer.serve_parallel` consume data callback.
        '''
        self.debug(f"Consuming a message on path: {path}: {msg}")
        match, processor = self._hrx_path_processor(path)
        self.debug(f"match: {match}, processor: {processor}")
        if not processor:
            # TODO [2020-07-29]: Log info about client too.
            log.error("Tried to consume message for unhandled path: {}, {}",
                      msg, path)
            return None

        self.debug("Sending to path processor to consume...")
        return await processor(match, path, msg)

    def _hrx_path_processor(self, path: str) -> Callable:
        '''
        Takes a path and returns:
          - None: Path is unknown.
          - A 2-tuple of:
            - The re.Match object for the path matching.
            - The rx handler for that path.
        '''
        for regex, func_tuple in self._hp_paths_re.items():
            match = regex.fullmatch(path)
            if match:
                return match, func_tuple[1]

        return None, None

    # ------------------------------
    # "TX/RX" Specific Path Handlers?
    # ------------------------------

    async def _htx_ping(self,
                        msg: Message) -> Message:
        '''
        Handle sending a ping?
        '''
        self.debug(f"ping triggered by: {msg}...")
        self.debug("start...")

        elapsed = await self._listener.ping()
        self.debug(f"pinged: {elapsed}")

        reply = Message(msg.id, msg.type, elapsed)
        await self._rx_enqueue(reply)

        # Don't actually need/want to send anything...
        return None

    async def _hrx_ping(self,
                        match: re.Match,
                        path: str,
                        msg: Message) -> None:
        '''
        Handle receiving a ping. By doing nothing.
        '''
        self.debug("got ping; ignoring. "
                   f"path: {path}, match: {match}, msg: {msg}...")
        return None

    async def _htx_echo(self,
                        msg: Message) -> Message:
        '''
        Handles sending an echo.
        '''
        self.debug(f"echoing {msg}...")
        return msg

    async def _hrx_echo(self,
                        match: re.Match,
                        path: str,
                        msg: Message) -> Message:
        '''
        Handles receiving an echo.

        ...By just giving back what we got.
        ...Or returning the echo-back to the game.
        '''
        if msg.type == MsgType.ECHO:
            # Received echo from client to send back.
            self.debug("got echo; returning it."
                       f"path: {path}, match: {match}, msg: {msg}...")
            return Message.echo(msg)
        else:
            self.debug("got echo-back; enqueuing."
                       f"path: {path}, match: {match}, msg: {msg}...")
            # Received echo-back from client; send to game.
            # TODO: add path into context
            await self._rx_enqueue(msg)

    async def _htx_text(self,
                        msg: Message) -> Message:
        '''
        Handle sending a message with text payload.
        '''
        self.debug(f"sending text {msg}...")
        return msg

    async def _hrx_text(self,
                        match: re.Match,
                        path: str,
                        msg: Message) -> Message:
        '''
        Handle receiving a message with text payload.
        '''
        # Receive from client; put into rx_queue.
        #
        # Game will get it eventually and deal with it. We may get a reply to
        # send at some point but that's irrelevant here.

        qid = self._rx_qid.next()
        ctx = MessageContext(self.dotted, qid)
        self.debug("received text msg; queuing: "
                   f"msg: {msg}, ctx: {ctx}")
        await self._rx_queue.put((msg, ctx))
        send = Message(msg.id, MsgType.ACK_ID, qid)
        self.debug(f"sending text ack: {send}")
        return send

    async def _htx_ack(self,
                       msg: Message) -> Message:
        '''
        Handle sending a message with an ACK_ID payload.
        '''
        log.warning("...Why is the TX handler for ACK involved?")
        self.debug(f"sending ack {msg}...")
        return msg

    async def _hrx_ack(self,
                       match: re.Match,
                       path: str,
                       msg: Message) -> Message:
        '''
        Handle receiving a message with an ACK_ID payload.
        '''
        # Receive from client; put into rx_queue.
        #
        # Game will get it eventually and deal with it. We may get a reply to
        # send at some point but that's irrelevant here.
        ctx = MessageContext(self.dotted, msg.message)
        self.debug("received text msg; queuing: "
                   f"msg: {msg}, ctx: {ctx}")
        await self._rx_queue.put((msg, ctx))

        # Don't ack the ack.
        return None

    async def _htx_root(self,
                        match: re.Match,
                        path: str,
                        msg: Message) -> None:
        '''
        Handle a send request to root path ("/").
        '''
        raise NotImplementedError("TODO: THIS.")
        return None

    async def _hrx_root(self,
                        match: re.Match,
                        path: str,
                        msg: Message) -> None:
        '''
        Handle receiving a request to root path ("/").
        '''
        self.debug(f"Received: path: {path}, match: {match}, msg: {msg}")

        # Do I have someone else to give this to?
        _, receiver = self._hp_paths_type.get(msg.type, None)
        if receiver:
            self.debug(f"forward to: {receiver}")
            return await receiver(match, path, msg)

        # else:
        # Ok, give up.
        log.warning("No handlers for msg; ignoring: "
                    f"path: {path}, match: {match}, msg: {msg}")
        return None
