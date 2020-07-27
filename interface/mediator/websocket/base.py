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

# TODO [2020-07-26]: Delete unused functions in websockets/mediators code.


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
                 secure: Union[str, bool] = True,
                 close:  asyncio.Event    = None) -> None:
        self._codec:  BaseCodec        = codec
        self._host:   str              = host
        self._port:   int              = port
        self._secure: Union[str, bool] = secure
        self._uri:    Optional[str]    = None

        self._connection: websockets.connect = None
        self._socket:     websockets.WebSocketClientProtocol = None
        self._close:      asyncio.Event = asyncio.Event()

        log.debug(f"host: {str(type(self._host))}({self._host}), "
                  f"port: {str(type(self._port))}({self._port}), "
                  f"secure: {str(type(secure))}({secure}), "
                  f"uri: {str(type(self.uri))}({self.uri})")

        # TODO [2020-07-25]: Configure logger for websockets.
        # See just above this anchor:
        #   https://websockets.readthedocs.io/en/stable/api.html#websockets.server.unix_serve

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
        if self._port and 0 < self._port < 65535:
            port_str = self.PORT_FMT.format(port=str(self._port))

        self._uri = self.URI_FMT.format(scheme=(self.SCHEME_WS_SECURE
                                                if self._secure else
                                                self.SCHEME_WS_STD),
                                        host=self._host,
                                        port=port_str)

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
            self._socket.close()
        # if self._connection:
        #     self._connection.???() = ???
        #     self._connection. = ???

        self._close.set()


    # -------------------------------------------------------------------------
    # Asyncio 'with' Magic
    # -------------------------------------------------------------------------

    async def __aenter__(self) -> 'VebSocket':
        self._connection = websockets.connect(self.uri)
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
