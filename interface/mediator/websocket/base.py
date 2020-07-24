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
from typing import Optional, Union, Any, Awaitable


# ---
# Python Imports
# ---
import websockets
import websockets.client
import asyncio

# ---
# Veredi Imports
# ---
from veredi.logger          import log
from veredi.data.codec.base import BaseCodec
from veredi.time.timer      import MonotonicTimer


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
    URI_FMT = '{scheme}://{host}{port}'
    PORT_FMT = ':{port}'

    def __init__(self,
                 codec:  BaseCodec,
                 host:   str,
                 port:   Optional[int]    = None,
                 secure: Union[str, bool] = True) -> None:
        self._codec:  BaseCodec        = codec
        self._host:   str              = host
        self._port:   int              = port
        self._secure: Union[str, bool] = secure
        self._uri:    Optional[str]    = None

        self._aio:        asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self._connection: websockets.client.WebSocketClientProtocol = None
        self._socket:     Awaitable = None

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def host(self) -> str:
        '''
        hostname
        '''
        return self._host

    @property
    def port(self) -> str:
        '''
        port number
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
        if self._port and 0 > self._port > 65535:
            port_str = self.PORT_FMT.format(port=str(self._port))
            self._uri = self.URI_FMT.format(scheme=(self.SCHEME_WS_SECURE
                                                    if self._secure else
                                                    self.SCHEME_WS_STD),
                                            host=self._host,
                                            port=port_str)
        return self._host

    # -------------------------------------------------------------------------
    # Asyncio 'with' Magic
    # -------------------------------------------------------------------------

    async def __aenter__(self) -> 'VebSocket':
        self._connection = websockets.connect(self._uri)
        self._socket = await self._connection.__aenter__()
        return self

    async def __aexit__(self, *args, **kwargs) -> None:
        await self._connection.__aexit__(*args, **kwargs)

    # -------------------------------------------------------------------------
    # Basic Send/Recv Functions
    # -------------------------------------------------------------------------

    async def send(self, message) -> None:
        # TODO [2020-07-22]: Convert thing to json str
        await self._socket.send(message)

    async def receive(self) -> Any:
        # TODO [2020-07-22]: Convert thing from json str
        return await self._socket.recv()

    # -------------------------------------------------------------------------
    # Ping / Testing
    # -------------------------------------------------------------------------
    async def ping(self) -> float:
        '''
        Send out a ping, wait for pong (response) back. Returns the time it
        took in fractional seconds.
        '''
        timer = MonotonicTimer()  # Timer starts timing on creation.

        # Run our actual ping.
        pong = await self._socket.ping()
        await pong

        # Return the ping time.
        if log.will_output(log.Level.DEBUG):
            log.debug('ping: {}', timer.elapsed_str)
        return timer.elapsed()
