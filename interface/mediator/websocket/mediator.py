# coding: utf-8

'''
Interface for WebSocket Mediation Implementations (Client and Server).
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (Optional, Union, NewType,
                    Callable, Dict, Tuple, Literal)

from abc import abstractmethod
import asyncio
import websockets
import multiprocessing
import multiprocessing.connection
import re

from veredi.logger             import log
from veredi.base               import dotted
from veredi.debug.const        import DebugFlag
from veredi.data               import background
from veredi.data.codec.base    import BaseCodec
from veredi.data.config.config import Configuration

from ..mediator                import Mediator
from ..context                 import (MessageContext,
                                       MediatorContext,
                                       UserConnToken)
from ..message                 import Message, MsgType
from .base                     import VebSocket


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
            MsgType.IGNORE:      (self._htx_root,    self._hrx_root),
            MsgType.PING:        (self._htx_ping,    self._hrx_ping),
            MsgType.ECHO:        (self._htx_echo,    self._hrx_echo),
            MsgType.ECHO_ECHO:   (self._htx_echo,    self._hrx_echo),
            MsgType.ACK_ID:      (self._htx_ack,     self._hrx_ack),
            MsgType.TEXT:        (self._htx_text,    self._hrx_text),
            MsgType.ENCODED:     (self._htx_encoded, self._hrx_encoded),
            MsgType.CODEC:       (self._htx_codec,   self._hrx_codec),
            MsgType.LOGGING:     (self._htx_logging, self._hrx_logging),
            MsgType.CONNECT:     (self._htx_connect, self._hrx_connect),
            MsgType.ACK_CONNECT: (self._htx_connect, self._hrx_connect),
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
                           context:  Optional[MediatorContext],
                           send_ack: Optional[bool] = True,
                           log_type: Optional[str]  = 'generic') -> Message:
        '''
        Handle receiving a message with generic/unknown payload.
        '''
        # Receive from server; put into rx_queue.
        #
        # Game will get it eventually and deal with it. We may get a reply to
        # send at some point but that's irrelevant here.
        ctx = self.make_msg_context(msg.msg_id)
        self.debug(f"received '{log_type}' msg; queuing: "
                   f"msg: {msg}, ctx: {ctx}")
        await self._med_to_game_put(msg, ctx)

        if send_ack:
            send = Message(msg.msg_id, MsgType.ACK_ID,
                           payload=ctx.id,
                           user_id=msg.user_id,
                           user_key=msg.user_key)
            send = await self._handle_reply(send, context, None)
            self.debug(f"sending '{log_type}' ack: {send}")
            log.critical(f"{self._name} got '{log_type}': "
                         "{msg}; sending ack: {send}")
            return send

        return None

    # -------------------------------------------------------------------------
    # TX / RX Handlers
    # -------------------------------------------------------------------------

    async def _hook_produce(self,
                            msg:  Optional[Message],
                            conn: UserConnToken
                            ) -> Optional[Message]:
        '''
        Hook that gets called right before `_handle_produce` returns a result.
        Can fiddle with the result, return it (or nothing or something entirely
        different)...
        '''
        return msg

    async def _hook_consume(self,
                            msg:  Optional[Message],
                            conn: UserConnToken
                            ) -> Optional[Message]:
        '''
        Hook that gets called right before `_handle_consume` returns a result.
        Can fiddle with the result, return it (or nothing or something entirely
        different)...
        '''
        return msg

    async def _handle_reply(self,
                            msg:       Optional[Message],
                            context:   Optional[MediatorContext],
                            conn:      UserConnToken
                            ) -> Optional[Message]:
        '''
        Reply helper for hooks and such before handing off an
        immediate reply.
        '''
        return msg

    # TODO [2020-08-12]: Type hinting double check of all the mediator code.

    async def _handle_produce_get_msg(
            self,
            conn: UserConnToken
    ) -> Tuple[Union[Message,        None, Literal[False]],
               Union[MessageContext, None, Literal[False]]]:
        '''
        Looks for a message to take from produce buffer(s) and return for
        sending.

        Returns:
          - (False, False) if it found nothing to produce/send.
          - (Message, MessageContext) if it found something to produce/send.
            - Could be Nones or MsgType.IGNORE.
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
                msg, ctx = self._game_pipe_get()
                # Just return; let caller deal with if these are none, ignore,
                # etc.
                return msg, ctx

            except EOFError as error:
                log.exception(error,
                              None,
                              "Failed getting from game pipe; "
                              "ignoring and continuing.")
                # EOFError gets raised if nothing left to receive or other end
                # closed. Wait til we know what that means to our game/mediator
                # pair before deciding to take (drastic?) action here...

        # Nothing in queues. Sleep a bit then return.
        await self._sleep()
        return False, False

    async def _handle_produce(self,
                              conn: UserConnToken
                              ) -> Optional[Message]:
        '''
        Loop waiting for messages from our multiprocessing.connection to
        communicate about with the mediator on the other end.
        '''
        while True:
            # Die if requested.
            if self.any_shutdown():
                break

            # Check for something in connection to send.
            msg, ctx = await self._handle_produce_get_msg(conn)
            # Checks for actually having a message below...

            # Don't send nothing, please.
            if msg is False and ctx is False:
                # Ignore. Default return from _handle_produce_get_msg().
                await self._continuing()
                continue
            if not msg or msg.type == MsgType.IGNORE:
                log.warning("Produced nothing for sending. "
                            f"Ignoring msg: {msg}, ctx: {ctx}")
                await self._continuing()
                continue

            # Have something to send!
            self.debug(f"Produced for sending: msg: {msg}, ctx: {ctx}")

            sender, _ = self._hp_paths_type.get(msg.type, None)
            if not sender:
                log.error("No handlers for msg type? "
                          f"Ignoring msg: {msg}, ctx: {ctx}")
                await self._continuing()
                continue

            self.debug("Producing result from send processor...")
            result = await sender(msg)

            # Only send out to socket if actually produced anything.
            if result:
                self.debug(f"Sending {result}...")
                result = await self._hook_produce(result, conn)
                return result

            else:
                self.debug("No result to send; done.")

            # reloop
            await self._continuing()

    async def _handle_consume(self,
                              msg:       Message,
                              path:      str,
                              context:   Optional[MediatorContext],
                              conn: UserConnToken
                              ) -> Optional[Message]:
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
        result = await processor(match, path, msg, context)
        result = await self._hook_consume(result, conn)
        return result

    # -------------------------------------------------------------------------
    # TX / RX Specific Handlers
    # -------------------------------------------------------------------------

    @abstractmethod
    async def _htx_connect(self,
                           msg: Message) -> Optional[Message]:
        '''
        Sends client their connected ack.
        '''
        raise NotImplementedError(
            "Client/Server must implement this separately.")

    @abstractmethod
    async def _hrx_connect(self,
                           match:   re.Match,
                           path:    str,
                           msg:     Message,
                           context: Optional[MediatorContext]
                           ) -> Optional[Message]:
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
        result = Message(msg.msg_id, msg.type,
                         payload=elapsed,
                         user_id=msg.user_id,
                         user_key=msg.user_key)
        self.debug(f"pinged: {elapsed}, result: {result}")
        await self._med_to_game_put(result,
                                    self.make_msg_context(result.msg_id))

        # No return; don't want to actually send anything.
        return None

    async def _hrx_ping(self,
                        match:   re.Match,
                        path:    str,
                        msg:     Message,
                        context: Optional[MediatorContext]
                        ) -> None:
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
                        match:   re.Match,
                        path:    str,
                        msg:     Message,
                        context: Optional[MediatorContext]
                        ) -> Optional[Message]:
        '''
        Handles receiving an echo.

        ...By just giving back what we got.
        ...Or returning the echo-back to the game.
        '''
        if msg.type == MsgType.ECHO:
            # Received echo from server to send back.
            self.debug("Got echo; returning it."
                       f"path: {path}, match: {match}, msg: {msg}...")
            reply = Message.echo(msg)
            return await self._handle_reply(reply, context, None)

        else:
            self.debug("Got echo-back; enqueuing."
                       f"path: {path}, match: {match}, msg: {msg}...")
            # Received echo-back from server; send to game.
            # TODO: add path into context
            await self._med_to_game_put(msg, self.make_msg_context(msg.msg_id))

        return None

    async def _htx_text(self,
                        msg: Message) -> Optional[Message]:
        '''
        Handle sending a message with text payload.
        '''
        return await self._htx_generic(msg, 'text')

    async def _hrx_text(self,
                        match:   re.Match,
                        path:    str,
                        msg:     Message,
                        context: Optional[MediatorContext]
                        ) -> Optional[Message]:
        '''
        Handle receiving a message with text payload.
        '''
        return await self._hrx_generic(match, path, msg, context,
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
                           match:   re.Match,
                           path:    str,
                           msg:     Message,
                           context: Optional[MediatorContext]
                           ) -> Optional[Message]:
        '''
        Handle receiving a message with an encoded payload.
        So basically treat like TEXT: do nothing to the message payload.
        '''
        return await self._hrx_generic(match, path, msg, context,
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
                         match:   re.Match,
                         path:    str,
                         msg:     Message,
                         context: Optional[MediatorContext]
                         ) -> Optional[Message]:
        '''
        Handle receiving a message with a payload we've been requested
        to 'codec plz'.

        So receive, then decode payload, then send on up.
        '''
        self.debug(f"received 'codec' {msg}...")

        # Decode first, then pass on to generic handler for the rest.
        #
        # TODO [2020-08-12]: This decode_ctx is just wrong. Should give it our
        # mediator context.
        decode_ctx = self._codec.make_context_data()
        payload = self._codec.decode(msg.payload, decode_ctx)
        recv = Message.codec(msg, payload)

        # recv is our processed msg, feed into _hrx_generic to process (ack,
        # put in rx queue, etc).
        return await self._hrx_generic(match, path, recv, context,
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
                           match:   re.Match,
                           path:    str,
                           msg:     Message,
                           context: Optional[MediatorContext]
                           ) -> Optional[Message]:
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
        self.debug("passing on to `_hrx_generic`...")
        return await self._hrx_generic(match, path, recv, context,
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
                       match:   re.Match,
                       path:    str,
                       msg:     Message,
                       context: Optional[MediatorContext]
                       ) -> Optional[Message]:
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
                        msg: Message) -> None:
        '''
        Handle a send request to root path ("/").
        '''
        raise NotImplementedError("TODO: THIS.")
        return None

    async def _hrx_root(self,
                        match:   re.Match,
                        path:    str,
                        msg:     Message,
                        context: Optional[MediatorContext]
                        ) -> None:
        '''
        Handle receiving a request to root path ("/").
        '''
        self.debug(f"Received: path: {path}, match: {match}, msg: {msg}")

        # Do I have someone else to give this to?
        _, receiver = self._hp_paths_type.get(msg.type, None)
        if receiver:
            self.debug(f"Forward to: {receiver}")
            return await receiver(match, path, msg, context)

        # else:
        # Ok, give up.
        log.warning("No handlers for msg; ignoring: "
                    f"path: {path}, match: {match}, msg: {msg}")
        return None
