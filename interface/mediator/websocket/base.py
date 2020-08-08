# coding: utf-8

'''
Veredi WebSocket interface.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Type Hinting Imports
# ---
from typing import Optional, Union, NewType, Any, Callable


# ---
# Python Imports
# ---
import websockets
import websockets.client
import asyncio
from io import StringIO


# ---
# Veredi Imports
# ---
from veredi.logger          import log
from veredi.data.codec.base import BaseCodec
from veredi.time.timer      import MonotonicTimer

from ..message               import Message, MsgType
from ..context               import MediatorContext, MessageContext
from .exceptions             import WebSocketError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

TxRxProcessor = NewType(
    'TxRxProcessor',
    Callable[[Message, Optional[MessageContext]], Optional[Message]]
)


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------
# Borrowed a bit of this and that:
#   https://websockets.readthedocs.io/en/stable/intro.html
#   https://stackoverflow.com/questions/42009202/how-to-call-a-async-function-contained-in-a-class

class VebSocket:
    '''
    Veredi Web Socket asyncio shenanigan class.
    '''

    SCHEME_WS_STD = 'ws'      # WebSockets
    SCHEME_WS_SECURE = 'wss'  # WebSockets w/ TLS (SSL)

    # General URI format is:
    #   URI = scheme:[//authority]path[?query][#fragment]
    #     - Authority is:
    #       authority = [userinfo@]host[:port]
    # So:
    URI_FMT = '{scheme}://{host}{port}{path}'
    PORT_FMT = ':{port}'
    PATH_FMT = '/{path}'

    PATH_ROOT = '/'

    SHORT_NAME = 'base'
    ''' Should be 'client' or 'server', depending. '''

    def __init__(self,
                 codec:          BaseCodec,
                 med_context_fn: Callable[[], MediatorContext],
                 msg_context_fn: Callable[[], MessageContext],
                 host:           str,
                 path:           Optional[str]              = None,
                 port:           Optional[int]              = None,
                 secure:         Optional[Union[str, bool]] = True,
                 debug_fn:       Optional[Callable]         = None) -> None:

        # ---
        # Required
        # ---
        self._codec:            BaseCodec                     = codec
        self._med_make_context: Callable[[], MediatorContext] = med_context_fn
        self._msg_make_context: Callable[[], MessageContext]  = msg_context_fn
        self._host:             str                           = host

        # ---
        # Optional
        # ---
        self._path:             str                           = path
        self._port:             int                           = port
        self._secure:           Union[str, bool]              = secure
        self._uri:              Optional[str]                 = None
        self._debug_fn:         Optional[Callable]            = debug_fn

        # ---
        # Internal
        # ---
        self._socket: websockets.WebSocketClientProtocol = None
        self._close:      asyncio.Event = asyncio.Event()

        # For self.connect_parallel_txrx
        self._data_consume: TxRxProcessor = None
        '''
        Data receiving/consuming callback for our parallel txrx websocket.
        '''

        # For self.connect_parallel_txrx
        self._data_produce: TxRxProcessor = None
        '''
        Data sending/producing callback for our parallel txrx websocket.
        '''

        self.debug(f"host: {str(type(self._host))}({self._host}), "
                   f"port: {str(type(self._port))}({self._port}), "
                   f"secure: {str(type(secure))}({secure}), "
                   f"uri: {str(type(self.uri))}({self.uri})")

        # Configure logger for websockets.
        self._init_websocket_logging()

    # -------------------------------------------------------------------------
    # Debug
    # -------------------------------------------------------------------------

    def _init_websocket_logging(self):
        '''
        Initializes websockets lib's logger to be at same logging level as
        veredi root logger.
        '''
        # See just above this anchor for how their docs say to do it:
        #   https://websockets.readthedocs.io/en/stable/api.html#websockets.server.unix_serve
        # But we'll do it like we do our logs.
        level = log.Level.WARNING  # log.get_level()
        log.init_logger('websockets.server',
                        level=level)

    def debug(self,
              msg: str,
              *args: Any,
              **kwargs: Any) -> None:
        '''
        Debug logs go through our callback if we have it. Otherwise just use
        log.debug.
        '''
        kwargs = log.incr_stack_level(kwargs)
        call = self._debug_fn if self._debug_fn else log.debug
        call(msg, *args, **kwargs)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def host(self) -> str:
        '''
        Returns hostname
        '''
        return self._host

    @property
    def path(self) -> str:
        '''
        Returns path or an empty string if path is falsy.
        '''
        return self._path or ''

    @path.setter
    def path(self, value: str) -> None:
        '''
        Sets self._path, clears URI so it rebuilds if needed.
        '''
        self._path = value
        self._uri = None

    @property
    def path_rooted(self) -> str:
        '''
        Returns `self.path` with prefixed '/'.
        '''
        return self.PATH_ROOT + (self._path or '')

    @property
    def port(self) -> str:
        '''
        Returns port number
        '''
        return self._port

    @property
    def uri(self) -> str:
        '''
        Builds and returns uri from host, port, etc.
        Caches URI for next get.
        '''
        if self._uri:
            return self._uri

        port_str = ''
        if self._port and 0 < self._port < 65535:
            port_str = self.PORT_FMT.format(port=str(self._port))

        path_str = ''
        if self._path:
            path_str = self.PATH_FMT.format(path=str(self._path))

        self._uri = self.URI_FMT.format(scheme=(self.SCHEME_WS_SECURE
                                                if self._secure else
                                                self.SCHEME_WS_STD),
                                        host=self._host,
                                        port=port_str,
                                        path=path_str)

        return self._uri

    # -------------------------------------------------------------------------
    # General Functions
    # -------------------------------------------------------------------------

    def close(self) -> None:
        '''
        Doesn't really do anything!

        Only sets our close event flag.
        '''
        self._close.set()

    async def _a_wait_close(self) -> None:
        '''
        A future that just waits for our close flag or
        websockets.WebSocketServer's close future to be set.

        Can be used in a 'loop forever' context to die when instructed.
        '''
        while True:
            if self._close.is_set():
                break
            # Await something so other async tasks can run? IDK.
            await asyncio.sleep(0.1)

        # Shutdown has been signaled to us somehow, but we're just some minion
        # so we only need to put ourselves in order.
        if self._socket:
            await self._socket.close()

        self._close.set()

    # -------------------------------------------------------------------------
    # Packet Building
    # -------------------------------------------------------------------------

    def encode(self, msg: Message, context: MediatorContext) -> str:
        '''
        Encodes msg as a structured string using our codec.
        '''
        stream = self._codec.encode(msg, context)
        value = stream.getvalue()
        stream.close()
        return value

    def decode(self, recvd: str, context: MediatorContext) -> Message:
        '''
        Decodes received string using our codec.
        '''
        stream = StringIO(recvd)
        try:
            value = self._codec.decode(recvd, context)
        finally:
            stream.close()
        msg = Message.decode(value)
        return msg

    # -------------------------------------------------------------------------
    # Messaging Functions
    # -------------------------------------------------------------------------

    async def ping(self, msg: Message, context: MediatorContext) -> float:
        '''
        Send out a ping, wait for pong (response) back. Returns the time it
        took in fractional seconds.
        '''
        if not self._socket:
            log.error(f"Cannot ping; no socket connection: {self._socket}")
            return

        if msg.type != MsgType.PING:
            error = ValueError("Requested ping of non-ping message.", msg)
            raise log.exception(error,
                                None,
                                f"Requested ping of non-ping message: {msg}")

        timer = MonotonicTimer()  # Timer starts timing on creation.

        # Run our actual ping.
        self.debug('ping pinging...')
        pong = await self._socket.ping()
        self.debug('ping ponging...')
        await pong
        self.debug('ping ponged.')

        # Return the ping time.
        self.debug('ping: {}', timer.elapsed_str)
        return timer.elapsed

    # -------------------------------------------------------------------------
    # Produce / Consume Coroutines
    # -------------------------------------------------------------------------

    def _ppc_done_handle(self,
                         fut: asyncio.Future) -> None:
        '''
        Called when a producer/consumer Future is done. Will get result and
        ignore unless it's an exception that makes it past the ignored filter.
        '''
        try:
            # I don't currently care about the actual return, just if it raises
            # an exception.
            fut.result()

        except (websockets.ConnectionClosedOK,
                asyncio.CancelledError):
            # The good kind of connection closed.
            # The 'cancelled on purpose' kind of cancelled.
            pass

        except (websockets.ConnectionClosedError,
                websockets.ConnectionClosed) as error:
            # The error kind and the... parent class of Error and Ok, maybe?
            # TODO [2020-08-01]: Get UserId for logging.
            log.exception(error,
                          WebSocketError,
                          f"Connection for user 'TODO' closed due to: {error}")
            # TODO [2020-08-01]: (re)raise this?

        except asyncio.InvalidStateError as error:
            # This shouldn't be raised, but I want to check for it anyways
            # since this exception is what this function should be fixing.
            #
            # Was raised when a Future wasn't done but was asked for
            # exception()/result().

            # This trace might not work... Because Async.
            import traceback
            trace = traceback.format_exc()
            log.exception(error,
                          WebSocketError,
                          "A Future had InvalidStateError as its exception?!"
                          f"{error}\n{trace}")

    async def _ppc_consume(self,
                           websocket: websockets.WebSocketCommonProtocol,
                           context:   MessageContext
                           ) -> None:
        '''
        Receives a message from the websocket and sends it on to the
        consume handler.

        Blocking.
        '''
        self.debug(f"Consuming messages in context: {context}...")
        async for raw in websocket:
            self.debug(f"{self.SHORT_NAME}: <--  : "
                       f" raw: {raw}")
            recv = self.decode(raw, self._med_make_context())
            self.debug(f"{self.SHORT_NAME}: <--  : "
                       f"recv: {recv}")

            # Actually process the data we're consuming.
            immediate_reply = await self._data_consume(recv, self.path_rooted)

            # And immediately reply if needed (i.e. ack).
            if immediate_reply:
                self.debug(f"{self.SHORT_NAME}:  -->: "
                           f"reply-msg: {immediate_reply}")
                send = self.encode(immediate_reply, self._med_make_context())
                self.debug(f"{self.SHORT_NAME}:  -->: "
                           f"reply-raw: {send}")
                await websocket.send(send)

    async def _ppc_produce(self,
                           websocket: websockets.WebSocketCommonProtocol,
                           context:   MessageContext
                           ) -> None:
        '''
        Looks for a message from the producer handler (the server) to send to
        this specific client.

        Blocking.
        '''
        try:
            # A ConnectionClosed exception of some type will knock us out of
            # this eternal loop.
            self.debug(f"Producing messages in context {context}...")
            while True:
                message = await self._data_produce()

                # Only send out to socket if actually produced anything.
                if not message:
                    self.debug("No result send; done.")
                    return

                self.debug(f"{self.SHORT_NAME}:  -->: send: {message}")
                send = self.encode(message, self._med_make_context())
                self.debug(f"{self.SHORT_NAME}:  -->: raw: {send}")
                await websocket.send(send)

        except websockets.ConnectionClosedOK:
            # The good kind of connection closed.
            pass

        except (websockets.ConnectionClosedError,
                websockets.ConnectionClosed) as error:
            # Bad kind, indifferent kind (base class maybe?).

            # TODO [2020-08-01]: Get UserId for logging.
            log.exception(error,
                          WebSocketError,
                          f"Connection on client 'TODO' closed due to: {error}")
            # TODO [2020-08-01]: (re)raise this?
