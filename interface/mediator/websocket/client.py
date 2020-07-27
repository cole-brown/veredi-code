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
from veredi.logger                      import log
from veredi.data.exceptions                   import ConfigError
from veredi.data.config.config    import Configuration
from veredi.data.codec.base import BaseCodec
from veredi.data.config.registry import register

from ..client import MediatorClient
from .base import VebSocket


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

            await self.send(data_send)
            log.warning(f"  -->: {data_send}")

            data_recv = await self.receive()
            log.warning(f"<--  : {data_recv}")


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
                                 self._a_test(),
                                 self._connect()))

        # rtt = self.ping()
        # log.warning("ping round trip time(ish):", rtt)
        # self._aio.run_forever()

    # -------------------------------------------------------------------------
    # Asyncio / Multiprocessing Functions
    # -------------------------------------------------------------------------

    async def _a_main(self, *aws: Awaitable) -> Iterable[Any]:
        '''
        Runs client async tasks/futures concurrently, returns the aggregate
        list of return values for those tasks/futures.
        '''
        print(f"\n\nclient._a_main: {repr(aws)}\n\n")
        ret_vals = await asyncio.gather(*aws)
        print(f"\n\nclient ret_vals: {ret_vals}\n\n")

        # self._aio.run_until_complete()
        # self._aio.run_until_complete()
        # self._aio.run_forever()
        return ret_vals

    async def _a_test(self) -> None:
        await asyncio.sleep(0.5)
        print("\n\n !!!!!!!!!! HELLO THERE CLIENT !!!!!!!!!! \n\n")

    async def _shutdown_watcher(self) -> None:
        '''
        Watches `self._shutdown_flag`. Will call stop() on our asyncio loop
        when the shutdown flag is set.
        '''
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

    def ping(self) -> float:
        '''
        Ping the server, return the monotonic time ping took.
        '''
        return self._aio.run_until_complete(
            self._socket.ping())

    async def _connect(self):
        '''
        Read from client, send reply, close connection.
        '''
        await self._socket.message("ignored string")
        log.warning("Client._connect: Done awaiting conn message.")
