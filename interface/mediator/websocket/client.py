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
from typing import Optional, Any, Mapping, Iterable, Awaitable


# ---
# Python Imports
# ---
import asyncio
import multiprocessing
import multiprocessing.connection


# ---
# Veredi Imports
# ---
from veredi.logger               import log
from veredi.data.config.config   import Configuration
from veredi.data.codec.base      import BaseCodec
from veredi.data.config.registry import register

from ..client                    import MediatorClient
from .base                       import VebSocket


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

    def __init__(self,
                 codec:  BaseCodec,
                 host:   str,
                 port:   Optional[int] = None,
                 secure: bool          = True) -> None:
        super().__init__(codec, host, port, secure)

    # -------------------------------------------------------------------------
    # Our Client Functions
    # -------------------------------------------------------------------------

    # TODO [2020-07-22]: take `data_send` param. Should it be string
    # (encoded already) or should we be the one with the codec?
    # I /think/ str, but not decided...
    async def message(self, data_send: Mapping[str, str]) -> None:
        '''
        Send data and await a response.
        '''
        # We (or rather base class VebSocket) are a context manager for
        # websockets, so:
        async with self:
            data_send = '{"some_test_data": "test client send"}'

            log.debug(f"  -->: {data_send}")
            await self.send(data_send)

            data_recv = await self.receive()
            log.debug(f"<--  : {data_recv}")

            # TODO: Return data.


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
                 shutdown_flag: multiprocessing.Event = None) -> None:
        # Base class init first.
        super().__init__(config, conn, shutdown_flag)

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

        self._socket: VebSocketClient = VebSocketClient(self._codec,
                                                        self._host,
                                                        self._port,
                                                        self._ssl)

    # -------------------------------------------------------------------------
    # Mediator API
    # -------------------------------------------------------------------------

    def start(self) -> None:
        '''
        Start our socket listening.
        '''
        # Kick it off into asyncio's hands.
        asyncio.run(self._a_main(self._shutdown_watcher(),
                                 self._connect()))

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
        # Parent's watcher is non-blocking so we can be simple about this:
        await super()._shutdown_watcher()

        # Tell our websocket server to finish up.
        log.debug("Tell our WebSocket to stop.")
        self._socket.close()

        # # Tell ourselves to stop.
        # log.debug("Tell ourselves to stop.")
        # # ...nothing I guess?

    # -------------------------------------------------------------------------
    # WebSocket Functions
    # -------------------------------------------------------------------------

    async def _connect(self):
        '''
        Read from client, send reply, close connection.
        '''
        await self._socket.message("ignored string")
        log.debug("Client._connect: Done awaiting conn message.")

    def ping(self) -> float:
        '''
        Ping the server, return the monotonic time ping took.
        '''
        return self._aio.run_until_complete(
            self._socket.ping())
