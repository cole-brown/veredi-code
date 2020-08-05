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
from typing import Optional, Union, Any, Callable


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
from ..context                   import MediatorContext


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


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

    def __init__(self,
                 codec:    BaseCodec,
                 host:     str,
                 path:     Optional[str]              = None,
                 port:     Optional[int]              = None,
                 secure:   Optional[Union[str, bool]] = True,
                 debug_fn: Optional[Callable]         = None) -> None:

        self._codec:    BaseCodec          = codec
        self._host:     str                = host
        self._path:     str                = path
        self._port:     int                = port
        self._secure:   Union[str, bool]   = secure
        self._uri:      Optional[str]      = None
        self._debug_fn: Optional[Callable] = debug_fn

        self._socket: websockets.WebSocketClientProtocol = None
        self._close:      asyncio.Event = asyncio.Event()

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

    async def echo(self, msg: Message, context: MediatorContext) -> Message:
        '''
        Send msg as echo, returns reply.
        '''
        if msg.type != MsgType.ECHO:
            error = ValueError("Requested echo of non-echo message.", msg)
            raise log.exception(error,
                                None,
                                f"Requested echo of non-echo message: {msg}")
        self.path = msg.path

        data = self.encode(msg, context)
        recvd = None
        async with websockets.connect(self.uri) as conn:
            await conn.send(data)
            recvd = await conn.recv()

        reply = self.decode(recvd, context)
        return reply

    async def text(self, msg: Message, context: MediatorContext) -> Message:
        '''
        Send msg as text, returns reply.
        '''
        if msg.type != MsgType.TEXT:
            error = ValueError("Requested text send of non-text message.", msg)
            raise log.exception(
                error,
                None,
                f"Requested text send of non-text message: {msg}")
        self.path = msg.path

        data = self.encode(msg, context)
        recvd = None
        async with websockets.connect(self.uri) as conn:
            await conn.send(data)
            recvd = await conn.recv()

        reply = self.decode(recvd, context)
        return reply
