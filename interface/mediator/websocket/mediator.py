# coding: utf-8

'''
Interface for WebSocket Mediation Implementations (Client and Server).
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (Optional, Union, NewType,
                    Callable, Dict, Tuple)

from abc import abstractmethod
import asyncio
import websockets
import multiprocessing
import multiprocessing.connection
import re

from veredi.logger               import log
from veredi.base                 import dotted
from veredi.debug.const          import DebugFlag
from veredi.data                 import background
from veredi.data.codec.base      import BaseCodec
from veredi.data.config.config   import Configuration

from ..mediator import Mediator
from ..context  import MessageContext
from ..message  import Message, MsgType
from .base      import VebSocket


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

TxHandler = NewType(
    'TxHandler',
    Callable[[Message], Optional[Message]]
)

RxHandler = NewType(
    'RxHandler',
    Callable[[re.Match, str, Message], Optional[Message]]
)


# -----------------------------------------------------------------------------
# Game-to-Client Interface
# -----------------------------------------------------------------------------

class WebSocketMediator(Mediator):
    '''
    WebSockets Interface/Base (Abstract) Class for WebSockets Client/Server
    Implementations.
    '''

    def __init__(self,
                 config:        Configuration,
                 conn:          multiprocessing.connection.Connection,
                 shutdown_flag: multiprocessing.Event,
                 species:       str,
                 debug:         DebugFlag = None,
                 ) -> None:
        # Base class init first.
        super().__init__(config, conn, shutdown_flag, debug)

        self._name:  str              = species
        '''Should be 'client' or 'server'.'''

        # Grab our data from the config...
        self._codec: BaseCodec        = config.make(None,
                                                    self._name,
                                                    'mediator',
                                                    'codec')

        self._host:  str              = config.get(self._name,
                                                   'mediator',
                                                   'hostname')

        self._port:  int              = int(config.get(self._name,
                                                       'mediator',
                                                       'port'))

        self._ssl:   Union[str, bool] = config.get(self._name,
                                                   'mediator',
                                                   'ssl')
        '''
        Client can just True/False this if not using self-certs.
        Server has a bit more to go through to set up ssl after this.
        '''

        # ---
        # Our WebSocket... Sub-class has to create.
        # ---
        self._socket: VebSocket = None
        '''
        Our actual WebSocket class. For server, will be serving/listening on
        host/port URI. For client, will be connecting to host/port URI.
        '''

        # ---
        # Path Regexes to Functions
        # ---
        self._hp_paths_re: Dict[re.Pattern, Tuple[TxHandler, RxHandler]] = None
        '''
        "Handle Parallel" Paths (separate handlers for sending, receiving).
        The "I have a path; what do I do?" version.
        '''

        self._hp_paths_type: Dict[MsgType, Tuple[TxHandler, RxHandler]] = None
        '''
        "Handle Parallel" Paths (separate handlers for sending, receiving).
        The "I have a message; what do I do?" version.
        '''

        self._register_paths()

        self._init_background()

    # -------------------------------------------------------------------------
    # Background Context
    # -------------------------------------------------------------------------

    def _init_background(self):
        '''
        Insert the mediator context data into the background.
        '''
        bg_data, bg_owner = self._background
        background.mediator.set(self.dotted,
                                bg_data,
                                bg_owner)

    @property
    def _background(self):
        '''
        Get background data for init_background()/background.mediator.set().
        '''
        self._bg = {
            'dotted': self.dotted,
            'type': dotted.join('websocket', self._name),
            'codec': self._codec.dotted,
        }
        return self._bg, background.Ownership.SHARE

    # -----------------------------------------------------------------------
    # Abstract Methods
    # -----------------------------------------------------------------------

    # (See Mediator base class for its abstracts.)

    # -------------------------------------------------------------------------
    # TX / RX Helpers
    # -------------------------------------------------------------------------

    def _register_paths(self) -> None:
        '''
        Register TX/RX handlers.
        '''
        _c = re.compile
        _i = re.IGNORECASE
        self._hp_paths_re = {
            _c(r'^/$',        _i): (self._htx_root,    self._hrx_root),
            _c(r'^/ping$',    _i): (self._htx_ping,    self._hrx_ping),
            _c(r'^/echo$',    _i): (self._htx_echo,    self._hrx_echo),
            _c(r'^/text$',    _i): (self._htx_text,    self._hrx_text),
            _c(r'^/encoded$', _i): (self._htx_encoded, self._hrx_encoded),
            _c(r'^/codec$',   _i): (self._htx_codec,   self._hrx_codec),
            _c(r'^/logging$', _i): (self._htx_logging, self._hrx_logging),
            _c(r'^/connect$', _i): (self._htx_connect, self._hrx_connect),
        }
        '''
        "Handle Parallel" Paths (separate handlers for sending, receiving).
        The "I have a path; what do I do?" version.
        '''

        self._hp_paths_type = {
            MsgType.IGNORE:    (self._htx_root,    self._hrx_root),
            MsgType.PING:      (self._htx_ping,    self._hrx_ping),
            MsgType.ECHO:      (self._htx_echo,    self._hrx_echo),
            MsgType.ECHO_ECHO: (self._htx_echo,    self._hrx_echo),
            MsgType.ACK_ID:    (self._htx_ack,     self._hrx_ack),
            MsgType.TEXT:      (self._htx_text,    self._hrx_text),
            MsgType.ENCODED:   (self._htx_encoded, self._hrx_encoded),
            MsgType.CODEC:     (self._htx_codec,   self._hrx_codec),
            MsgType.LOGGING:   (self._htx_logging, self._hrx_logging),
            MsgType.CONNECT:   (self._htx_connect, self._hrx_connect),
        }
        '''
        "Handle Parallel" Paths (separate handlers for sending, receiving).
        The "I have a message; what do I do?" version.
        '''

    def _hrx_path_processor(self, path: str) -> Callable:
        '''
        Takes a path and returns:
          - None: Path is unknown.
          - A 2-tuple of:
            - The re.Match object for the path matching.
            - The rx handler for that path.
        '''
        for regex, func_tuple in self._hp_paths_re.items():
            match = regex.fullmatch(path)
            if match:
                return match, func_tuple[1]

        return None, None

    async def _htx_generic(self,
                           msg:      Message,
                           log_type: Optional[str] = 'generic') -> Message:
        '''
        Handle sending a message with a generic/unknown payload. By just
        returing `msg` as the thing to send.
        '''
        self.debug(f"sending '{log_type}' {msg}...")
        return msg

    async def _hrx_generic(self,
                           match:    're.Match',
                           path:     str,
                           msg:      Message,
                           send_ack: Optional[bool] = True,
                           log_type: Optional[str] = 'generic') -> Message:
        '''
        Handle receiving a message with generic/unknown payload.
        '''
        # Receive from server; put into rx_queue.
        #
        # Game will get it eventually and deal with it. We may get a reply to
        # send at some point but that's irrelevant here.
        ctx = self.make_msg_context(msg.id)
        self.debug(f"received '{log_type}' msg; queuing: "
                   f"msg: {msg}, ctx: {ctx}")
        await self._med_to_game_put(msg, ctx)

        if send_ack:
            send = Message(msg.id, MsgType.ACK_ID,
                           payload=ctx.id)
            self.debug(f"sending '{log_type}' ack: {send}")
            return send

        return None

    # -------------------------------------------------------------------------
    # TX / RX Handlers
    # -------------------------------------------------------------------------

    async def _hook_produce(self,
                            msg: Optional[Message]) -> Optional[Message]:
        '''
        Hook that gets called right before `_handle_produce` returns a result.
        Can fiddle with the result, return it (or nothing or something entirely
        different)...
        '''
        return msg

    async def _hook_consume(self,
                            msg: Optional[Message]) -> Optional[Message]:
        '''
        Hook that gets called right before `_handle_consume` returns a result.
        Can fiddle with the result, return it (or nothing or something entirely
        different)...
        '''
        return msg

    async def _handle_produce_get_msg(self):
        '''
        Looks for a message to take from produce buffer(s) and return for
        sending.
        '''
        # Give our lil' queue priority over game...
        if self._med_tx_has_data():
            try:
                msg, ctx = self._med_tx_get()
            except asyncio.QueueEmpty:
                # get_nowait() got nothing. That's fine; go on to check other
                # things.
                pass
            else:
                # Someone else check that this isn't None, plz.
                if msg.type == MsgType.IGNORE:
                    self.debug(f"send: ignoring IGNORE msg: {msg}")
                else:
                    self.debug(f"send: mediator message: {msg}")
                    return msg, ctx

        # Check for something in game connection to send; don't block.
        if self._game_has_data():
            try:
                msg, ctx = await self._game_pipe_get()
            except asyncio.QueueEmpty:
                # get_nowait() got nothing. That's fine; go on to check other
                # things.
                pass
            else:
                # Someone else check that this isn't None, plz.
                if msg.type == MsgType.IGNORE:
                    self.debug(f"send: ignoring IGNORE mediator msg: {msg}")
                else:
                    self.debug(f"send: game message: {msg}")
                    return msg, ctx

        # Nothing in queues. Sleep a bit then return.
        await asyncio.sleep(0.1)
        return None, None

    async def _handle_produce(self):
        '''
        Loop waiting for messages from our multiprocessing.connection to
        communicate about with the mediator on the other end.
        '''
        while True:
            # Die if requested.
            if self.any_shutdown():
                break

            # Check for something in connection to send.
            msg, ctx = await self._handle_produce_get_msg()
            # Checks for actually having a message below...

            # Have something to send!
            self.debug(f"produced for sending: msg: {msg}, ctx: {ctx}")

            # Don't send a None, please.
            if not msg:
                log.warning("No message for sending? "
                            f"Ignoring msg: {msg}, ctx: {ctx}")
                continue

            sender, _ = self._hp_paths_type.get(msg.type, None)
            if not sender:
                log.error("No handlers for msg type? "
                          f"Ignoring msg: {msg}, ctx: {ctx}")
                continue

            self.debug("Producing result from send processor...")
            result = await sender(msg)

            # Only send out to socket if actually produced anything.
            if result:
                self.debug(f"Sending {result}...")
                result = await self._hook_produce(result)
                return result

            else:
                self.debug("No result to send; done.")
                # reloop

    async def _handle_consume(self,
                              msg: Message,
                              path: str) -> Optional[Message]:
        '''
        Handles a `VebSocketServer.serve_parallel` consume data callback.
        '''
        self.debug(f"Consuming a message on path: {path}: {msg}")
        match, processor = self._hrx_path_processor(path)
        self.debug(f"match: {match}, processor: {processor}")
        if not processor:
            # TODO [2020-07-29]: Log info about client too.
            log.error("Tried to consume message for unhandled path: {}, {}",
                      msg, path)
            return None

        self.debug("Sending to path processor to consume...")
        result = await processor(match, path, msg)
        result = await self._hook_consume(result)
        return result

    # -------------------------------------------------------------------------
    # TX / RX Specific Handlers
    # -------------------------------------------------------------------------

    @abstractmethod
    async def _htx_connect(self,
                           msg: Message) -> Optional[Message]:
        '''
        Handle sending a message with text payload.
        '''
        raise NotImplementedError(
            "Client/Server must implement this separately.")

    @abstractmethod
    async def _hrx_connect(self,
                           match: re.Match,
                           path: str,
                           msg: Message) -> Optional[Message]:
        '''
        Handle receiving a message with text payload.
        '''
        raise NotImplementedError(
            "Client/Server must implement this separately.")

    async def _htx_ping(self,
                        msg: Message) -> None:
        '''
        Handle sending a ping?
        '''
        self.debug(f"ping triggered by: {msg}...")
        self.debug("start...")

        elapsed = await self._socket.ping(msg,
                                          self.make_med_context())
        result = Message(msg.id, msg.type, payload=elapsed)
        self.debug(f"pinged: {elapsed}, result: {result}")
        await self._med_to_game_put(result, self.make_msg_context(result.id))

        # No return; don't want to actually send anything.
        return None

    async def _hrx_ping(self,
                        match: re.Match,
                        path: str,
                        msg: Message) -> None:
        '''
        Handle receiving a ping. By doing nothing.
        '''
        self.debug("got ping; ignoring."
                   f"path: {path}, match: {match}, msg: {msg}...")
        return None

    async def _htx_echo(self,
                        msg: Message) -> Message:
        '''
        Handles sending an echo.
        '''
        return await self._htx_generic(msg, 'echo')

    async def _hrx_echo(self,
                        match: re.Match,
                        path: str,
                        msg: Message) -> Optional[Message]:
        '''
        Handles receiving an echo.

        ...By just giving back what we got.
        ...Or returning the echo-back to the game.
        '''
        if msg.type == MsgType.ECHO:
            # Received echo from server to send back.
            self.debug("Got echo; returning it."
                       f"path: {path}, match: {match}, msg: {msg}...")
            return Message.echo(msg)

        else:
            self.debug("Got echo-back; enqueuing."
                       f"path: {path}, match: {match}, msg: {msg}...")
            # Received echo-back from server; send to game.
            # TODO: add path into context
            await self._med_to_game_put(msg, self.make_msg_context(msg.id))

        return None

    async def _htx_text(self,
                        msg: Message) -> Optional[Message]:
        '''
        Handle sending a message with text payload.
        '''
        return await self._htx_generic(msg, 'text')

    async def _hrx_text(self,
                        match: re.Match,
                        path: str,
                        msg: Message) -> Optional[Message]:
        '''
        Handle receiving a message with text payload.
        '''
        return await self._hrx_generic(match, path, msg,
                                       send_ack=True,
                                       log_type='text')

    async def _htx_encoded(self,
                           msg: Message) -> Optional[Message]:
        '''
        Handle sending a message with an encoded payload.
        So basically treat like TEXT: do nothing to the message payload.
        '''
        return await self._htx_generic(msg, 'encoded')

    async def _hrx_encoded(self,
                           match: re.Match,
                           path: str,
                           msg: Message) -> Optional[Message]:
        '''
        Handle receiving a message with an encoded payload.
        So basically treat like TEXT: do nothing to the message payload.
        '''
        return await self._hrx_generic(match, path, msg,
                                       send_ack=True,
                                       log_type='encoded')

    async def _htx_codec(self,
                         msg: Message) -> Optional[Message]:
        '''
        Handle sending a message with a payload we've been requested
        to 'codec plz'.

        So encode payload, then send.
        '''
        encode_ctx = self._codec.make_context_data()
        payload = self._codec.encode(msg.payload, encode_ctx)
        send = Message.codec(msg, payload)
        return await self._htx_generic(send, 'codec')

    async def _hrx_codec(self,
                         match: re.Match,
                         path: str,
                         msg: Message) -> Optional[Message]:
        '''
        Handle receiving a message with a payload we've been requested
        to 'codec plz'.

        So receive, then decode payload, then send on up.
        '''
        self.debug(f"received 'codec' {msg}...")

        # Decode first, then pass on to generic handler for the rest.
        decode_ctx = self._codec.make_context_data()
        payload = self._codec.decode(msg.payload, decode_ctx)
        recv = Message.codec(msg, payload)

        # recv is our processed msg, feed into _hrx_generic to process (ack,
        # put in rx queue, etc).
        return await self._hrx_generic(match, path, recv,
                                       send_ack=True,
                                       log_type='codec')

    async def _htx_logging(self,
                           msg: Message) -> Optional[Message]:
        '''
        Handle sending a logging/debug-related message.

        This will encode payload, then send.
        '''
        self.debug(f"sending 'logging' {msg} via 'codec'...")
        return await self._htx_codec(msg)

    async def _hrx_logging(self,
                           match: re.Match,
                           path: str,
                           msg: Message) -> Optional[Message]:
        '''
        Handle receiving a logging/debug-related message.

        So receive, decode, and send on up to:
          - ourself
          - the game
        '''
        self.debug(f"receiving 'logging' {msg} via 'codec'...")

        # Decode first, then pass on to generic handler for the rest. Not using
        # _hrx_codec as I want to stuff into our _rx_med_queue in between...
        decode_ctx = self._logging.make_context_data()
        payload = self._logging.decode(msg.payload, decode_ctx)
        recv = Message.encoded(msg, payload)

        self.debug(f"received 'logging' {recv}.")
        self.debug("Queueing for self...")
        await self._rx_med_queue.put(msg)

        # recv is our processed msg, feed into _hrx_generic to process (ack,
        # put in rx queue, etc).
        self.debug("passing on to `_hrx_codec`...")
        return await self._hrx_generic(match, path, recv,
                                       send_ack=True,
                                       log_type='logging')

    async def _htx_ack(self,
                       msg: Message) -> Optional[Message]:
        '''
        Handle sending a message with an ACK_ID payload.
        '''
        log.warning("...Why is the TX handler for ACK involved?")
        return await self._htx_generic(msg, 'ack')

    async def _hrx_ack(self,
                       match: re.Match,
                       path: str,
                       msg: Message) -> Optional[Message]:
        '''
        Handle receiving a message with an ACK_ID payload.
        '''
        # Receive from server; put into rx_queue.
        #
        # Game will get it eventually and deal with it. We may get a reply to
        # send at some point but that's irrelevant here.
        ctx = MessageContext(self.dotted, msg.payload)
        self.debug("received text msg; queuing: "
                   f"msg: {msg}, ctx: {ctx}")
        await self._med_to_game_put(msg, ctx)

        # Don't ack the ack.
        return None

    async def _htx_root(self,
                        match: re.Match,
                        path: str,
                        msg: Message) -> None:
        '''
        Handle a send request to root path ("/").
        '''
        raise NotImplementedError("TODO: THIS.")
        return None

    async def _hrx_root(self,
                        match: re.Match,
                        path: str,
                        msg: Message) -> None:
        '''
        Handle receiving a request to root path ("/").
        '''
        self.debug(f"Received: path: {path}, match: {match}, msg: {msg}")

        # Do I have someone else to give this to?
        _, receiver = self._hp_paths_type.get(msg.type, None)
        if receiver:
            self.debug(f"Forward to: {receiver}")
            return await receiver(match, path, msg)

        # else:
        # Ok, give up.
        log.warning("No handlers for msg; ignoring: "
                    f"path: {path}, match: {match}, msg: {msg}")
        return None
