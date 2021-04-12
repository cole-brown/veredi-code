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
from typing import (Optional, Union, Any,
                    Callable, Dict, Set, Tuple, Literal)
from veredi.base.null import Null, Nullable, NullNoneOr

# ---
# Python Imports
# ---
import asyncio
import websockets
import multiprocessing
import multiprocessing.connection
import re


# ---
# Veredi Imports
# ---
from veredi.logs                 import log
from veredi.debug.const          import DebugFlag
from veredi.base.identity        import MonotonicId
from veredi.base.context         import VerediContext
from veredi.base.strings         import label
from veredi.data                 import background
from veredi.data.identity        import UserId, UserKey
from veredi.data.config.config   import Configuration
from veredi.data.serdes.base     import BaseSerdes
from veredi.data.codec           import Codec

from .mediator                   import WebSocketMediator
from .exceptions                 import WebSocketError
from .base                       import VebSocket, TxProcessor, RxProcessor
from ..const                     import MsgType
from ..message                   import Message, ConnectionMessage
from ..context                   import (MediatorServerContext,
                                         MessageContext,
                                         UserConnToken)
from ...user                     import BaseUser, UserConn
from ...output.envelope          import Envelope, Address
from ...output.event             import Recipient


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

    SHORT_NAME = 'base'
    ''' Should be 'client' or 'server', depending. '''

    def __init__(self,
                 serdes:         BaseSerdes,
                 codec:          Codec,
                 med_context_fn: Callable[[],
                                          MediatorServerContext],
                 msg_context_fn: Callable[[],
                                          MessageContext],
                 unregister_fn:  Callable[[UserConnToken],
                                          Optional[Message]],
                 host:           str,
                 path:           Optional[str]                         = None,
                 port:           Optional[int]                         = None,
                 secure:         Optional[Union[str, bool]]            = True,
                 debug_fn:       Optional[Callable]                    = None
                 ) -> None:
        super().__init__(serdes, codec,
                         med_context_fn, msg_context_fn,
                         host,
                         path     = path,
                         port     = port,
                         secure   = secure,
                         debug_fn = debug_fn)

        self._unregistered = unregister_fn

        self.debug(f"host: {str(type(self._host))}({self._host}), "
                   f"port: {str(type(self._port))}({self._port}), "
                   f"secure: {str(type(secure))}({secure})")

        self.debug(f"created {self.uri}...")

        # bad: self._server = websockets.serve(hello, "localhost", 8765)
        # bad: self._server = websockets.serve(hello, "::1", 8765)
        # works: self._server = websockets.serve(hello, "127.0.0.1", 8765)
        #   - but issues with things running in the 'wrong' asyncio event loop.
        # so... bad?: init-ing here?
        #   - It gets in the wrong asyncio event loop somehow.
        self._listener: websockets.WebSocketServer = None

        # We just know sockets. MediatorServer knows what user has what socket.
        self._sockets_open: Set[websockets.WebSocketServerProtocol] = set()

        self._paths_ignored: Set[re.Pattern] = set()

    # -------------------------------------------------------------------------
    # Serve
    # -------------------------------------------------------------------------

    async def serve_parallel(
            self,
            produce_fn: TxProcessor,
            consume_fn: RxProcessor
    ) -> None:
        '''
        Start WebSocket Server listening on `self._host` and `self._port`.
        Clients will be expected to connect somehow first - maybe with a
        friendly hello() - then the `consume_fn` callback will be used for
        receiving data from the client and the `produce_fn` callback will be
        used for sending data back to the client.

        We'll try to keep the connection to the client around for as long as we
        can; we guarentee nothing.
        '''
        self._data_produce = produce_fn
        self._data_consume = consume_fn

        # Create it here, then... don't await it. Let self._a_wait_close() wait
        # on both server and our close flag.
        self.debug(f"Starting server {self.uri}...")
        self._listener = await websockets.serve(self.handler_ppc,
                                                self._host,
                                                self._port)
        self.debug(f"Serving {self.uri}...")
        await self._a_wait_close(self._listener)

    # -------------------------------------------------------------------------
    # Helper Functions
    # -------------------------------------------------------------------------

    def ignore_path(self, path_re: re.Pattern, remove: bool = False) -> None:
        '''
        Add/remove an ignored path for client socket registration.

        `path_re.fullmatch` is used for making the match, so...
        '''
        if remove:
            self._paths_ignored.remove(path_re)
            return

        self._paths_ignored.add(path_re)

    def register_for_path(self, path: str) -> bool:
        '''
        Returns True if we should register the client socket who just connected
        to this path.

        Returns False if not (for e.g. PING, ECHO).
        '''
        # Check each of our ignores, return False for "Don't Register!" if we
        # match one.
        for regex in self._paths_ignored:
            match = regex.fullmatch(path)
            if match:
                return False

        # Ok; register them.
        return True

    def register(self,
                 websocket: websockets.WebSocketServerProtocol
                 ) -> None:
        '''
        Add this websocket to our collection of clients.
        '''
        self._sockets_open.add(websocket)

    async def unregister(self,
                         websocket: websockets.WebSocketServerProtocol,
                         close: bool = False
                         ) -> None:
        '''
        Remove this websocket from our collection of clients.

        Closes socket if `close` is True.
        '''
        self._sockets_open.remove(websocket)
        if self._unregistered:
            await self._unregistered(self.token(websocket))

        # Both 'ws.open' and 'ws.closed' are False during opening/closing
        # sequences so I guess check both?
        if close and websocket.open and not websocket.closed:
            # If this takes too long, adjust 'close_timeout' keyword arg of
            # WebSocketServerProtocol constructor.
            websocket.close()

    async def _a_wait_close(self,
                            listener: websockets.WebSocketServer) -> None:
        '''
        A future that just waits for our close flag or
        websockets.WebSocketServer's close future to be set.

        Can be used in a 'loop forever' context to die when instructed.
        '''
        while True:
            if (self._close.is_set()
                    or listener.closed_waiter.done()):
                break
            # Await something so other async tasks can run? IDK.
            await asyncio.sleep(0.1)

        # This is supposed to close connections with code 1001 ('going
        # away'), which is supposed to raise a ConnectionClosedOK exception
        # on the clients. If you forget to wait_closed() or get killed
        # early, you might send out 1006 instead ('connection closed
        # abnormally [internal]') which is ConnectionClosedError exception
        # on client.
        listener.close()
        await listener.wait_closed()

        # Make sure close flag is set. Could have triggered close by the other
        # flag check.
        self._close.set()

    # -------------------------------------------------------------------------
    # Two-Way Communication Handler
    # -------------------------------------------------------------------------
    #
    # Consumer and producer in parallel.

    async def handler_ppc(self,
                          websocket: websockets.WebSocketServerProtocol,
                          path:      str) -> None:
        '''
        Handles "parallel produce(tx)/consume(rx) on same websocket, keeping it
        around until client leaves or something.

        `websocket` is the websocket connection to the client.

        `path` is a url-like path. Only one used so far is root ("/").

        https://websockets.readthedocs.io/en/stable/intro.html#both
        '''
        self.debug("{}.handler_ppc: "
                   "websocket: {}, path: {}",
                   self.__class__.__name__,
                   websocket,
                   path)

        # Register client as connected.
        if self.register_for_path(path):
            self.debug("{}.handler_ppc: "
                       "websocket: {}: Registering user...",
                       self.__class__.__name__,
                       websocket)
            self.register(websocket)

        self.debug("{}.handler_ppc: "
                   "websocket: {}: Creating produce/consume handlers...",
                   self.__class__.__name__,
                   websocket)
        # Make both consume and produce handlers for this client. Run them in
        # parallel. The first one that finishes signifies an end to our
        # connection over this websocket.
        consume = asyncio.ensure_future(self._ppc_consume(
            websocket,
            self._msg_make_context(path)))
        consume.add_done_callback(self._ppc_done_handle)

        produce = asyncio.ensure_future(self._ppc_produce(
            websocket,
            self._msg_make_context(path)))
        produce.add_done_callback(self._ppc_done_handle)

        # Client has to do this, but we're already using _a_wait_closed() for
        # waiting on the socket listener so do not do this 'poison pill' on
        # server.
        # # And this one is just to exit when asked to close().
        # poison = asyncio.ensure_future(self._a_wait_closed())
        # poison.add_done_callback(self._ppc_done_handle)

        self.debug("{}.handler_ppc: "
                   "websocket: {}: "
                   "Running produce/consume for user on socket...",
                   self.__class__.__name__,
                   websocket)
        done, pending = await asyncio.wait(
            [produce, consume],
            return_when=asyncio.FIRST_COMPLETED)

        self.debug("{}.handler_ppc: "
                   "websocket: {}: "
                   "Done running produce/consume for user on socket. "
                   "Cleaning up pending tasks: done: {}, pending: {}",
                   self.__class__.__name__,
                   websocket,
                   done, pending)

        # Whoever didn't finish first gets the axe.
        for task in pending:
            task.cancel()

        self.debug("{}.handler_ppc: "
                   "websocket: {}: "
                   "Done running produce/consume for user on socket. "
                   "Unregistering websocket...",
                   self.__class__.__name__,
                   websocket)

        # And we need to forget this client.
        await self.unregister(websocket)

        self.debug("{}.handler_ppc: "
                   "websocket: {}: "
                   "Produce/Consume complete for user on socket. ",
                   self.__class__.__name__,
                   websocket)


# -----------------------------------------------------------------------------
# The "Registered Client(s) of the WebSocketServer" Bit
# -----------------------------------------------------------------------------

class ClientRegistry:
    '''
    Get at registered clients a variety of ways.
    '''

    def __init__(self, debug_fn: Callable) -> None:
        self._id:   Dict[UserId,        BaseUser] = {}
        '''
        UserId to User map.
        '''

        self._key:  Dict[UserKey,       BaseUser] = {}
        '''
        UserKey to User map.
        '''

        self._conn: Dict[UserConnToken, BaseUser] = {}
        '''
        UserConnToken to User map.
        '''

        self.debug: Callable = debug_fn
        '''
        Should be WebSocketServer.debug().
        '''

    # ------------------------------
    # Register / Unregister
    # ------------------------------

    def register(self,
                 user_id:  UserId,
                 user_key: Optional[UserKey],
                 conn:     UserConnToken) -> UserConn:
        '''
        Creates a User instance and indexes it by all the things we
        can get it by.
        '''
        log.debug(f"Register user: {user_id} {user_key} {conn}")

        if not user_id or not conn:
            msg = ("UserId and UserConnToken required to register a user! "
                   f"Got: id: {user_id}, key: {user_key}, conn: {conn}")
            raise log.exception(ValueError(msg, user_id, user_key, conn), msg)

        user = UserConn(user_id, user_key, conn,
                        debug=self.debug,
                        # Create a queue for the user.
                        tx_queue=asyncio.Queue())

        self._id[user_id] = user
        # TODO: make user_key required?
        if user_key:
            self._key[user_key] = user
        self._conn[conn] = user

        return user

    def unregister(self,
                   user_id:  NullNoneOr[UserId],
                   user_key: NullNoneOr[UserKey],
                   conn:     NullNoneOr[UserConnToken]) -> bool:
        '''
        Looks for client using any of the provided parameters - only need one
        to succeed. Unregisters client if found. Returns True for 'found &
        unregistered', False otherwise.
        '''
        # 0) Find client using whatever was provided. This relies on Null/None
        # being returned if client not found.
        client = self.get(user_id, user_key, conn)
        log.debug(f"Unregister user: {user_id} {user_key} {conn}")

        # Not registered, maybe?
        if not client:
            self.debug("Cannot unregister; user not found in ClientRegistry. "
                       "id: {}, key: {}, conn: {}",
                       user_id, user_key, conn)
            return False

        # Remove from our collections and return True.
        self._id.pop(client.id, None)
        self._key.pop(client.key, None)
        self._conn.pop(client.connection, None)
        return True

    # ------------------------------
    # Getters / Setters
    # ------------------------------

    def id(self, user: UserId) -> Nullable[UserConn]:
        '''
        Get by user's id.
        Returns Null() if it can't find client.
        '''
        return self._id.get(user, Null())

    def key(self, user: UserKey) -> Nullable[UserConn]:
        '''
        Get by user's key.
        Returns Null() if it can't find client.
        '''
        return self._key.get(user, Null())

    def connection(self, user: UserConnToken) -> Nullable[UserConn]:
        '''
        Get by user's connection token.
        Returns Null() if it can't find client.
        '''
        return self._conn.get(user, Null())

    def get(self,
            user_id:  UserId,
            user_key: Optional[UserKey],
            conn:     UserConnToken) -> Nullable[UserConn]:
        '''
        Get when you don't know what to use to get.
        Will return Null if nothing found.
        '''
        client = (self.id(user_id)
                  or self.key(user_key)
                  or self.connection(conn))
        return client

    # ------------------------------
    # User already exists?
    # ------------------------------

    def __contains__(self,
                     check: Union[UserId, UserKey, UserConnToken]) -> bool:
        '''
        Returns true if ClientRegistry contains a user with the `check` value.
        '''
        if isinstance(check, UserId):
            return check in self._id
        elif isinstance(check, UserKey):
            return check in self._key
        elif isinstance(check, int):  # UserConnToken
            return check in self._conn

        # Else how am I supposed to check that even?!
        msg = (f"Can't check if '{check}' is a registered user. "
               f"Unknown type: {type(check)}")
        raise log.exception(ValueError(msg, check), msg)


# -----------------------------------------------------------------------------
# The "Mediator-to-Client" Bit
# -----------------------------------------------------------------------------

class WebSocketServer(WebSocketMediator,
                      name_dotted='veredi.interface.mediator.websocket.server',
                      name_string='server'):
    '''
    Mediator for serving over WebSockets.
    '''

    def _define_vars(self) -> None:
        '''
        Set up our vars with type hinting, docstrs.
        '''
        super()._define_vars()

        self._clients: ClientRegistry = ClientRegistry(self.debug)
        '''
        Our currently connected users.
        '''

    def __init__(self,
                 context: VerediContext) -> None:
        # Base class init first.
        super().__init__(context)

        # NOTE: For increased logging on only client from the get-go:
        # log.set_group_level(log.Group.DATA_PROCESSING, log.Level.INFO)
        # log.set_group_level(log.Group.PARALLEL, log.Level.DEBUG)
        # log.critical("Server set data_proc to {}.",
        #              log.get_group_level(log.Group.DATA_PROCESSING))
        # log.data_processing(self.dotted,
        #                     "Server set data_proc to {}.",
        #                     log.get_group_level(log.Group.DATA_PROCESSING))

        # ---
        # Now we can make our WebSocket stuff...
        # ---
        self._socket = VebSocketServer(self._serdes,
                                       self._codec,
                                       self.make_med_context,
                                       self.make_msg_context,
                                       self.disconnected,
                                       self._host,
                                       path=None,
                                       port=self._port,
                                       secure=self._ssl,
                                       debug_fn=self.debug)

    # -------------------------------------------------------------------------
    # User Connection Tracking
    # -------------------------------------------------------------------------

    async def _validate_connect(self,
                                uid:  UserId,
                                ukey: Optional[UserKey],
                                conn: UserConnToken,
                                msg:  Message) -> bool:
        '''
        Validates user, registers if valid, returns valid/invalid user bool.
        '''
        self.debug("_validate_connect: Validating...\n"
                   "uid: {}, ukey: {}, conn: {}, msg: {}",
                   uid, ukey, conn, msg)

        # TODO [2020-08-13]: Actually validate. Check against what user_id we
        # expected. Check user_key or whatever as well.
        if uid and isinstance(uid, UserId):
            if uid in self._clients:
                old = self._clients.get(uid, ukey, conn)
                log.warning("_validate_connect: "
                            "User is already registered; unregistering old "
                            f"and reregistering new. "
                            f"OLD: uid: {old.id}, ukey: {old.key}, "
                            f"token: {old.connection}; "
                            f"NEW: uid: {uid}, ukey: {ukey}, token: {conn}")
                # TODO [2020-08-13]: Should we tell socket to disconnect that
                # one?
                await self.unregister(uid, ukey, conn)

            self.debug("_validate_connect: User validated.\n"
                       "uid: {}, ukey: {}, conn: {}, msg: {}",
                       uid, ukey, conn, msg)

            return True

        log.critical("_validate_connect: "
                     "User failed registration validation... "
                     "No UserId/UserKey or need to deserialize/decode?\n"
                     " uid: {} {}; ukey: {} {}",
                     type(uid), uid,
                     type(ukey), ukey)
        return False

    async def register(self,
                       user_id:  UserId,
                       user_key: Optional[UserKey],
                       conn:     UserConnToken,
                       msg:      Message) -> Optional[Message]:
        '''
        Validate client, register as connected if passes validation.

        Return ACK_CONNECT message if needed.
        '''
        self.debug("register: "
                   "user_id: {}, user_key: {}, conn: {}, msg: {}",
                   user_id, user_key, conn, msg)

        success = False
        if not await self._validate_connect(user_id, user_key, conn, msg):
            # Failed. Return ACK_CONNECT for failure.
            # TODO: Don't always return message? Always return None? IDK?
            success = False
            self.debug("register: "
                       "User failed to validate for registration: "
                       "({}, {}, {})",
                       user_id, user_key, conn)

        else:
            self.debug("register: "
                       "User validated; registering... "
                       "({}, {}, {})",
                       user_id, user_key, conn)
            # Register the client ourselves.
            self._clients.register(user_id, user_key, conn)
            # Also tell the game about them connecting.
            conn_msg = ConnectionMessage.connected(user_id, user_key, conn)
            await self._med_to_game_put(conn_msg,
                                        self.make_msg_context(conn_msg.msg_id))
            success = True
            self.debug("register: "
                       "Registered user: "
                       "({}, {}, {})",
                       user_id, user_key, conn)

        # Currently, returninng ACK_CONNECT for success and failure.
        ack = Message.connected(msg, user_id, user_key, success)
        self.debug("register: "
                   "User registration complete; sending reply...\n"
                   "to:  {}, {}\n"
                   "msg: {}",
                   user_id, user_key, ack)
        return ack

    async def disconnected(self,
                           conn:     Optional[UserConnToken]
                           ) -> Optional[Message]:
        '''
        Callback for VebSocketServer to inform of a disconnected client
        connection.
        '''
        self.debug("disconnected: "
                   "WebSocket has noticed user {} disconnected.",
                   conn)
        await self.unregister(None, None, conn)

    async def unregister(self,
                         user_id:  Optional[UserId],
                         user_key: Optional[UserKey],
                         conn:     Optional[UserConnToken]
                         ) -> Optional[Message]:
        '''
        Client has disconnected, remove from registered.
        '''
        self.debug("unregister: "
                   "user_id: {}, user_key: {}, conn: {}",
                   user_id, user_key, conn)

        # Unregister the client ourselves.
        success = self._clients.unregister(user_id, user_key, conn)
        self.debug("unregister: "
                   "success?: {}",
                   success)

        # Also tell the game about them unregistering.
        conn_msg = ConnectionMessage.disconnected(user_id, user_key, conn)
        self.debug("unregister: "
                   "Sending unregister message: {}",
                   conn_msg)
        await self._med_to_game_put(conn_msg,
                                    self.make_msg_context(conn_msg.msg_id))

        if success:
            self.debug("unregister: "
                       "Unregistered user: "
                       "({}, {}, {})",
                       user_id, user_key, conn)
        else:
            self.debug("unregister: "
                       "No user found in registry for: "
                       "({}, {}, {})",
                       user_id, user_key, conn)

        # Already disconnected, so we can't really say goodbye. Maybe in the
        # future if there's a structured shutdown or server-initiated...
        return None

    # -------------------------------------------------------------------------
    # Debug
    # -------------------------------------------------------------------------

    def debug(self,
              msg:      str,
              *args:    Any,
              **kwargs: Any) -> None:
        '''
        Debug logs if our DebugFlag has the proper bits set for Mediator
        debugging.
        '''
        if (self._debug
                and self._debug.any(DebugFlag.MEDIATOR_BASE,
                                    DebugFlag.MEDIATOR_SERVER)):
            msg = f"{self.name}: " + msg
            kwargs = log.incr_stack_level(kwargs)
            self._log_data_processing(self.dotted,
                                      msg,
                                      *args,
                                      **kwargs,
                                      log_minimum=log.Level.DEBUG)

    def logging_request(self, msg: Message) -> None:
        '''
        Ignore this on server; client doesn't get to tell us what to do.
        '''
        self.debug("logging_request: "
                   "Ignored on server; clients don't tell us what to do! "
                   "msg: {}",
                   msg)
        return None

    # -------------------------------------------------------------------------
    # Mediator API
    # -------------------------------------------------------------------------

    def make_med_context(self,
                         connection: UserConnToken = None
                         ) -> MediatorServerContext:
        '''
        Make a context with our context data, our serdes, etc.
        '''
        serdes_ctx, _ = self._serdes.background
        codec_ctx, _ = self._codec.background
        ctx = MediatorServerContext(self.dotted,
                                    type='websocket.server',
                                    serdes=serdes_ctx,
                                    codec=codec_ctx,
                                    conn=connection)
        return ctx

    def make_msg_context(self,
                         id: MonotonicId,
                         ) -> MessageContext:
        '''
        Make a context for a message.
        '''
        ctx = MessageContext(self.dotted, id)
        return ctx

    def start(self) -> None:
        '''
        The server should start accepting connections, calls from the clients,
        etc. It should be fully armed and operational after this call.

        Kicks of async co-routine for listening for connections.
        '''
        self.debug("start: Starting server...")

        try:
            # Kick it off into asyncio's hands.
            asyncio.run(self._a_main(self._shutdown_watcher(),
                                     self._serve(),
                                     self._med_queue_watcher(),
                                     self._to_game_watcher(),
                                     self._from_game_watcher(),
                                     self._test_watcher()))

        except websockets.exceptions.ConnectionClosedOK:
            pass

        except Exception as error:
            # TODO [2020-07-28]: Should we shut it all down, or keep going?
            self.shutdown = True
            import traceback
            trace = traceback.format_exc()
            log.exception(
                error,
                "Caught exception running MediatorServer coroutines:\n{}",
                trace)

        self.debug("start: Done.")

    # -------------------------------------------------------------------------
    # Asyncio / Multiprocessing Functions
    # -------------------------------------------------------------------------

    async def _shutdown_watcher(self) -> None:
        '''
        Watches `self._shutdown_process`. Will call stop() on our asyncio loop
        when the shutdown flag is set.
        '''
        self.debug("_shutdown_watcher: Wait on parent._shutdown_watcher()...")
        await super()._shutdown_watcher()

        # Tell our websocket server to finish up.
        self.debug("_shutdown_watcher: "
                   "Tell our WebSocket to stop.")
        self._socket.close()

        # # Tell ourselves to stop.
        # self.debug("Tell ourselves to stop.")
        # We should have our coroutines watching the shutdown flag.

        self.debug("_shutdown_watcher: "
                   "Done.")

    async def _to_game_watcher(self) -> None:
        '''
        Deals with sending data in our queue out to the game over our
        multiprocessing connection to it.
        '''
        # Don't block...
        while True:
            if self.any_shutdown():
                # Finish out of this coroutine if we should die.
                return

            if not self._med_to_game_has_data():
                await self._continuing()
                continue

            # Else get one thing and send it off this round.
            try:
                msg, ctx = self._med_to_game_get()
                self.debug("_to_game_watcher (_med_to_game_queue->game_pipe): "
                           "_med_to_game_queue has message to process: "
                           "msg: {}, ctx: {}",
                           msg, ctx)
                if not msg or not ctx:
                    self.debug("_to_game_watcher (_med_to_game_queue->game_pipe): "
                               "Got nothing for message to process? "
                               "Need both message and context! "
                               "msg: {}, ctx: {}",
                               msg, ctx)
                    await self._continuing()
                    continue

            except asyncio.QueueEmpty:
                # get_nowait() got nothing. That's fine; go back to waiting.
                await self._continuing()
                continue

            # Transfer from 'received from client queue' to
            # 'sent to game connection'.
            self.debug("_to_game_watcher (_med_to_game_queue->game_pipe): "
                       "Send to game pipe: {}, {}",
                       msg, ctx)
            self._game_pipe_put(msg, ctx)

            self.debug("_to_game_watcher (_med_to_game_queue->game_pipe): "
                       "Done processing message: {}, {}",
                       msg, ctx)

            # Skip this - we used get_nowait(), not get().
            # self._rx_queue.task_done()
            await self._continuing()
            continue

    async def _from_game_watcher(self) -> None:
        '''
        Watches game pipe. Gets messages from it and demarks for specific
        user(s).
        '''
        # Don't block...
        while True:
            if self.any_shutdown():
                # Finish out of this coroutine if we should die.
                return

            if not self._game_has_data():
                await self._continuing()
                continue

            # Else get one thing and send it off this round.
            try:
                msg, ctx = self._game_pipe_get()
                self.debug("_from_game_watcher (game_pipe->client_queue): "
                           "Got message from game to send: {} {}",
                           msg, ctx)

            except EOFError as error:
                log.exception(error,
                              "Failed getting from game pipe; "
                              "ignoring and continuing.")
                # EOFError gets raised if nothing left to receive or other end
                # closed. Wait til we know what that means to our game/mediator
                # pair before deciding to take (drastic?) action here...
                await self._continuing()
                continue

            else:
                # None/IGNORE check.
                if not msg or not ctx:
                    self.debug("_from_game_watcher (game_pipe->client_queue): "
                               "Got nothing for message to process? "
                               "Need both message and context! "
                               "msg: {}, ctx: {}",
                               msg, ctx)
                    await self._continuing()
                    continue
                if msg.type == MsgType.IGNORE:
                    self.debug("_from_game_watcher (game_pipe->client_queue): "
                               "Ignoring IGNORE msg: {}",
                               msg)
                    await self._continuing()
                    continue

            # ---
            # Multiple Recipients
            # ---
            self.debug("_from_game_watcher (game_pipe->client_queue): "
                       "Figuring out recipient(s): {} {}",
                       msg, ctx)

            # Is it an Envelope? They can be addressed to many clients.
            if msg.type == MsgType.ENVELOPE:
                self.debug("_from_game_watcher (game_pipe->client_queue): "
                           "Envelope - creating message for each recipient: "
                           "{} {}",
                           msg, ctx)
                # Process the envelope message into client messages.
                await self._envelope_to_messages(msg, ctx)
                self.debug("_from_game_watcher (game_pipe->client_queue): "
                           "Done processing envelope message.")

                # Skip the rest of the steps - they're for non-envelopes.
                await self._continuing()
                continue

            # ---
            # Single Recipient
            # ---
            self.debug("_from_game_watcher (game_pipe->client_queue): "
                       "Solo message - giving message to user: "
                       "{} {}",
                       msg, ctx)
            await self._message_to_client(msg, ctx)
            self.debug("_from_game_watcher (game_pipe->client_queue): "
                       "Done processing solo message.")
            await self._continuing()
            continue

    # -------------------------------------------------------------------------
    # Game Message Processors
    # -------------------------------------------------------------------------

    async def _message_to_client(self,
                                 message:     Message,
                                 context: VerediContext) -> None:
        '''
        Push this message & context into the specific client's TX queue.
        '''
        self.debug("_message_to_client: {} {}",
                   message, context)

        # Do we know this guy?
        client = self._clients.id(message.user_id)
        if not client:
            self.debug("_message_to_client: "
                       "No client to send this to. Not connected yet "
                       "or already disconnected? Dropping message: "
                       "{}, context: {}",
                       message, context)
            return

        # Transfer from 'received from game pipe' to
        # 'this user's send queue'.
        self.debug("_message_to_client: "
                   "client: {} ::"
                   "Send to client-specific tx queue: ({}, {})",
                   client, message, context)
        await client.put_data(message, context)
        self.debug("_message_to_client: "
                   "client: {} ::"
                   "Put message it client's tx queue: ({}, {})",
                   client, message, context)

    async def _envelope_to_messages(self,
                                    message: Message,
                                    context: VerediContext) -> None:
        '''
        Takes an envelope and turns it into a message for each addressee user.
        '''
        self.debug("_envelope_to_messages: "
                   "Message to send out: ({}, {})",
                   message, context)

        # ---
        # Error check.
        # ---
        envelope = message.payload
        if not isinstance(envelope, Envelope):
            err_msg = ("MediatorServer got incorrect payload in "
                       f"'{MsgType.ENVELOPE}' message. Can only handle "
                       "Envelope, got '{message.type}' from: {message}")
            error = ValueError(err_msg, message, context)
            raise log.exception(error, message, context=context)

        # ---
        # Process each addressee.
        # ---
        # Loop over each type of recipient first...
        for recipient in Recipient:
            self.debug("_envelope_to_messages: "
                       "Processing recipient: {}",
                       recipient)

            if (recipient is Recipient.INVALID
                    or recipient not in envelope.valid_recipients):
                self.debug("_envelope_to_messages: "
                           "Invalid recipient for message: {} (valid: {})",
                           recipient, envelope.valid_recipients)
                continue

            # For this type of recipient, get addresses (if any).
            address = envelope.address(recipient)
            if not address:
                self.debug("_envelope_to_messages: "
                           "No address for recipient {}: {}",
                           recipient, address)
                continue

            # Have actual users for this type of recipient. Make a message for
            # each of them.
            self.debug("_envelope_to_messages: "
                       "Making message for: recipient: {}, addressee: {}",
                       recipient, address)
            await self._address_to_messages(message.msg_id,
                                            address,
                                            envelope,
                                            context)
            self.debug("_envelope_to_messages: "
                       "Done with recipient: {}",
                       recipient)

        self.debug("_envelope_to_messages: "
                   "Done processing envelope recipients for: {}, {}",
                   message, context)

    async def _address_to_messages(self,
                                   msg_id:   MonotonicId,
                                   address:  Address,
                                   envelope: Envelope,
                                   context:  VerediContext) -> None:
        '''
        Creates a Message from `envelope` payload for each user in `address`.
        Queues the messages and context up for sending to the user(s).
        '''
        self.debug("_address_to_messages: id: {}, addr: {}, "
                   "envelope: {}, ctx: {}",
                   msg_id,
                   address,
                   envelope,
                   context)

        for uid in address.user_ids:
            # Don't bother with invalid user ids.
            if not uid or uid == UserId.INVALID:
                log.error("Cannot address Envelope to user. "
                          "Invalid UserId: {}",
                          uid)
                continue

            # Get user from user's id.
            user = self._clients.id(uid)
            # Don't bother sending to invalid users.
            if not user or not user.id or user.id == UserId.INVALID:
                # This isn't an error; could be a warning; info for now. User
                # could have logged off/disappeared/whatever while this message
                # was getting to us.
                log.info("Cannot address Envelope to UserId '{}' - user is "
                         "not connected: {}", uid, user)
                continue

            self.debug("_address_to_messages: Addressing to user {}...",
                       user)

            # Generate the message for this user at this address's
            # security.abac.Subject value/level.
            message = envelope.message(msg_id,
                                       address.security_subject,
                                       user)
            self.debug("_address_to_messages: Created message for user {}: {}",
                       user,
                       message)
            if not message:
                log.error("Failed to create message for use from Envelope. "
                          "User: {}, Access: {}, Envelope: {}",
                          user, address.security_subject, envelope)
                continue

            # Queue up message and context.
            self.debug("_address_to_messages: Queueing message to user {}: {}",
                       user,
                       message)
            await self._message_to_client(message, context)
            self.debug("_address_to_messages: Message queued to user {}.",
                       user)

        self.debug("_address_to_messages: Done creating {} messages for users "
                   "from envelope: {}",
                   msg_id, envelope)

    # -------------------------------------------------------------------------
    # WebSocket Server
    # -------------------------------------------------------------------------

    async def _serve(self) -> None:
        '''
        Read from client, send reply, close connection.
        '''
        uri = self._socket.uri
        self.debug(f"_serve: Starting to serve: {uri}")
        # await self._socket.serve_basic(self._handle_basic)
        await self._socket.serve_parallel(self._handle_produce,
                                          self._handle_consume)
        self.debug(f"_serve: Done serving: {uri}")

    def _hook_user_auth(self,
                        msg:     Optional[Message],
                        context: Optional[MediatorServerContext],
                        conn:    UserConnToken
                        ) -> Optional[Message]:
        '''
        Inserts user's id/key into `msg` if needed.
        '''
        self.debug("_hook_user_auth: "
                   "Add user's auth to message? "
                   "{}, {}, {}",
                   conn, msg, context)

        # Sanity?
        if (not msg  # No msg to fiddle with?
            # No connection to use to find their key?
            or (not conn
                and (not context or not context.connection))):
            # Can't do nothin'.
            self.debug("_hook_user_auth: "
                       "Cannot add auth - Null message or unable to "
                       "find user conn. "
                       "{}, {}, {}{}",
                       conn,
                       msg,
                       context,
                       ((" " + str(context.connection)) if context else ""))

            return msg

        # Find this user.
        if not conn:
            # Sanity check should have ensured this exists if that doesn't.
            self.debug("_hook_user_auth: "
                       "No user conn provided - getting from context."
                       "provided: {}, in-context: {}",
                       conn,
                       context.connection)
            conn = context.connection

        user = self._clients.connection(conn)
        self.debug("_hook_user_auth: "
                   "Get user via conn: {} -> {}",
                   conn,
                   user)
        # TODO: check user_key too:
        # if not user and (not msg.user_id or not msg.user_key):
        if not user and (not msg.user_id):
            log.error("Cannot insert user id/key into message that needs "
                      "it... No registered user found for "
                      f"connection: {conn}")
            # TODO: Return none, or still return msg? Not sure right now.
            return msg

        # TODO [2020-08-13]: I think msg should have id/key applied by game or
        # before it gets here? If that turns out not to be the case, just
        # quietly inject it without the debug message.

        self.debug("_hook_user_auth: "
                   "Check/insert user auth...")

        # Ok; have user... Check/insert id and/or key.
        if not msg.user_id:
            # Add user_id in.
            self.debug("_hook_user_auth: "
                       "Produced message had no user id/key: {}. "
                       "Adding from registered users: {}",
                       msg, user)
            msg.user_id = user.id

        if not msg.user_key and user.key:
            # Add user_key in.
            self.debug("_hook_user_auth: "
                       "Produced message had no user key: {}. "
                       "Adding from registered users: {}",
                       msg, user)
            msg.user_key = user.key

        self.debug("_hook_user_auth: "
                   "Done.")
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
        self.debug("_hook_consume saw message from {}: {}", conn, msg)
        return msg

    async def _handle_reply(self,
                            msg:       Optional[Message],
                            context:   Optional[MediatorServerContext],
                            conn:      UserConnToken
                            ) -> Optional[Message]:
        '''
        Reply helper for hooks and such before handing off an
        immediate reply.
        '''
        msg = self._hook_user_auth(msg, context, conn)
        self.debug("_handle_reply saw message to {}: {} {}", conn, msg, context)
        return msg

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
        # self.debug("_handle_produce_get_msg: {}",
        #            conn)

        # TODO: What to do with _med_tx_queue check/send? Check somewhere else
        # and assign to users? Don't have server use at all?

        # We need to know who to send each message to. So the messages need to
        # be assigned to a user we know of...
        client = self._clients.connection(conn)
        # self.debug("_handle_produce_get_msg: conn: {} -> client: {}",
        #            conn, client)
        if not client or not client.has_data():
            # self.debug("_handle_produce_get_msg: "
            #            "No client or no data from client: {} -> {}",
            #            client,
            #            ("HAS_DATA"
            #             if client and client.has_data() else
            #             "NO_DATA"))

            # Dunno client or no data for them right now.
            return False, False

        # Get a message to send...
        msg, ctx = client.get_data()
        self.debug("_handle_produce_get_msg: "
                   "Got message to send to client {}: {}, {}",
                   client,
                   msg, ctx)
        return msg, ctx

    async def _handle_produce(self,
                              conn: UserConnToken
                              ) -> Optional[Message]:
        '''
        Loop waiting for messages to send to this specific user.
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
                log.warning("_handle_produce: {}: "
                            "Produced nothing for sending."
                            "Ignoring msg: {}, ctx: {}",
                            conn, msg, ctx)
                await self._continuing()
                continue

            # Have something to send!
            self.debug("_handle_produce: {}: "
                       "Produced for sending to client "
                       "msg: {}, ctx: {}",
                       conn, msg, ctx)

            sender, _ = self._hp_paths_type.get(msg.type, None)
            if not sender:
                log.error("_handle_produce: {}: "
                          "No handlers for msg type? "
                          "Ignoring msg: {}, ctx: {}",
                          conn, msg, ctx)
                await self._continuing()
                continue

            self.debug("_handle_produce: {}: "
                       "Producing result from send processor...",
                       conn)
            result = await sender(msg, ctx, conn)

            # Only send out to socket if actually produced anything.
            if result:
                self.debug("_handle_produce: {}: "
                           "Sending {}...",
                           conn, result)
                result = await self._hook_produce(result, conn)
                return result

            else:
                self.debug("_handle_produce: {}: "
                           "No result to send; done.",
                           conn)

            # reloop
            await self._continuing()
            continue

    async def _hook_produce(self,
                            msg:  Optional[Message],
                            conn: UserConnToken
                            ) -> Optional[Message]:
        '''
        Hook that gets called right before `_handle_produce` returns a result.
        Can fiddle with the result, return it (or nothing or something entirely
        different)...
        '''
        self.debug("_hook_produce saw message _to_ {}: {}", conn, msg)
        if not msg or not conn:
            return msg

        # log.critical(f"\n\n
        msg = self._hook_user_auth(msg, None, conn)
        return msg

    # -------------------------------------------------------------------------
    # TX / RX Specific Handlers
    # -------------------------------------------------------------------------

    async def _htx_connect(self,
                           msg:  Message,
                           ctx:  Optional[MediatorServerContext],
                           conn: UserConnToken) -> Optional[Message]:
        '''
        Send auth/registration result back down to the client?
        Or was that handled during _hrx_connect?
        '''
        self.debug("_htx_connect saw message _to_ {}: {}, {}",
                   conn, msg, ctx)
        return await self._htx_generic(msg, ctx, conn, log_type='connect')

    async def _hrx_connect(self,
                           match:   re.Match,
                           path:    str,
                           msg:     Message,
                           context: Optional[MediatorServerContext]
                           ) -> Optional[Message]:
        '''
        Handle auth/registration request from a client.
        '''
        self.debug("_htx_connect saw message on (match {}, path {}): {}, {}",
                   match, path, msg, context)
        # UserId already decoded by Message.
        if msg:
            self.debug("_hrx_connect: msg.payload (UserId?): {}",
                       msg.payload)
        else:
            self.debug("_hrx_connect: No msg?!: {}",
                       msg)

        user_id = msg.payload
        # TODO: A user key instead of 'None'.
        user_key = None
        conn = context.connection
        self.debug("_hrx_connect: Registering user... "
                   "user_id: {}, user_key: {}, conn: {}",
                   user_id, user_key, conn)

        # Validate and register user.
        reply = await self.register(user_id, user_key, conn, msg)
        self.debug("_hrx_connect: Sending user registration reply... "
                   "user_id: {}, user_key: {}, conn: {} -> msg: {}",
                   user_id, user_key, conn, msg)
        return reply
