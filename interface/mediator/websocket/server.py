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
from typing import Optional, Any, Iterable, Awaitable, Mapping


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
from veredi.logger               import log
from veredi.base.identity        import MonotonicId
from veredi.data.config.config   import Configuration
from veredi.data.codec.base      import BaseCodec
from veredi.data.config.registry import register

from ..server                    import MediatorServer
from .base                       import VebSocket


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

        log.debug(f"host: {str(type(self._host))}({self._host}), "
                  f"port: {str(type(self._port))}({self._port}), "
                  f"secure: {str(type(secure))}({secure})")

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
        server = await websockets.serve(self.handler, self._host, self._port)
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

        # ---
        # Base Class
        # ---START
        # We rewrote it a lot so just pull bits we need from base's impl:

        # Shutdown has been signaled to us somehow, but we're just some minion
        # so we only need to put ourselves in order.
        if self._socket:
            self._socket.close()
        # ---END
        # Base Class
        # ---

        # Shutdown has been signaled to us somehow, but we're just some minion
        # so we only need to put ourselves in order.
        server.close()
        self._close.set()

    async def handler(self,
                      websocket: websockets.WebSocketServerProtocol,
                      path:      str) -> Awaitable:
        '''
        Handle receiving some data from a client over provided websocket.

        `websocket` is the websocket connection to the client.

        `path` is a url-like path. Only one I've gotten so far in tests
        is root ("/").
        '''
        log.debug(f"VebSocketServer.handler: websocket: {websocket}")
        log.debug(f"VebSocketServer.handler:      path: {path}")

        data_recv = await websocket.recv()
        log.debug(f"<--  : {data_recv}")

        # TODO: return await self._process_data(data_recv, path) ?
        result = None
        if self._process_data and callable(self._process_data):
            result = await self._process_data(data_recv, path)

        data_send = '{"field": "Hello. I got your data; thanks."}'
        log.debug(f"  -->: {data_send}")
        await websocket.send(data_send)


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
                                         self._host,
                                         self._port,
                                         self._ssl)
        self._rx_queue = asyncio.Queue()
        '''Queue for received data from clients.'''

        self._rx_qid = MonotonicId.generator()
        '''ID for queue items.'''

    # -------------------------------------------------------------------------
    # Mediator API
    # -------------------------------------------------------------------------

    def start(self) -> None:
        '''
        The server should start accepting connections, calls from the clients,
        etc. It should be fully armed and operational after this call.

        Kicks of async co-routine for listening for connections.
        '''
        # Kick it off into asyncio's hands.
        asyncio.run(self._a_main(self._shutdown_watcher(),
                                 self._serve(),
                                 self._process()))

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

    async def _process(self) -> None:
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
                request = self._rx_queue.get_nowait()
                if not request:
                    continue
            except asyncio.QueueEmpty:
                # get_nowait() got nothing. That's fine; go back to waiting.
                continue
            log.debug(f"  -  : request: {request}")
            # TODO: something with the request...

            self._rx_queue.task_done()

    # -------------------------------------------------------------------------
    # WebSocket Asyncio Functions
    # -------------------------------------------------------------------------

    async def _serve(self):
        '''
        Read from client, send reply, close connection.
        '''
        await self._listener.serve(self._handle)
        log.debug("Server._serve: Done.")

    async def _handle(self, data: Mapping[str, str], path: str) -> None:
        '''
        TODO: better docstr
        '''
        qid = self._rx_qid.next()

        log.debug(f"  x  : data: {data}")
        log.debug(f"  x  : path: {path}")
        log.debug(f"  x  : id:   {qid}")

        await self._rx_queue.put((qid, path, data))
        return qid
