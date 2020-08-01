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
import websockets
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

from ..message import Message, MsgType
from ..client                    import MediatorClient
from .base                       import VebSocket
from ..context                   import MediatorClientContext


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
                 codec:   BaseCodec,
                 host:    str,
                 path:    Optional[str] = None,
                 port:    Optional[int] = None,
                 secure:  bool          = True,
                 close:   asyncio.Event = None) -> None:
        super().__init__(codec, host, path, port, secure)
        log.debug(f"created client socket: {self.uri}")

    # -------------------------------------------------------------------------
    # Our Client Functions
    # -------------------------------------------------------------------------

    async def hello(self) -> None:
        '''
        Send a hello and await a response.
        '''
        log.debug("Hello?")
        print("\n\nHello?")

        # TODO [2020-08-01]: Finish hello?


    # TODO [2020-07-22]: take `data_send` param. Should it be string
    # (encoded already) or should we be the one with the codec?
    # I /think/ str, but not decided...
    async def message(self, data_send: Mapping[str, str]) -> None:
        '''
        Send data and await a response.
        '''
        log.debug("no message. >:(")
        # # We (or rather base class VebSocket) are a context manager for
        # # websockets, so:
        # async with self:
        #     data_send = '{"some_test_data": "test client send"}'

        #     log.debug(f"  -->: {data_send}")
        #     await self.send(data_send)

        #     data_recv = await self.receive()
        #     log.debug(f"<--  : {data_recv}")

        #     # TODO: Return data.


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

        self._server_socket:

    # -------------------------------------------------------------------------
    # Mediator API
    # -------------------------------------------------------------------------

    def make_context(self) -> MediatorClientContext:
        '''
        Make a context with our context data, our codec's, etc.
        '''
        ctx = MediatorClientContext(self.dotted)
        ctx.sub['type'] = 'websocket.client'
        ctx.sub['codec'] = self._codec.make_context_data()
        return ctx

    def start(self) -> None:
        '''
        Start our socket listening.
        '''
        # Kick it off into asyncio's hands.
        try:
            asyncio.run(self._a_main(self._shutdown_watcher(),
                                     # self._connect(),
                                     self._game_watcher()))
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

        # # Tell our websocket server to finish up.
        # log.debug("Tell our WebSocket to stop.")
        # self._socket.close()

        # # Tell ourselves to stop.
        # log.debug("Tell ourselves to stop.")
        # # ...nothing I guess?

    # -------------------------------------------------------------------------
    # WebSocket Functions
    # -------------------------------------------------------------------------

    def _server_conn(self, path: Optional[str] = None) -> VebSocketClient:
        '''
        Get a new WebSocket connection to our server.
        '''
        # TODO: an async Event to watch for shutdown?
        socket = VebSocketClient(self._codec,
                                 self._host,
                                 path,
                                 self._port,
                                 self._ssl)
        return socket

    async def _hello(self):
        '''
        Connect to the server just to say hello.
        '''
        log.debug("Client._connect: Hello to server...")
        self._server_socket = await self._server_conn()

.hello()
        log.debug("Client._connect: Done helloing.")

    async def _game_watcher(self):
        '''
        Loop waiting for messages from our multiprocessing.connection to
        communicate about with the MediatorServer.
        '''
        while True:
            # Die if requested.
            if self._shutdown:
                break

            # Check for something in connection to send; don't block.
            if not self._game.poll():
                await asyncio.sleep(0.1)
                continue

            log.debug("client._game_watcher has message.")
            # Have something to send; receive it from game connection so
            # we can send it.
            msg = self._game.recv()
            log.debug(f"client._game_watcher: recvd for sending: {msg}")

            # ---
            # Send Handlers by MsgType
            # ---
            if msg.type == MsgType.PING:
                log.debug("client._game_watcher: pinging...")
                reply = await self._ping(msg)
                log.debug(f"client._game_watcher: ping'd: {reply}")
                self._game.send(reply)

            elif msg.type == MsgType.ECHO:
                log.debug("client._game_watcher: echoing...")
                reply = await self._echo(msg)
                log.debug(f"client._game_watcher: echo'd: {reply}")
                self._game.send(reply)

            elif msg.type == MsgType.TEXT:
                log.debug("client._game_watcher: texting...")
                reply = await self._text(msg)
                log.debug(f"client._game_watcher: text'd: {reply}")
                self._game.send(reply)

            else:
                log.error(f"Unhandled message type {msg.type} for "
                          f"message: {msg}. Ignoring.")

    async def _ping(self, msg: Message) -> Message:
        '''
        Ping the server, return a Message of the monotonic time ping took.
        Returns Message with values:
          id, type - copied from input `msg`
          message - float elapsed monotonic time
        '''
        log.debug("client._ping: start...")
        # elapsed = await self._server_conn().ping()
        async with self._server_conn('ping') as conn:
            log.debug("client._ping: connected...")
            elapsed = await conn.ping(msg, self.make_context())
            log.debug(f"client._ping: pinged: {elapsed}")
        reply = Message(msg.id, msg.type, elapsed)
        return reply

    async def _echo(self, msg: Message) -> Message:
        '''
        Send echo message to server, returns reply.
        '''
        async with self._server_conn() as conn:
            reply = await conn.echo(msg, self.make_context())
        return reply

    async def _text(self, msg: Message) -> Message:
        '''
        Send text message to server, returns reply.
        '''
        async with self._server_conn() as conn:
            reply = await conn.text(msg, self.make_context())
        return reply
