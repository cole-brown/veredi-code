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
from veredi.data                 import background
from veredi.data.config.config   import Configuration
from veredi.data.codec.base      import BaseCodec
from veredi.data.config.registry import register

from ..message                   import Message, MsgType
from ..client                    import MediatorClient
from .base                       import VebSocket, TxRxProcessor
from ..context                   import MediatorClientContext, MessageContext
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
            produce_fn: TxRxProcessor,
            consume_fn: TxRxProcessor
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

            self.debug("Client done with connection to {self.uri}. Cancelling "
                       "still pending tasks produce/consume tasks...")
            # Whoever didn't finish first gets the axe.
            for task in pending:
                task.cancel()

        self._socket = None
        self.debug("Client connection done.")


# -----------------------------------------------------------------------------
# Client (Veredi)
# -----------------------------------------------------------------------------

@register('veredi', 'interface', 'mediator', 'websocket', 'client')
class WebSocketClient(MediatorClient):
    '''
    Mediator for... client-ing over WebSockets.
    '''

    def __init__(self,
                 config:        Configuration,
                 conn:          multiprocessing.connection.Connection,
                 shutdown_flag: multiprocessing.Event,
                 debug:         DebugFlag = None) -> None:
        # Base class init first.
        super().__init__(config, conn, shutdown_flag, debug)

        # Grab our data from the config...
        self._codec:  BaseCodec       = config.make(None,
                                                    'client',
                                                    'mediator',
                                                    'codec')

        self._host:   str             = config.get('client',
                                                   'mediator',
                                                   'hostname')

        self._port:   int             = int(config.get('client',
                                                       'mediator',
                                                       'port'))

        self._ssl:    str             = config.get('client',
                                                   'mediator',
                                                   'ssl')

        # ---
        # Now we can make our WebSocket stuff...
        # ---
        self._connect_request: asyncio.Event = None
        '''
        Flag to indicate our server connection asyncio task should connect to
        server and start running the producer/consumer pipelines.
        '''

        self._server: VebSocketClient = None
        '''
        Our connection to the MediatorServer that we'll try to keep open and do
        all communication through.
        '''

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

        self._init_background()

    def _init_background(self):
        '''
        Insert the mediator context data into the background.
        '''
        bg_data, bg_owner = self._background
        background.mediator.set(self.dotted,
                                bg_data,
                                bg_owner)

    @property
    def _background(self):
        '''
        Get background data for init_background()/background.mediator.set().
        '''
        self._bg = {
            'dotted': self.dotted,
            'type': 'websocket.server',
            'codec': self._codec.dotted,
        }
        return self._bg, background.Ownership.SHARE

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
            kwargs = log.incr_stack_level(kwargs)
            log.debug(msg,
                      *args,
                      **kwargs)

    # -------------------------------------------------------------------------
    # Mediator API
    # -------------------------------------------------------------------------

    def make_med_context(self) -> MediatorClientContext:
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
                                     self._server_watcher()))

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

    def _game_has_data(self) -> bool:
        '''Returns True if queue from game has data to send to server.'''
        return self._game.poll()


    async def _shutdown_watcher(self) -> None:
        '''
        Watches `self._shutdown_flag`. Will call stop() on our asyncio loop
        when the shutdown flag is set.
        '''
        # Parent's watcher is non-blocking so we can be simple about this:
        await super()._shutdown_watcher()

        # If we have a server conn, ask it to close too.
        if self._server:
            self._server.close()

    async def _queue_watcher(self):
        '''
        Loop waiting on messages in our _rx_queue to send down to the game.
        '''
        while True:
            # Die if requested.
            if self._shutdown:
                break

            # Check for something in connection to send; don't block.
            if self._rx_queue.empty():
                await asyncio.sleep(0.1)
                continue

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

    async def _server_watcher(self) -> None:
        '''
        AsyncIO awaitable. Will sleep until client wants to connect to server,
        then will await our :meth:`_server_connection` connection's
        :meth:`connect_parallel` for sending/receiving messages.

        Opens connection to the server, then can send and receive in parallel
        in the :meth:`_handle_produce` and :meth:`_handle_consume` functions.
        '''
        self._connect_request = asyncio.Event()
        self.debug("Starting an endless loop...")

        # Wait for someone to want to talk to server...
        while True:
            # Check exit condition.
            if self._shutdown:
                self.debug("Obeying shutdown request...")
                if self._server:
                    self._server.close()
                    self._server = None
                return

            # If game has data to send and we're not running, try
            # maybe running?
            if self._game_has_data():
                self._connect_request.set()

            # Check... enter condition.
            if not self._connect_request.is_set():
                await asyncio.sleep(0.1)
                continue
            self._connect_request.clear()

            # Ok. Bring server connection online.
            self.debug("Starting connection to server...")

            if self._server:
                raise log.exception(None,
                                    WebSocketError,
                                    "WebSocket to server exists but we were "
                                    "expecting it not to. {}",
                                    self._server)

            # TODO: path for my user? With user key, user secret?
            self.debug("Creating connection to server...")
            self._server = self._server_connection()

            self.debug("Starting connection handlers...")
            await self._server.connect_parallel(self._handle_produce,
                                                self._handle_consume)
            self.debug("Done with connection to server.")

            # And back to waiting on the connection request flag.
            self._server = None

    async def connect(self) -> None:  # TODO: user param?
        '''
        Flags :meth:`_server_watcher` with a request to get it all going.
        '''
        # TODO: path for my user? With user key, user secret?
        self.debug("Requesting connection to server...")
        self._connect_request.set()

    async def _rx_enqueue(self,
                          msg: Message,
                          ctx: Optional[MessageContext] = None) -> None:
        '''
        Enqueues `msg` into the rx_queue with either the supplied or a default
        message context.
        '''
        qid = self._rx_qid.next()
        ctx = ctx or MessageContext(self.dotted, qid)
        self.debug(f"queuing: msg: {msg}, ctx: {ctx}")
        await self._rx_queue.put((msg, ctx))

    # -------------------------------------------------------------------------
    # WebSocket Functions
    # -------------------------------------------------------------------------

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

    async def _handle_produce(self):
        '''
        Loop waiting for messages from our multiprocessing.connection to
        communicate about with the MediatorServer.
        '''
        while True:
            # Die if requested.
            if self._shutdown:
                break

            # Check for something in connection to send; don't block.
            if not self._game_has_data():
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

            self.debug("Producing result from send processor...")
            result = await sender(msg)

            # Only send out to socket if actually produced anything.
            if result:
                self.debug(f"Sending {result}...")
                return result

            else:
                self.debug("No result to send; done.")
                # reloop

    async def _handle_consume(self,
                              msg: Message,
                              path: str) -> Optional[Message]:
        '''
        Handles a `VebSocketClient.connect_parallel` consume data callback.
        '''
        match, processor = self._hrx_path_processor(path)
        if not processor:
            # TODO [2020-07-29]: Log info about client too.
            log.error("Tried to consume message for unhandled path: {}, {}",
                      msg, path)
            return None

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
    # "Parallel TX/RX" Handlers
    # ------------------------------

    async def _htx_ping(self,
                        msg: Message) -> Message:
        '''
        Handle sending a ping?
        '''
        self.debug(f"ping triggered by: {msg}...")
        self.debug("start...")

        elapsed = await self._server.ping(msg,
                                          self.make_med_context())
        self.debug(f"pinged: {elapsed}")
        reply = Message(msg.id, msg.type, elapsed)
        await self._rx_enqueue(reply)

        # No return; don't want to actually send anything.

    async def _hrx_ping(self,
                        match: re.Match,
                        path: str,
                        msg: Message) -> None:
        '''
        Handle receiving a ping. By doing nothing.
        '''
        self.debug("got ping; ignoring."
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
            # Received echo from server to send back.
            self.debug("Got echo; returning it."
                       f"path: {path}, match: {match}, msg: {msg}...")
            return Message.echo(msg)
        else:
            self.debug("Got echo-back; enqueuing."
                       f"path: {path}, match: {match}, msg: {msg}...")
            # Received echo-back from server; send to game.
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
            self.debug(f"Forward to: {receiver}")
            return await receiver(match, path, msg)

        # else:
        # Ok, give up.
        log.warning("No handlers for msg; ignoring: "
                    f"path: {path}, match: {match}, msg: {msg}")
        return None
