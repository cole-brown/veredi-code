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
import threading


# ---
# Veredi Imports
# ---
from veredi.logger                      import log
from veredi.base.identity import MonotonicId
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

        log.debug(f"host: {str(type(self._host))}({self._host}), "
                  f"port: {str(type(self._port))}({self._port}), "
                  f"secure: {str(type(secure))}({secure})")

        # bad: self._server = websockets.serve(hello, "localhost", 8765)
        # works: self._server = websockets.serve(hello, "127.0.0.1", 8765)
        # bad: self._server = websockets.serve(hello, "::1", 8765)
        # TODO [2020-07-25]: Fix? Is it a docker thing? It'd be nice for
        # 'localhost' to work properly...
        # bad?: init-ing here? It gets in the wrong asyncio event loop somehow?
        # self._server = websockets.serve(self.handler, self._host, self._port)
        self._server = None

    # -------------------------------------------------------------------------
    # Our Server Functions
    # -------------------------------------------------------------------------

    # async def _a_serve(self) -> None:
    #     '''
    #     Server self._server until we have to die.
    #     '''
    #     # Proper ("graceful") shutdown. See:
    #     #    https://websockets.readthedocs.io/en/stable/deployment.html#graceful-shutdown
    #     # Not doing it exactly like that, but closeish?..
    #     async with self._server:
    #         await self._a_wait_close()

    async def serve(self, process_data_fn) -> None:
        '''
        Start our socket listening. Returns data from client to receive_fn.
        '''
        self._process_data = process_data_fn
        # self._server = websockets.serve(self.handler, self._host, self._port,
        #                                 loop=asyncio.get_event_loop())

        # # Created our WebSocket in init; just kick it off into asyncio's hands.
        # await self._a_serve()

        # This probably works.
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
            await self._process_data(data_recv, path)

        # TODO [2020-07-22]: How to get data back for returning to client? Do I
        # await on the self._process_data? Do I send data to mediator and wait
        # on an ID or something in a general reply stream?
        #
        # Do I hang on to this socket until I get a response from on high?

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
                                 self._a_test(),
                                 self._serve(),
                                 self._process()))

        # self._aio.run_until_complete(self._shutdown_watcher())

    # -------------------------------------------------------------------------
    # Asyncio / Multiprocessing Functions
    # -------------------------------------------------------------------------

    async def _a_main(self, *aws: Awaitable) -> Iterable[Any]:
        '''
        Runs client async tasks/futures concurrently, returns the aggregate
        list of return values for those tasks/futures.
        '''
        print(f"\n\nserver._a_main: {repr(aws)}\n\n")
        ret_vals = await asyncio.gather(*aws)
        print(f"\n\nserver ret_vals: {ret_vals}\n\n")

        # self._aio.run_until_complete()
        # self._aio.run_until_complete()
        # self._aio.run_forever()
        return ret_vals

    async def _a_test(self) -> None:
        await asyncio.sleep(1)
        print("\n\n !!!!!!!!!! HELLO THERE SERVER !!!!!!!!!! \n\n")

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
        # # ...nothing I guess?

    async def _process(self) -> None:
        '''
        Deals with sending data in our queue out to the game over our
        multiprocessing connection to it.
        '''
        # Don't block...
        while True:
            if self._rx_queue.empty():
                await asyncio.sleep(0.1)

            # Else get one thing and send it off this round.
            request = await self._rx_queue.get()
            log.warning(f"  -  : request: {request}")
            # TODO: something with the request...

    # -------------------------------------------------------------------------
    # WebSocket Asyncio Functions
    # -------------------------------------------------------------------------

    async def _serve(self):
        '''
        Read from client, send reply, close connection.
        '''
        await self._listener.serve(self._handle)
        log.warning("Server._serve: Done.")

    async def _handle(self, data: Mapping[str, str], path: str) -> None:
        '''
        TODO: better docstr
        '''
        qid = self._rx_qid.next()
        log.warning(f"  x  : data: {data}")
        log.warning(f"  x  : path: {path}")
        log.warning(f"  x  : id:   {qid}")
        await self._rx_queue.put((qid, path, data))

    # def ping(self) -> float:
    #     '''
    #     Ping the server, return the monotonic time ping took.
    #     '''
    #     return self._aio.run_until_complete(
    #         self._connection.ping())
