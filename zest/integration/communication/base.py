# coding: utf-8

'''
Base testing class for zest_websocket_and_cmds.

Only really tests the websockets and Mediator.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Tuple, Literal

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
# Mediation
# ---
from veredi.interface.mediator.const            import MsgType
from veredi.interface.mediator.message          import Message
from veredi.interface.mediator.websocket.server import WebSocketServer
from veredi.interface.mediator.websocket.client import WebSocketClient
from veredi.interface.mediator.context          import MessageContext
from veredi.interface.mediator.payload.bare     import BarePayload


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


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

    proc_test = context.sub.get('proc-test', ProcTest.NONE)
    delay_log_level = proc_test.has(ProcTest.LOG_LEVEL_DELAY)
    log_level = ConfigContext.log_level(context)
    log_level_init = (None
                      if delay_log_level else
                      log_level)

    logger_server = log.get_logger(comms.name,
                                   min_log_level=log_level_init)

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
            veredi_logger=logger_server)
    if not comms.config:
        raise log.exception(
            TypeError,
            "MediatorServer requires a configuration; received None.",
            veredi_logger=logger_server)
    if not log_level:
        raise log.exception(
            TypeError,
            "MediatorServer requires a default log level (int); "
            "received None.",
            veredi_logger=logger_server)
    if not comms.shutdown:
        raise log.exception(
            TypeError,
            "MediatorServer requires a shutdown flag; received None.",
            veredi_logger=logger_server)

    # ------------------------------
    # Finish Set-Up and Start It.
    # ------------------------------

    # Always set LOG_SKIP flag in case its wanted.
    comms.debug_flags = comms.debug_flags | DebugFlag.LOG_SKIP

    logger_server.debug(f"Starting WebSocketServer '{comms.name}'...")
    mediator = WebSocketServer(context)
    mediator.start()

    # We've delayed as long as we can; set log level.
    if delay_log_level:
        log.set_level_min(log_level, logger_server)

    # ------------------------------
    # Sub-Process is done now.
    # ------------------------------
    logger_server.debug(f"MediatorServer '{comms.name}' done.")


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

    proc_test = context.sub.get('proc-test', ProcTest.NONE)
    delay_log_level = proc_test.has(ProcTest.LOG_LEVEL_DELAY)
    log_level = ConfigContext.log_level(context)
    log_level_init = (None
                      if delay_log_level else
                      log_level)

    logger_client = log.get_logger(comms.name,
                                   min_log_level=log_level_init)

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
            veredi_logger=logger_client)
    if not comms.config:
        raise log.exception(
            TypeError,
            "MediatorClient requires a configuration; received None.",
            veredi_logger=logger_client)
    if not log_level:
        raise log.exception(
            TypeError,
            "MediatorClient requires a default log level (int); "
            "received None.",
            veredi_logger=logger_client)
    if not comms.shutdown:
        raise log.exception(
            TypeError,
            "MediatorClient requires a shutdown flag; received None.",
            veredi_logger=logger_client)

    # ------------------------------
    # Finish Set-Up and Start It.
    # ------------------------------

    # Always set LOG_SKIP flag in case its wanted.
    comms.debug_flags = comms.debug_flags | DebugFlag.LOG_SKIP

    logger_client.debug(f"Starting WebSocketClient '{comms.name}'...")
    mediator = WebSocketClient(context)
    mediator.start()

    # We've delayed as long as we can; set log level.
    if delay_log_level:
         log.set_level_min(log_level, logger_client)

    # ------------------------------
    # Sub-Process is done now.
    # ------------------------------
    logger_client.debug(f"MediatorClient '{comms.name}' done.")


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_WebSockets_Base(ZestIntegrateMultiproc):

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # TODO [2020-07-25]: 2 or 4 or something?
    NUM_CLIENTS = 1

    NAME_LOG = 'veredi.test.websockets.log'
    NAME_SERVER = 'veredi.test.websockets.server'
    NAME_CLIENT_FMT = 'veredi.test.websockets.client.{i:02d}'
    NAME_MAIN = 'veredi.test.websockets.tester'

    # -------------------------------------------------------------------------
    # Set-Up & Tear-Down
    # -------------------------------------------------------------------------

    def pre_set_up(self,
                   # Ignored params:
                   filename:  Literal[None]  = None,
                   extra:     Literal[Tuple] = (),
                   test_type: Literal[None]  = None) -> None:
        super().pre_set_up('config.websocket.yaml',
                           filename=__file__)
        self.DISABLED_TESTS = set()
        '''
        Strings of test names that should be skipped.
        e.g. 'test_connect'
        '''

    def set_up(self,
               log_level:         log.Level,
               proc_flags_server: ProcTest,
               proc_flags_client: ProcTest,
               proc_flags_logs:   ProcTest = ProcTest.NONE) -> None:
        self.debug_flags = DebugFlag.MEDIATOR_ALL

        super().set_up(log_level, proc_flags_logs)

        self._msg_id: MonotonicIdGenerator = MonotonicId.generator()
        '''ID generator for creating Mediator messages.'''

        self._user_id: UserIdGenerator = UserId.generator()
        '''For these, just make up user ids.'''

        self._set_up_server(log_level, proc_flags_server)
        self._set_up_clients(log_level, proc_flags_client)

    def tear_down(self,
                  log_level: log.Level) -> None:
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
        super().tear_down(log_level)

        self._msg_id = None
        self._user_id = None

    # ---
    # Server Set-Up / Tear-Down
    # ---

    def _set_up_server(self,
                       log_level: log.Level,
                       proc_test: Optional[ProcTest]) -> None:
        if proc_test.has(ProcTest.DNE):
            # Mediator Server 'Does Not Exist' right now.
            self.log_critical("Mediator server set up has {}. "
                              "Skipping creation/set-up.",
                              ProcTest.DNE)
            return

        self.log_debug("Set up mediator server... {}",
                       proc_test)
        name = self.NAME_SERVER
        context = zontext.empty(self,
                                '_set_up_server',
                                UnitTestContext)

        self.proc.server = multiproc.set_up(proc_name=name,
                                            config=self.config,
                                            context=context,
                                            entry_fn=run_server,
                                            initial_log_level=log_level,
                                            debug_flags=self.debug_flags,
                                            unit_testing=True,
                                            proc_test=proc_test)

    def _tear_down_server(self) -> None:
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

    def _set_up_clients(self,
                        log_level: log.Level,
                        proc_test: Optional[ProcTest]) -> None:
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
            context = zontext.empty(self,
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
                                      initial_log_level=log_level,
                                      debug_flags=self.debug_flags,
                                      unit_testing=True,
                                      proc_test=proc_test,
                                      shutdown=shutdown)

            # Save id/key where test can access them.
            client.set_user(user_id, user_key)

            # Append to the list of clients!
            self.proc.clients.append(client)

    def _tear_down_clients(self) -> None:
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

    def client_connect(self, client: ClientProcToSubComm) -> None:
        # Send something... Currently client doesn't care and tries to connect
        # on any message it gets when it has no connection. But it may change
        # later.
        mid = Message.SpecialId.CONNECT
        msg = Message(mid, MsgType.IGNORE,
                      payload=None)
        client.send(msg, self.msg_context(mid))

        # Wait a bit for all the interprocess communicating to happen.
        self.wait(0.5)

        # Received "you're connected now" back?
        recv, ctx = client.recv()

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

    def do_test_ignored_tests(self) -> None:
        self.assertFalse(self.DISABLED_TESTS,
                         "Expected no disabled tests, "
                         f"got: {self.DISABLED_TESTS}")

    # ---
    # Child classes should implement `test_ignored_tests()` so they're in
    # control of what gets run:
    #
    # def test_ignored_tests(self):
    #     self.assert_test_ran(
    #         self.runner_of_test(self.do_test_ignored_tests))
    # ---

    # ------------------------------
    # Test doing nothing and cleaning up.
    # ------------------------------

    def do_test_nothing(self) -> None:
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

    # ---
    # Child classes should implement `test_ignored_tests()` so they're in
    # control of what gets run:
    #
    # def test_nothing(self):
    #     # No checks for this, really. Just "does it properly not explode"?
    #     self.assert_test_ran(
    #         self.runner_of_test(self.do_test_nothing))
    # ---

    # ------------------------------
    # Test Client Requesting Connection to Server.
    # ------------------------------

    def do_test_connect(self, client: ClientProcToSubComm) -> None:
        # Send something... Currently client doesn't care and tries to connect
        # on any message it gets when it has no connection. But it may change
        # later.
        mid = Message.SpecialId.CONNECT
        msg = Message(mid, MsgType.IGNORE,
                      payload=None)
        client.send(msg, self.msg_context(mid))

        # Received "you're connected now" back?
        recv, ctx = client.recv()

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

    # ---
    # Implement if you want to sanity-check the connection part of
    # client/server communication.
    #
    # def test_connect(self):
    #     # self.debugging = True
    #     with log.LoggingManager.on_or_off(self.debugging):
    #         self.assert_test_ran(
    #             self.runner_of_test(self.do_test_connect,
    #                                 *self.proc.clients))
    # ---
