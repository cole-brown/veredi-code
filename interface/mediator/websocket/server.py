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
from typing import Optional


# ---
# Python Imports
# ---
import asyncio
import websockets
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

from ..server import MediatorServer
from .base import VebSocket


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
                 codec:  BaseCodec,
                 host:   str,
                 port:   Optional[int] = None,
                 secure: bool          = True) -> None:
        super().__init__(codec, host, port, secure)

        self._server = websockets.serve(self.handler, self._host, self._port)

    # -------------------------------------------------------------------------
    # Our Server Functions
    # -------------------------------------------------------------------------

    def serve(self, process_data_fn) -> None:
        '''
        Start our socket listening. Returns data from client to receive_fn.
        '''
        self._process_data = process_data_fn

        # Created our socket in init; just kick it off into asyncio's hands.
        self._aio.run_until_complete(self.handler)
        self._aio.run_forever()

    async def handler(self, websocket, path) -> None:
        '''
        Handle receiving some data from a client over provided websocket.

        TODO: ...what is 'path'?
        '''
        log.warning(f"VebSocketServer.handler: websocket: {websocket}")
        log.warning(f"VebSocketServer.handler:      path: {path}")

        data_recv = await websocket.recv()
        log.warning(f"<--  : {data_recv}")

        if self._process_data and callable(self._process_data):
            self._process_data(data_recv)

        # TODO [2020-07-22]: How to get data back for returning to client? Do I
        # await on the self._process_data? Do I send data to mediator and wait
        # on an ID or something in a general reply stream?

        data_send = '{"field": "Hello. I got your data; thanks."}'
        await websocket.send(data_send)
        log.warning(f"  -->: {data_send}")


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
                 shutdown_flag: multiprocessing.Event = None) -> None:
        # Base class init first.
        super().__init__(config, conn)

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
                                         self._host,
                                         self._port,
                                         self._ssl)

    # -------------------------------------------------------------------------
    # Mediator API
    # -------------------------------------------------------------------------

    def start(self) -> None:
        '''
        The server should start accepting connections, calls from the clients,
        etc. It should be fully armed and operational after this call.

        Kicks of async co-routine for listening for connections.
        '''
        self._listener.serve()

    # -------------------------------------------------------------------------
    # WebSocket Asyncio Functions
    # -------------------------------------------------------------------------

    def _handler(self, websocket, path) -> None:
        '''
        Handle receiving some data from a client.

        Executed once per WebSocket connection. Connection is closed when this
        returns.
        '''
        data_recv = await websocket.recv()
        log.warning(f"<--  : {data_recv}")

        data_send = '{"field": "Hello. I got your data; thanks."}'
        await websocket.send(data_send)
        log.warning(f"  -->: {data_send}")

    def ping(self) -> float:
        '''
        Ping the server, return the monotonic time ping took.
        '''
        return self._aio.run_until_complete(
            self._connection.ping())
