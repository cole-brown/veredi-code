# coding: utf-8

'''
Integration Test for a server and clients talking to each other over
websockets.

Only really tests the websockets and Mediator.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional

import multiprocessing
import multiprocessing.connection

from veredi.zest                                import zontext
from veredi.parallel                            import multiproc
from veredi.zest.base.multiproc                 import (ZestIntegrateMultiproc,
                                                        Processes,
                                                        ProcTest,
                                                        ClientProcToSubComm)
from veredi.logs                                import (log,
                                                        log_client)
from veredi.debug.const                         import DebugFlag
from veredi.base.identity                       import (MonotonicId,
                                                        MonotonicIdGenerator)
from veredi.data.identity                       import (UserId,
                                                        UserIdGenerator,
                                                        UserKey,
                                                        UserKeyGenerator)
from veredi.base.context                        import (VerediContext,
                                                        UnitTestContext)
from veredi.data.config.context                 import ConfigContext


# ---
# Need these to register...
# ---
from veredi.data.serdes.json                    import serdes


# ---
# Mediation
# ---
from veredi.interface.mediator.const            import MsgType
from veredi.interface.mediator.message          import Message
from veredi.interface.mediator.websocket.server import WebSocketServer
from veredi.interface.mediator.websocket.client import WebSocketClient
from veredi.interface.mediator.context          import MessageContext
from veredi.interface.mediator.payload.logging  import (LogPayload,
                                                        LogReply,
                                                        LogField,
                                                        Validity,
                                                        _NC_LEVEL)
from veredi.interface.mediator.payload.bare     import BarePayload


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

LOG_LEVEL = log.Level.INFO  # DEBUG
'''Test should set this to desired during set_up()'''


# -----------------------------------------------------------------------------
# Multiprocessing Runners
# -----------------------------------------------------------------------------
def run_server(comms: multiproc.SubToProcComm, context: VerediContext) -> None:
    '''
    Init and run server-side client/engine IO mediator.
    '''
    # ------------------------------
    # Set Up Logging, Get from Context
    # ------------------------------
    comms = ConfigContext.subproc(context)
    if not comms:
        raise log.exception(
            TypeError,
            "MediatorServer requires a SubToProcComm; received None.")

    log_level = ConfigContext.log_level(context)
    lumberjack = log.get_logger(comms.name,
                                min_log_level=log_level)

    multiproc._sigint_ignore()

    # ------------------------------
    # Sanity Check
    # ------------------------------
    # It's a test - and the first multiprocess test - so... don't assume the
    # basics.
    if not comms.pipe:
        raise log.exception(
            TypeError,
            "MediatorServer requires a pipe connection; received None.",
            veredi_logger=lumberjack)
    if not comms.config:
        raise log.exception(
            TypeError,
            "MediatorServer requires a configuration; received None.",
            veredi_logger=lumberjack)
    if not log_level:
        raise log.exception(
            TypeError,
            "MediatorServer requires a default log level (int); "
            "received None.",
            veredi_logger=lumberjack)
    if not comms.shutdown:
        raise log.exception(
            TypeError,
            "MediatorServer requires a shutdown flag; received None.",
            veredi_logger=lumberjack)

    # ------------------------------
    # Finish Set-Up and Start It.
    # ------------------------------

    # Always set LOG_SKIP flag in case its wanted.
    comms.debug_flags = comms.debug_flags | DebugFlag.LOG_SKIP

    lumberjack.debug(f"Starting WebSocketServer '{comms.name}'...")
    mediator = WebSocketServer(context)
    mediator.start()

    # ------------------------------
    # Sub-Process is done now.
    # ------------------------------
    lumberjack.debug(f"MediatorServer '{comms.name}' done.")


def run_client(comms: multiproc.SubToProcComm, context: VerediContext) -> None:
    '''
    Init and run one client-side client/engine IO mediator.
    '''
    # ------------------------------
    # Set Up Logging, Get from Context
    # ------------------------------
    comms = ConfigContext.subproc(context)
    if not comms:
        raise log.exception(
            TypeError,
            "MediatorClient requires a SubToProcComm; received None.")

    log_level = ConfigContext.log_level(context)
    lumberjack = log.get_logger(comms.name,
                                min_log_level=log_level)

    multiproc._sigint_ignore()

    # ------------------------------
    # Sanity Check
    # ------------------------------
    # It's a test - and the first multiprocess test - so... don't assume the
    # basics.
    if not comms.pipe:
        raise log.exception(
            TypeError,
            "MediatorClient requires a pipe connection; received None.",
            veredi_logger=lumberjack)
    if not comms.config:
        raise log.exception(
            TypeError,
            "MediatorClient requires a configuration; received None.",
            veredi_logger=lumberjack)
    if not log_level:
        raise log.exception(
            TypeError,
            "MediatorClient requires a default log level (int); "
            "received None.",
            veredi_logger=lumberjack)
    if not comms.shutdown:
        raise log.exception(
            TypeError,
            "MediatorClient requires a shutdown flag; received None.",
            veredi_logger=lumberjack)

    # ------------------------------
    # Finish Set-Up and Start It.
    # ------------------------------

    # Always set LOG_SKIP flag in case its wanted.
    comms.debug_flags = comms.debug_flags | DebugFlag.LOG_SKIP

    lumberjack.debug(f"Starting WebSocketClient '{comms.name}'...")
    mediator = WebSocketClient(context)
    mediator.start()

    # ------------------------------
    # Sub-Process is done now.
    # ------------------------------
    lumberjack.debug(f"MediatorClient '{comms.name}' done.")


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_WebSockets(ZestIntegrateMultiproc):

    # TODO [2020-07-25]: 2 or 4 or something?
    NUM_CLIENTS = 1

    NAME_LOG = 'veredi.test.websockets.log'
    NAME_SERVER = 'veredi.test.websockets.server'
    NAME_CLIENT_FMT = 'veredi.test.websockets.client.{i:02d}'
    NAME_MAIN = 'veredi.test.websockets.tester'

    # -------------------------------------------------------------------------
    # Set-Up & Tear-Down
    # -------------------------------------------------------------------------

    def pre_set_up(self) -> None:
        super().pre_set_up('config.websocket.yaml')

    def set_up(self):
        self.debug_flags = DebugFlag.MEDIATOR_ALL
        self.DISABLED_TESTS = set({
            # Nothing, ideally.

            # # ---
            # # This is cheating.
            # # ---
            # 'test_ignored_tests',

            # # ---
            # # Simplest test.
            # # ---
            # 'test_nothing',
            # 'test_logs_ignore',

            # # ---
            # # More complex tests.
            # # ---
            # 'test_connect',
            # 'test_ping',
            # 'test_echo',
            # 'test_text',
            # 'test_logging',
        })

        default_flags = ProcTest.NONE
        super().set_up(LOG_LEVEL, default_flags)

        self._msg_id: MonotonicIdGenerator = MonotonicId.generator()
        '''ID generator for creating Mediator messages.'''

        self._user_id: UserIdGenerator = UserId.generator()
        '''For these, just make up user ids.'''

        self._set_up_server(self.config, default_flags)  # ProcTest.DNE)
        self._set_up_clients(self.config, default_flags)  # ProcTest.DNE)

    def tear_down(self):
        # Stop our processes.
        if self.proc.server:
            self._stop(self.proc.server)
        if self.proc.clients:
            for client in self.proc.clients:
                self._stop(client)

        # Run our tear downs.
        self._tear_down_server()
        self._tear_down_clients()

        # And now hand over to parent for tear_down of log proc, whatever else
        # it does.
        super().tear_down(LOG_LEVEL)

        self._msg_id = None
        self._user_id = None

    # ---
    # Server Set-Up / Tear-Down
    # ---

    def _set_up_server(self, config, proc_test):
        if proc_test.has(ProcTest.DNE):
            # Mediator Server 'Does Not Exist' right now.
            self.log_critical("Mediator server set up has {}. "
                              "Skipping creation/set-up.",
                              ProcTest.DNE)
            return

        self.log_debug("Set up mediator server... {}",
                       proc_test)
        name = self.NAME_SERVER
        context = zontext.empty(__file__,
                                self,
                                '_set_up_server',
                                UnitTestContext)

        self.proc.server = multiproc.set_up(proc_name=name,
                                            config=self.config,
                                            context=context,
                                            entry_fn=run_server,
                                            initial_log_level=LOG_LEVEL,
                                            debug_flags=self.debug_flags,
                                            unit_testing=True,
                                            proc_test=proc_test)

    def _tear_down_server(self):
        if not self.proc.server:
            # Mediator Server 'Does Not Exist' right now.
            self.log_critical("No mediator server exists. Skipping tear-down.")
            return

        self.log_debug("Tear down mediator server...")
        # Ask all mediators to stop if we haven't already...
        if not self.proc.server.shutdown.is_set():
            self._stop(self.proc.server)

        self.proc.server = None

    # ---
    # Clients Set-Up / Tear-Down
    # ---

    def _set_up_clients(self, config, proc_test):
        if proc_test.has(ProcTest.DNE):
            # Mediator Clients 'Do Not Exist' right now.
            self.log_critical("Mediator client(s) set up has {}. "
                              "Skipping creation/set-up.",
                              ProcTest.DNE)
            return

        self.log_debug("Set up mediator client(s)... {}",
                       proc_test)
        # Shared with all clients.
        shutdown = multiprocessing.Event()

        # Init the clients to an empty list.
        self.proc.clients = []
        # And make as many as we want...
        for i in range(self.NUM_CLIENTS):
            name = self.NAME_CLIENT_FMT.format(i=i)
            context = zontext.empty(__file__,
                                    self,
                                    f"_set_up_clients('{name}')",
                                    UnitTestContext)

            # Give the client an id/key directly for now...
            user_id = self._user_id.next(name)
            # TODO: generate a user key
            user_key = None
            ut_data = context.sub
            ut_data['id'] = user_id
            ut_data['key'] = user_key

            # Set up client. Use ClientProcToSubComm subclass so unit tests can
            # have easy access to client's id/key.
            client = multiproc.set_up(proc_name=name,
                                      config=self.config,
                                      context=context,
                                      entry_fn=run_client,
                                      t_proc_to_sub=ClientProcToSubComm,
                                      initial_log_level=LOG_LEVEL,
                                      debug_flags=self.debug_flags,
                                      unit_testing=True,
                                      proc_test=proc_test,
                                      shutdown=shutdown)

            # Save id/key where test can access them.
            client.set_user(user_id, user_key)

            # Append to the list of clients!
            self.proc.clients.append(client)

    def _tear_down_clients(self):
        if not self.proc.clients:
            # Mediator Clients 'Do Not Exist' right now.
            self.log_critical("No mediator client(s) exist. "
                              "Skipping tear-down.")
            return

        self.log_debug("Tear down mediator client(s)...")
        # Ask all mediators to stop if we haven't already... Checking each
        # client even though clients all share a shutdown event currently, just
        # in case that changes later.
        for client in self.proc.clients:
            if not client.shutdown.is_set():
                self._stop(client)
                break

        self.proc.clients = None

    # -------------------------------------------------------------------------
    # Test Helpers
    # -------------------------------------------------------------------------

    def msg_context(self,
                    msg_ctx_id: Optional[MonotonicId] = None
                    ) -> MessageContext:
        '''
        Some simple context to pass with messages.

        Makes up an id if none supplied.
        '''
        msg_id = msg_ctx_id or MonotonicId(7731, allow=True)
        ctx = MessageContext(
            'veredi.zest.integration.communication.'
            'zest_client_server_websocket',
            msg_id)
        return ctx

    # -------------------------------------------------------------------------
    # Do-Something-During-A-Test Functions
    # -------------------------------------------------------------------------

    def client_connect(self, client):
        # Send something... Currently client doesn't care and tries to connect
        # on any message it gets when it has no connection. But it may change
        # later.
        mid = Message.SpecialId.CONNECT
        msg = Message(mid, MsgType.IGNORE,
                      payload=None)
        client.pipe.send((msg, self.msg_context(mid)))

        # Wait a bit for all the interprocess communicating to happen.
        self.wait(0.5)

        # Received "you're connected now" back?
        recv, ctx = client.pipe.recv()

        # We have a whole test to make sure this goes right, so just
        # sanity checks.
        self.assertTrue(recv)
        self.assertIsInstance(recv, Message)
        self.assertIsInstance(recv.msg_id, Message.SpecialId)
        self.assertEqual(recv.type, MsgType.ACK_CONNECT)
        self.assertIsNotNone(recv.user_id)

        # Server->game. Server sends game user info when they connect.
        self.assertTrue(self.proc.server.has_data())
        recv, ctx = self.proc.server.recv()
        self.assertIsNotNone(recv)
        self.assertIsNotNone(ctx)
        self.assertIsInstance(recv, Message)
        self.assertIsInstance(recv.msg_id, Message.SpecialId)
        self.assertEqual(recv.msg_id, Message.SpecialId.CONNECT)
        self.assertEqual(recv.type, MsgType.CONNECT)

        # Ok; now everyone should be empty.
        self.assert_empty_pipes()

    # =========================================================================
    # =--------------------------------Tests----------------------------------=
    # =--                        Real Actual Tests                          --=
    # =---------------------...after so much prep work.-----------------------=
    # =========================================================================

    # ------------------------------
    # Check to see if we're blatently ignoring anything...
    # ------------------------------

    def test_ignored_tests(self):
        self.assertFalse(self.DISABLED_TESTS,
                         "Expected no disabled tests, "
                         f"got: {self.DISABLED_TESTS}")

    # ------------------------------
    # Test doing nothing and cleaning up.
    # ------------------------------

    def do_test_nothing(self):
        self.assertIsInstance(self.proc, Processes)
        self.assertIsInstance(self.proc.server, multiproc.ProcToSubComm)
        self.assertIsInstance(self.proc.clients, list)
        for client in self.proc.clients:
            self.assertIsInstance(client, multiproc.ProcToSubComm)

        # This really doesn't do much other than bring up the processes and
        # then kill them, but it's something.
        self.wait(0.1)

        # Make sure we don't have anything in the queues... Allow for having
        # neither client nor server. We've had to regress all the way back to
        # trying to get this running a few times already. Multiprocessing with
        # multiple threads and multiple asyncios is... fun.
        self.assert_empty_pipes()

    def test_nothing(self):
        # No checks for this, really. Just "does it properly not explode"?
        self.assert_test_ran(
            self.runner_of_test(self.do_test_nothing))

    # ------------------------------
    # Test Client Requesting Connection to Server.
    # ------------------------------

    def do_test_connect(self, client):
        # Send something... Currently client doesn't care and tries to connect
        # on any message it gets when it has no connection. But it may change
        # later.
        mid = Message.SpecialId.CONNECT
        msg = Message(mid, MsgType.IGNORE,
                      payload=None)
        client.pipe.send((msg, self.msg_context(mid)))

        # Received "you're connected now" back?
        recv, ctx = client.pipe.recv()

        # Make sure we got a message back and it has the ping time in it.
        self.assertTrue(recv)
        self.assertTrue(ctx)
        self.assertIsInstance(recv, Message)
        self.assertTrue(ctx, MessageContext)
        self.assertIsInstance(recv.msg_id, Message.SpecialId)
        self.assertEqual(mid, recv.msg_id)

        # Translation from stored int to enum or id class instance borks this
        # check up. `msg.msg_id` will be MonotonicId, `recv.msg_id` will be
        # SpecialId, and they won't equal.
        # TODO: Does this work now?
        self.assertEqual(msg.msg_id, recv.msg_id)

        # Don't check this either. Duh. We create it as IGNORE, we're testing
        # CONNECT, and we're expecting ACK_CONNECT back.
        # self.assertEqual(msg.type, recv.type)
        # Can do this though.
        self.assertEqual(recv.type, MsgType.ACK_CONNECT)
        self.assertIsInstance(recv.payload, BarePayload)
        self.assertIn('code', recv.payload.data)
        self.assertIn('text', recv.payload.data)
        # Did we connect successfully?
        self.assertTrue(recv.payload.data['code'])

        # This should be... something.
        self.assertIsNotNone(recv.user_id)
        self.assertIsInstance(recv.user_id, UserId)
        # Not sure what it should be, currently, so can't really test that?

        # TODO [2020-08-13]: Server should know what key client will have
        # before client connects.

    def test_connect(self):
        if self.disabled():
            return

        self.assert_test_ran(
            self.runner_of_test(self.do_test_connect, *self.proc.clients))

    # ------------------------------
    # Test cliets pinging server.
    # ------------------------------

    def do_test_ping(self, client):
        # Get the connect out of the way.
        self.client_connect(client)

        mid = self._msg_id.next()
        msg = Message(mid, MsgType.PING,
                      payload=None)
        client.pipe.send((msg, self.msg_context(mid)))
        recv, ctx = client.pipe.recv()
        # Make sure we got a message back and it has the ping time in it.
        self.assertTrue(recv)
        self.assertTrue(ctx)
        self.assertIsInstance(recv, Message)
        self.assertTrue(ctx, MessageContext)
        self.assertEqual(msg.msg_id, ctx.id)
        self.assertEqual(mid, recv.msg_id)
        self.assertEqual(msg.msg_id, recv.msg_id)
        self.assertEqual(msg.type, recv.type)

        # I really hope the local ping is between negative nothingish and
        # positive five seconds.
        self.assertIsInstance(recv.payload, float)
        self.assertGreater(recv.payload, -0.0000001)
        self.assertLess(recv.payload, 5)

        # Make sure we don't have anything in the queues...
        self.assert_empty_pipes()

    def test_ping(self):
        # No other checks for ping outside do_test_ping.
        self.assert_test_ran(
            self.runner_of_test(self.do_test_ping, *self.proc.clients))

    # ------------------------------
    # Test Clients sending an echo message.
    # ------------------------------

    def do_test_echo(self, client):
        # Get the connect out of the way.
        self.client_connect(client)

        mid = self._msg_id.next()
        send_msg = f"Hello from {client.name}"
        expected = send_msg
        msg = Message(mid, MsgType.ECHO,
                      payload=send_msg)
        ctx = self.msg_context(mid)
        client.send(msg, ctx)
        self.wait(0.5)
        recv, ctx = client.recv()
        # Make sure we got a message back and it has the same
        # message as we sent.
        self.assertTrue(recv)
        self.assertTrue(ctx)
        self.assertIsInstance(recv, Message)
        self.assertTrue(ctx, MessageContext)
        # IDs made it around intact.
        self.assertEqual(msg.msg_id, ctx.id)
        self.assertEqual(mid, recv.msg_id)
        self.assertEqual(msg.msg_id, recv.msg_id)
        # Sent echo, got echo-back.
        self.assertEqual(msg.type, MsgType.ECHO)
        self.assertEqual(recv.type, MsgType.ECHO_ECHO)
        # Got what we sent.
        self.assertIsInstance(recv.payload, str)
        self.assertEqual(recv.payload, expected)

        # Make sure we don't have anything in the queues...
        self.assert_empty_pipes()

    def test_echo(self):
        self.assert_test_ran(
            self.runner_of_test(self.do_test_echo, *self.proc.clients))

    # ------------------------------
    # Test Clients sending text messages to server.
    # ------------------------------

    def do_test_text(self, client):
        # Get the connect out of the way.
        self.client_connect(client)

        mid = self._msg_id.next()

        # ---
        # Client -> Server: TEXT
        # ---
        self.log_debug("client to server...")

        send_txt = f"Hello from {client.name}?"
        client_send = Message(mid, MsgType.TEXT,
                              payload=send_txt)
        client_send_ctx = self.msg_context(mid)

        client_recv_msg = None
        client_recv_ctx = None
        with log.LoggingManager.on_or_off(self.debugging, True):
            # Have client send, then receive from server.
            client.pipe.send((client_send, client_send_ctx))

            # Server automatically sent an ACK_ID, need to check client.
            client_recv_msg, client_recv_ctx = client.pipe.recv()

        self.log_debug("client send msg: {}", client_send)
        # Why is this dying when trying to print its payload?!
        # # self.log_ultra_mega_debug(
        # #     "client_recv msg: {client_recv_msg._payload}")
        # ...
        # ...Huh... f-strings and veredi.logger and multiprocessor or
        # log_server or something don't like each other somewhere along
        # the way? This is a-ok:
        self.log_debug("client_recv msg: {}", client_recv_msg._payload)

        # Make sure that the client received the correct thing.
        self.assertIsNotNone(client_recv_msg)
        self.assertIsInstance(client_recv_msg, Message)
        self.assertIsNotNone(client_recv_ctx)
        self.assertIsInstance(client_recv_ctx, MessageContext)
        self.assertEqual(mid, client_recv_msg.msg_id)
        self.assertEqual(client_send.msg_id, client_recv_msg.msg_id)
        self.assertEqual(client_recv_msg.type, MsgType.ACK_ID)
        ack_id = client_recv_msg.payload
        self.assertIsInstance(ack_id, type(mid))

        # ---
        # Check: Client -> Server: TEXT
        # ---
        self.log_debug("test_text: server to game...")
        server_recv_msg = None
        server_recv_ctx = None
        with log.LoggingManager.on_or_off(self.debugging, True):
            # Our server should have put the client's packet in its pipe for
            # us... I hope.
            self.log_debug("test_text: game recv from server...")
            server_recv_msg, server_recv_ctx = self.proc.server.pipe.recv()

        self.log_debug("client_sent/server_recv: {}", server_recv_msg)
        # Make sure that the server received the correct thing.
        self.assertEqual(mid, server_recv_msg.msg_id)
        self.assertEqual(client_send.msg_id, server_recv_msg.msg_id)
        self.assertEqual(client_send.type, server_recv_msg.type)
        self.assertIsInstance(server_recv_msg.payload, str)
        self.assertEqual(server_recv_msg.payload, send_txt)
        # Check the Context.
        self.assertIsInstance(server_recv_ctx, MessageContext)
        self.assertEqual(server_recv_ctx.id, ack_id)

        # ---
        # Server -> Client: TEXT
        # ---

        self.log_debug("test_text: server_send/client_recv...")
        # Tell our server to send a reply to the client's text.
        recv_txt = f"Hello from {self.proc.server.name}!"
        server_send = Message(server_recv_ctx.id, MsgType.TEXT,
                              user_id=server_recv_msg.user_id,
                              user_key=server_recv_msg.user_key,
                              payload=recv_txt)

        client_recv_msg = None
        client_recv_ctx = None
        with log.LoggingManager.on_or_off(self.debugging, True):
            # Make something for server to send and client to recvive.
            self.log_debug("test_text: server_send...")
            self.log_debug("test_text: pipe to game: {}", server_send)
            self.proc.server.pipe.send((server_send, server_recv_ctx))
            self.log_debug("test_text: client_recv...")
            client_recv_msg, client_recv_ctx = client.pipe.recv()

        self.log_debug("server_sent/client_recv: {}", client_recv_msg)
        self.assertIsNotNone(client_recv_ctx)
        self.assertIsInstance(client_recv_ctx, MessageContext)

        self.assertIsInstance(client_recv_msg, Message)
        self.assertEqual(ack_id, client_recv_msg.msg_id)
        self.assertEqual(server_send.msg_id, client_recv_msg.msg_id)
        self.assertEqual(server_send.type, client_recv_msg.type)
        self.assertIsInstance(client_recv_msg.payload, str)
        self.assertEqual(client_recv_msg.payload, recv_txt)

        # ---
        # Server -> Client: ACK
        # ---

        # Client automatically sent an ACK_ID, need to check server for it.
        server_recv = self.proc.server.pipe.recv()

        self.log_debug("server sent msg: {}", server_send)
        self.log_debug("server recv ack: {}", server_recv)
        # Make sure that the server received the correct thing.
        self.assertIsNotNone(server_recv)
        self.assertIsInstance(server_recv, tuple)
        self.assertEqual(len(server_recv), 2)  # Make sure next line is sane...
        server_recv_msg, server_recv_ctx = server_recv
        # Make sure that the server received their ACK_ID.
        self.assertIsNotNone(server_recv_msg)
        self.assertIsInstance(server_recv_msg, Message)
        self.assertIsNotNone(server_recv_ctx)
        self.assertIsInstance(server_recv_ctx, MessageContext)
        self.assertEqual(mid, server_recv_msg.msg_id)
        self.assertEqual(server_send.msg_id, server_recv_msg.msg_id)
        self.assertEqual(server_recv_msg.type, MsgType.ACK_ID)
        ack_id = server_recv_msg.payload
        self.assertIsInstance(ack_id, type(mid))

        # Make sure we don't have anything in the queues...
        self.assert_empty_pipes()

    def test_text(self):
        self.assert_test_ran(
            self.runner_of_test(self.do_test_text, *self.proc.clients))

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # This is brittle - it can cause whatever runs next to get stuck in some
    # weird infinite loop of runner_of_test() calls.
    #
    # Since this is now eclipsed by test_logging(), which also checks ignoring
    # logs, I'm just commenting it out.
    #
    # Next person (me) to come along should put it out of its misery.
    #
    # # ------------------------------
    # # Test Ignoring Logs...
    # # ------------------------------
    #
    # def do_test_logs_ignore(self):
    #     self.assertIsNotNone(self.proc.log)
    #
    #     self.assertEqual(self.proc.log.ignored_counter.value, 0)
    #
    #     self.proc.log.ignore_logs.set()
    #
    #     # Does this not get printed and does this increment our counter?
    #     self.assertEqual(self.proc.log.ignored_counter.value, 0)
    #
    #     # Connect this process to the log server, do a long that should be
    #     # ignored, and then disconnect.
    #     log_client.init(self.__class__.__name__, log_level)
    #     self.log_critical("You should not see this.")
    #     log_client.close()
    #     # Gotta wait a bit for the counter to sync back to this process,
    #     # I guess.
    #     self.wait(1)  # 0.1)
    #     self.assertEqual(self.proc.log.ignored_counter.value, 1)
    #
    # def test_logs_ignore(self):
    #     self.assert_test_ran(
    #         self.runner_of_test(self.do_test_logs_ignore))
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    # ------------------------------
    # Test Server sending LOGGING to client.
    # ------------------------------

    def _check_ignored_counter(self,
                               assert_eq_value=None,
                               assert_gt_value=None):
        # Check counter if asked.
        if assert_eq_value is not None:
            self.assertEqual(self.proc.log.ignored_counter.value,
                             assert_eq_value)

        if assert_gt_value is not None:
            self.assertGreater(self.proc.log.ignored_counter.value,
                               assert_gt_value)

    def ignore_logging(self,
                       enable,
                       assert_eq_value=None,
                       assert_gt_value=None):
        '''
        Instruct log_server to start or stop ignoring log messages. Will
        assertEqual() or assertGreater() on the ignored_counter if those values
        are not None.

        `enable` should be:
          - True or False to toggle. Asserts before and after values.
          - None to leave alone.
        '''
        if enable is True:
            # Sanity check.
            self.assertFalse(self.proc.log.ignore_logs.is_set())
            was = self.proc.log.ignore_logs.is_set()

            # Check counter if asked.
            self._check_ignored_counter(assert_eq_value, assert_gt_value)

            # Start ignoring logs.
            self.proc.log.ignore_logs.set()

            line_pre = '-='
            line_post = '=-'
            line_title = 'logging'
            line_width = 80
            line_padding = line_width - len(line_title)
            line_pad_half = line_padding // 2
            line_titled = ((line_pre * (line_pad_half // len(line_pre)))
                           + line_title
                           + (line_post * (line_pad_half // len(line_post))))
            line_untitled = line_pre * (line_width // 2 - 1) + '-'

            self.log_debug(
                '\n\n'
                + line_titled + '\n'
                + 'IGNORE LOGGING: \n'
                + f'  was    = "{was}" \n'
                + f'  set    = "{self.proc.log.ignore_logs.is_set()}" \n'
                + f'  count  = "{self.proc.log.ignored_counter.value} \n'
                + line_untitled
                + '\n\n')

        elif enable is False:
            # Sanity check.
            self.assertTrue(self.proc.log.ignore_logs.is_set())

            # Stop ignoring logs.
            was = self.proc.log.ignore_logs.is_set()
            self.proc.log.ignore_logs.clear()

            line_pre = '-='
            line_post = '=-'
            line_title = 'logging'
            line_width = 80
            line_padding = line_width - len(line_title)
            line_pad_half = line_padding // 2
            line_titled = ((line_pre * (line_pad_half // len(line_pre)))
                           + line_title
                           + (line_post * (line_pad_half // len(line_post))))
            line_untitled = line_pre * (line_width - 1) + '-'

            self.log_debug(
                '\n\n'
                + line_untitled + '\n'
                + 'IGNORE LOGGING: \n'
                + f'  was    = "{was}" \n'
                + f'  set    = "{self.proc.log.ignore_logs.is_set()}" \n'
                + f'  count  = "{self.proc.log.ignored_counter.value} \n'
                + line_titled
                + '\n\n')

            # Check counter if asked.
            self._check_ignored_counter(assert_eq_value, assert_gt_value)

        elif enable is None:
            # Check counter if asked.
            self._check_ignored_counter(assert_eq_value, assert_gt_value)

        # Um... what?
        else:
            self.fail(f'enabled must be True/False/None. Got: {enable}')

        # Wait a bit so flag propogates to log_server? Maybe? Why isn't
        # this working?
        # It wasn't working because a LogRecordSocketReceiver's 'request' is a
        # whole client, actually, whereas I thought it was a log record.
        self.wait(0.1)

    def do_test_logging(self, client):
        # Get the connect out of the way.
        self.client_connect(client)

        # Start ignoring logs.
        self.ignore_logging(True, assert_eq_value=0)

        # Have a client adjust its log level to debug. Should spit out a lot of
        # logs then.
        payload = LogPayload()
        payload.request_level(log.Level.DEBUG)

        mid = self._msg_id.next()
        send_msg = Message.log(mid,
                               client.user_id,
                               client.user_key,
                               payload)

        send_ctx = self.msg_context(mid)
        # server -> client
        self.proc.server.pipe.send((send_msg, send_ctx))
        # Server should have put client's reply into the unit test pipe so we
        # can check it.
        ut_msg = self.proc.server.ut_pipe.recv()

        # Make sure we got a LOGGING message reply back.
        self.assertTrue(ut_msg)
        self.assertIsInstance(ut_msg, Message)
        # Sent logging... right?
        self.assertEqual(send_msg.type, MsgType.LOGGING)
        # Got logging... right?
        self.assertEqual(ut_msg.type, MsgType.LOGGING)

        # Got logging response?
        self.assertIsInstance(ut_msg.payload, LogPayload)
        report = ut_msg.payload.report
        self.assertIsNotNone(report)
        level = report[LogField.LEVEL]

        # Got reply for our level request?
        self.assertIsInstance(level, LogReply)
        self.assertEqual(level.valid, Validity.VALID)

        # Got /valid/ reply?
        self.assertTrue(LogReply.validity(level.value, _NC_LEVEL),
                        Validity.VALID)

        # Client reports they're now at the level we requested?
        self.assertEqual(level.value, log.Level.DEBUG)

        # Client should have push into the ut_pipe too.
        # Don't really care, at the moment, but we do care to
        # assert_empty_pipes() for other reasons so get this one out.
        ut_msg_client = client.ut_pipe.recv()
        self.assertTrue(ut_msg_client)
        self.assertIsInstance(ut_msg_client, Message)
        self.assertEqual(ut_msg_client.type, MsgType.LOGGING)

        self.wait(0.1)
        # Stop ignoring logs and make sure we ignored something, at least,
        # right? Well... either have to tell client to go back to previous
        # logging level or we have to keep ignoring. Clean-up / tear-down has
        # logs too.
        self.ignore_logging(None, assert_gt_value=2)

        # Make sure we don't have anything in the queues...
        self.assert_empty_pipes()

    def test_logging(self):
        self.assert_test_ran(
            self.runner_of_test(self.do_test_logging, *self.proc.clients))


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.zest.integration.communication.zest_client_server_websocket

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
