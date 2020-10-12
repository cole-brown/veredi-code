# coding: utf-8

'''
Functional Test for a client talking to a server:
  - Client:
    - Connecting.
    - Message server requesting a command.
  - Server:
    - Receiving command request.
    - Send command to game.
  - Game:
    - InputSystem:
      - Receive input command.
      - Process command.
    - Engine / Game Systems:
      - Process / complete command.
      - Initiate output.
    - OutputSystem.
      - Receive output.
      - Process output, send to Server.
  - Server:
    - Receive output message from Game.
    - Process, send to (correct) client.
  - Client:
    - Receive output message.
    - Verify.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Set

import multiprocessing
import multiprocessing.connection

from veredi.zest                                import zontext
from veredi.zest.zpath                          import TestType
from veredi.zest.base.multiproc                 import (ZestIntegrateMultiproc,
                                                        Processes,
                                                        ProcTest,
                                                        ClientProcToSubComm)
from veredi.logger                              import (log,
                                                        log_client)
from veredi.debug.const                         import DebugFlag
from veredi.base.identity                       import (MonotonicId,
                                                        MonotonicIdGenerator)
from veredi.data.identity                       import (UserId,
                                                        UserIdGenerator,
                                                        UserKey,
                                                        UserKeyGenerator)
from veredi.parallel                            import multiproc
from veredi.base.context         import VerediContext
from veredi.data.config.context         import ConfigContext


# ---
# Need these to register...
# ---
from veredi.data.codec.json                     import codec


# ---
# Mediation
# ---
from veredi.interface.mediator.message          import Message, MsgType
from veredi.interface.mediator.websocket.server import WebSocketServer
from veredi.interface.mediator.websocket.client import WebSocketClient
from veredi.interface.mediator.context          import MessageContext
from veredi.interface.mediator.payload.logging  import (LogPayload,
                                                        LogReply,
                                                        LogField,
                                                        _NC_LEVEL)
from veredi.interface.mediator.system import MediatorSystem

from veredi.interface.output.event          import OutputEvent


# ---
# Game
# ---
from veredi.data.exceptions              import LoadError
from veredi.game.ecs.base.identity       import ComponentId
from veredi.game.ecs.base.entity    import Entity
from veredi.game.ecs.base.system    import System
from veredi.rules.d20.pf2.ability.system                             import AbilitySystem
from veredi.rules.d20.pf2.ability.event                              import AbilityRequest, AbilityResult
from veredi.rules.d20.pf2.ability.component                          import AbilityComponent
from veredi.rules.d20.pf2.health.component import HealthComponent

from veredi.game.data.event              import (DataLoadedEvent,
                                                 DataLoadRequest)
from veredi.game.data.identity.system    import IdentitySystem
from veredi.game.data.identity.component import IdentityComponent
from veredi.game.data.identity.event     import CodeIdentityRequest
from veredi.base.context                 import UnitTestContext
from veredi.data.context                 import (DataGameContext,
                                                 DataLoadContext)
from veredi.game.ecs.base.component      import ComponentLifeCycle

# ---
# Registry
# ---
from veredi.rules.d20.pf2.health.component  import HealthComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

LOG_LEVEL = log.Level.INFO  # DEBUG
'''Test should set this to desired during setUp()'''


# -----------------------------------------------------------------------------
# Multiprocessing Runners
# -----------------------------------------------------------------------------

# ------------------------------
# MediatorServer
# ------------------------------

# MediatorServer is managed by MediatorSystem.


# ------------------------------
# MediatorClient
# ------------------------------

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
            "MediatorClient requires a SubToProcComm; received None.")

    log_level = ConfigContext.log_level(context)
    lumberjack = log.get_logger(comms.name,
                                min_log_level=log_level)
    lumberjack.setLevel(log_level)

    multiproc._sigint_ignore()
    log_client.init(log_level)

    # ------------------------------
    # Sanity Check
    # ------------------------------
    # It's a test - and the first multiprocess test - so... don't assume the
    # basics.
    if not comms.pipe:
        raise log.exception(
            "MediatorClient requires a pipe connection; received None.",
            veredi_logger=lumberjack)
    if not comms.config:
        raise log.exception(
            "MediatorClient requires a configuration; received None.",
            veredi_logger=lumberjack)
    if not log_level:
        raise log.exception(
            "MediatorClient requires a default log level (int); "
            "received None.",
            veredi_logger=lumberjack)
    if not comms.shutdown:
        raise log.exception(
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
    log_client.close()
    lumberjack.debug(f"MediatorClient '{comms.name}' done.")


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_Functional_WebSockets_Commands(ZestIntegrateMultiproc):
    _TEST_TYPE = TestType.FUNCTIONAL

    # TODO [2020-09-09]: 2 or 4 or something?
    NUM_CLIENTS = 1

    NAME_LOG = 'veredi.test.websockets.log'
    NAME_CLIENT_FMT = 'veredi.test.websockets.client.{i:02d}'
    NAME_MAIN = 'veredi.test.websockets.tester'
    # Technically we're:
    #   "veredi.zest.functional.communication.zest_websocket_and_cmds"
    # ...but that's really long, so just 'veredi.test.<whatever>'.

    # -------------------------------------------------------------------------
    # Set-Up & Tear-Down
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        More vars!
        '''
        super()._define_vars()

        self._msg_id: MonotonicIdGenerator = MonotonicId.generator()
        '''ID generator for creating Mediator messages.'''

        self._user_id: UserIdGenerator = UserId.generator()
        '''For these, just make up user ids.'''

        self._required_systems: Set[System] = set({
            # InputSystem:  Covered by ZestIntegrateEngine.set_up()
            # OutputSystem: Covered by ZestIntegrateEngine.set_up()
            AbilitySystem,
            IdentitySystem,
            MediatorSystem,
        })
        '''Extra systems we need to fill in this game's systems.'''

        self.entity: Entity = None
        '''Entity for to test with.'''

    def set_up(self):
        # Want MEDIATOR_ALL for mediators and GAME_ALL for engine?
        # Which == SPAM.
        self.debug_flags = DebugFlag.SPAM
        self.DISABLED_TESTS = set({
            # Nothing, ideally.

            # TODO [2020-09-09]: Names of these tests.

            # ---
            # This is cheating.
            # ---
            # 'test_ignored_tests',

            # ---
            # Simplest test.
            # ---
            # 'test_nothing',
            # 'test_logs_ignore',

            # ---
            # More complex tests.
            # ---
            # 'test_connect',
            # 'test_ping',
            # 'test_echo',
            # 'test_text',
            # 'test_logging',
        })

        # ---
        # Parent Stuff (Log Server, Engine, etc)
        # ---
        default_flags = ProcTest.NONE
        super().set_up('config.websocket.yaml', LOG_LEVEL, default_flags)

        # ---
        # Commands / Events / Game
        # ---
        self._set_up_game()

        # ---
        # Client / Server
        # ---
        self._set_up_clients(self.config, default_flags)  # ProcTest.DNE)

    def tear_down(self):
        # ---
        # Goodbye Game.
        # ---
        # MediatorSystem is responsible for stopping the MediatorServer and
        # should do so in here.
        self._tear_down_game()

        # ---
        # Our tear down.
        # ---
        self._tear_down_clients()
        # MediatorSystem is responsible for any MediatorServer tear-down too.

        # And now hand over to parent for tear_down of log proc & whatever else
        # it does.
        super().tear_down(LOG_LEVEL)

        self._msg_id = None
        self._user_id = None

    # ---
    # Game Set-Up / Tear-Down
    # ---

    def _set_up_game(self):
        self.start_engine_events_systems_etc()

        self.entity = self.create_entity(clear_events=True)

    def _tear_down_game(self):
        self.engine_life_end()

        self.entity = None

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
            context = zontext.empty(self.__class__.__name__,
                                    f"_set_up_clients('{name}')")

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

    def sub_events(self) -> None:
        self.manager.event.subscribe(OutputEvent,
                                     self._eventsub_generic_append)

    def msg_context(self,
                    msg_ctx_id: Optional[MonotonicId] = None
                    ) -> MessageContext:
        '''
        Some simple context to pass with messages.

        Makes up an id if none supplied.
        '''
        msg_id = msg_ctx_id or MonotonicId(7731, allow=True)
        ctx = MessageContext(
            'veredi.zest.integration.communication.zest_websocket_and_cmds',
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
                      payload=None,
                      user_id=client.user_id,
                      user_key=client.user_key)
        client.pipe.send((msg, self.msg_context(mid)))

        # Received "you're connected now" back?
        recv, ctx = client.pipe.recv()

        # We have a whole test to make sure this goes right, so just
        # sanity checks.
        self.assertTrue(recv)
        self.assertIsInstance(recv, Message)
        self.assertIsInstance(recv.msg_id, Message.SpecialId)
        self.assertEqual(recv.type, MsgType.ACK_CONNECT)
        self.assertIsNotNone(recv.user_id)

        self.assert_empty_pipes()

        # Hook the client up to an entity.
        log.ultra_mega_debug("uid: {}, ukey: {}", client.user_id, client.user_key)
        self.entity_ident.user_id  = client.user_id
        self.entity_ident.user_key = client.user_key
        self.assertTrue(self.entity_ident.user_id)
        self.assertEqual(self.entity_ident.user_id, client.user_id)
        # self.assertTrue(self.entity_ident.user_key)
        self.assertEqual(self.entity_ident.user_key, client.user_key)

    def create_entity(self, clear_events=True) -> Entity:
        '''
        Creates entity by:
          - Having parent create_entity()
          - Calling identity() to create/attach IdentityComponent.
          - Calling load() to create/attach our AbilityComponent.
          - Clearing events (if flagged to do so).

          - Returning entity.
        '''
        entity = super().create_entity()
        self.assertTrue(entity)

        # Create and attach components.
        self.entity_ident = self._load_entity_data(entity,
                                                   clear_events=clear_events)
        self.assertTrue(self.entity_ident)

        # Throw away loading events.
        if clear_events:
            self.clear_events()

        return entity

    def _load_entity_data(self,
                          entity,
                          clear_events=True) -> IdentityComponent:
        # Make the load request event for our entity.
        request = self._load_request(entity.id,
                                     DataGameContext.DataType.MONSTER)
        self.assertFalse(self.events)

        # Ask for our Ability Guy data to be loaded. Don't care about asserting
        # anything, so use _event_now instead of trigger_events.
        self._event_now(request)

        expected_comps = {IdentityComponent, AbilityComponent, HealthComponent}
        entity_ident = None
        for event in self.events:
            # Attach the loaded component to our entity.
            self.assertIsInstance(event, DataLoadedEvent)
            cid = event.component_id
            self.assertNotEqual(cid, ComponentId.INVALID)
            component = self.manager.component.get(cid)
            self.assertIsNotNone(component)
            self.assertIn(type(component), expected_comps)
            if isinstance(component, IdentityComponent):
                entity_ident = component

            self.manager.entity.attach(entity.id, component)
            component._life_cycle = ComponentLifeCycle.ALIVE
            # Make sure component got attached to entity.
            self.assertIn(type(component), entity)

        if clear_events:
            self.clear_events()
        return entity_ident

    def _load_request(self, entity_id, type):
        ctx = DataLoadContext('unit-testing',
                              type,
                              'test-campaign')
        if type == DataGameContext.DataType.MONSTER:
            ctx.sub['family'] = 'dragon'
            ctx.sub['monster'] = 'aluminum dragon'
        else:
            raise LoadError(
                f"No DataGameContext.DataType to ID conversion for: {type}",
                None,
                ctx)

        event = DataLoadRequest(
            id,
            ctx.type,
            ctx)

        return event

    def client_send_with_ack(self, client, mid, msg):
        # Send out message from client that expects ack.
        client.pipe.send((msg, self.msg_context(mid)))

        # Get ack back from server.
        ack, ctx = client.pipe.recv()

        # ---
        # Is a test; check things.
        # ---

        # Got non-nulls.
        self.assertTrue(ack)
        self.assertTrue(ctx)

        # Got expected object types.
        self.assertIsInstance(ack, Message)
        self.assertTrue(ctx, MessageContext)

        # Message ID is intact.
        self.assertEqual(mid, ack.msg_id)
        self.assertEqual(msg.msg_id, ack.msg_id)

        # Received the ACK we expected.
        self.assertEqual(ack.type, MsgType.ACK_ID)

        # Return the ack. Don't need the context for anything atm.
        return ack

    # =========================================================================
    # =--------------------------------Tests----------------------------------=
    # =--                        Real Actual Tests                          --=
    # =---------------------...after so much prep work.-----------------------=
    # =========================================================================

    # ------------------------------
    # Check to see if we're blatently ignoring anything...
    # ------------------------------

    # def test_ignored_tests(self):
    #     self.assertFalse(self.DISABLED_TESTS,
    #                      "Expected no disabled tests, "
    #                      f"got: {self.DISABLED_TESTS}")

    # ------------------------------
    # Test doing nothing and cleaning up.
    # ------------------------------

    def do_test_nothing(self):
        self.assertIsInstance(self.proc, Processes)
        # We do not have a server. MediatorSystem does.
        self.assertIsNone(self.proc.server)
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
        self.assertIsNotNone(self.entity)
        self.assertIsNotNone(self.entity_ident)
        self.assertIsNotNone(self.input_system)
        self.assertIsNotNone(self.output_system)
        self.assertIsNotNone(self.manager.system.get(AbilitySystem))
        # No checks for this, really. Just "does it properly not explode"?
        self.assert_test_ran(
            self.runner_of_test(self.do_test_nothing))

    # ------------------------------
    # Test that our systems exist.
    # ------------------------------

    def do_test_ability_cmd(self, client):
        # Get the connect out of the way.
        self.client_connect(client)

        cmd_str = "/ability $strength.score + 4"
        '''AbilitySystem math command.'''

        # Make a message with our command in it and send on up.
        mid = self._msg_id.next()
        msg = Message(mid, MsgType.TEXT,
                      payload=cmd_str,
                      user_id=client.user_id,
                      user_key=client.user_key)
        self.client_send_with_ack(client, mid, msg)

        # Game should process events set off by the message...
        max_ticks = 20
        ticked = 0
        output_event = None
        for i in range(max_ticks):
            self.engine_tick()
            ticked += 1
            for event in self.events:
                if type(event) is OutputEvent:
                    # Cut out early if we got the output event. Give extra
                    # ticks to process the output event in next step, not here,
                    # if needed.
                    output_event = event
                    break

        input_history = self.input_system.historian.most_recent(self.entity.id)

        # Client should have received a follow-up from server with results.
        self.assertIsNotNone(input_history)
        self.assertIsNotNone(input_history.status)
        self.assertIsNotNone(output_event)
        self.assertTrue(client.has_data())

        # Make sure we don't have anything in the queues.
        self.assert_empty_pipes()

    def test_ability_cmd(self):
        if self.disabled():
            return

        self.assert_test_ran(
            self.runner_of_test(self.do_test_ability_cmd, *self.proc.clients))

    # # ------------------------------
    # # Test cliets pinging server.
    # # ------------------------------

    # def do_test_ping(self, client):
    #     # Get the connect out of the way.
    #     self.client_connect(client)

    #     mid = self._msg_id.next()
    #     msg = Message(mid, MsgType.PING,
    #                   payload=None,
    #                   user_id=client.user_id,
    #                   user_key=client.user_key)
    #     client.pipe.send((msg, self.msg_context(mid)))
    #     recv, ctx = client.pipe.recv()
    #     # Make sure we got a message back and it has the ping time in it.
    #     self.assertTrue(recv)
    #     self.assertTrue(ctx)
    #     self.assertIsInstance(recv, Message)
    #     self.assertTrue(ctx, MessageContext)
    #     self.assertEqual(msg.msg_id, ctx.id)
    #     self.assertEqual(mid, recv.msg_id)
    #     self.assertEqual(msg.msg_id, recv.msg_id)
    #     self.assertEqual(msg.type, recv.type)

    #     # I really hope the local ping is between negative nothingish and
    #     # positive five seconds.
    #     self.assertIsInstance(recv.payload, float)
    #     self.assertGreater(recv.payload, -0.0000001)
    #     self.assertLess(recv.payload, 5)

    #     # Make sure we don't have anything in the queues...
    #     self.assert_empty_pipes()

    # def test_simple(self):
    #     # No other checks for ping outside do_test_ping.
    #     self.assert_test_ran(
    #         self.runner_of_test(self.do_test_ping, *self.proc.clients))

    # # ------------------------------
    # # Test Clients sending an echo message.
    # # ------------------------------

    # def do_test_echo(self, client):
    #     # Get the connect out of the way.
    #     self.client_connect(client)

    #     mid = self._msg_id.next()
    #     send_msg = f"Hello from {client.name}"
    #     expected = send_msg
    #     msg = Message(mid, MsgType.ECHO,
    #                   payload=send_msg,
    #                   user_id=client.user_id,
    #                   user_key=client.user_key)
    #     ctx = self.msg_context(mid)
    #     # self.debugging = True
    #     with log.LoggingManager.on_or_off(self.debugging, True):
    #         client.pipe.send((msg, ctx))
    #         recv, ctx = client.pipe.recv()
    #     # Make sure we got a message back and it has the same
    #     # message as we sent.
    #     self.assertTrue(recv)
    #     self.assertTrue(ctx)
    #     self.assertIsInstance(recv, Message)
    #     self.assertTrue(ctx, MessageContext)
    #     # IDs made it around intact.
    #     self.assertEqual(msg.msg_id, ctx.id)
    #     self.assertEqual(mid, recv.msg_id)
    #     self.assertEqual(msg.msg_id, recv.msg_id)
    #     # Sent echo, got echo-back.
    #     self.assertEqual(msg.type, MsgType.ECHO)
    #     self.assertEqual(recv.type, MsgType.ECHO_ECHO)
    #     # Got what we sent.
    #     self.assertIsInstance(recv.payload, str)
    #     self.assertEqual(recv.payload, expected)

    #     # Make sure we don't have anything in the queues...
    #     self.assert_empty_pipes()

    # def test_echo(self):
    #     self.assert_test_ran(
    #         self.runner_of_test(self.do_test_echo, *self.proc.clients))

    # # ------------------------------
    # # Test Clients sending text messages to server.
    # # ------------------------------

    # def do_test_text(self, client):
    #     # Get the connect out of the way.
    #     self.client_connect(client)

    #     mid = self._msg_id.next()

    #     # ---
    #     # Client -> Server: TEXT
    #     # ---
    #     self.log_debug("client to server...")

    #     send_txt = f"Hello from {client.name}?"
    #     client_send = Message(mid, MsgType.TEXT,
    #                           payload=send_txt,
    #                           user_id=client.user_id,
    #                           user_key=client.user_key)
    #     client_send_ctx = self.msg_context(mid)

    #     client_recv_msg = None
    #     client_recv_ctx = None
    #     with log.LoggingManager.on_or_off(self.debugging, True):
    #         # Have client send, then receive from server.
    #         client.pipe.send((client_send, client_send_ctx))

    #         # Server automatically sent an ACK_ID, need to check client.
    #         client_recv_msg, client_recv_ctx = client.pipe.recv()

    #     self.log_debug("client send msg: {}", client_send)
    #     # Why is this dying when trying to print its payload?!
    #     # # self.log_ultra_mega_debug(
    #     # #     "client_recv msg: {client_recv_msg._payload}")
    #     # ...
    #     # ...Huh... f-strings and veredi.logger and multiprocessor or
    #     # log_server or something don't like each other somewhere along
    #     # the way? This is a-ok:
    #     self.log_debug("client_recv msg: {}", client_recv_msg._payload)

    #     # Make sure that the client received the correct thing.
    #     self.assertIsNotNone(client_recv_msg)
    #     self.assertIsInstance(client_recv_msg, Message)
    #     self.assertIsNotNone(client_recv_ctx)
    #     self.assertIsInstance(client_recv_ctx, MessageContext)
    #     self.assertEqual(mid, client_recv_msg.msg_id)
    #     self.assertEqual(client_send.msg_id, client_recv_msg.msg_id)
    #     self.assertEqual(client_recv_msg.type, MsgType.ACK_ID)
    #     ack_id = mid.decode(client_recv_msg.payload)
    #     self.assertIsInstance(ack_id, type(mid))

    #     # ---
    #     # Check: Client -> Server: TEXT
    #     # ---
    #     self.log_debug("test_text: server to game...")
    #     server_recv_msg = None
    #     server_recv_ctx = None
    #     with log.LoggingManager.on_or_off(self.debugging, True):
    #         # Our server should have put the client's packet in its pipe for
    #         # us... I hope.
    #         self.log_debug("test_text: game recv from server...")
    #         server_recv_msg, server_recv_ctx = self.proc.server.pipe.recv()

    #     self.log_debug("client_sent/server_recv: {}", server_recv_msg)
    #     # Make sure that the server received the correct thing.
    #     self.assertEqual(mid, server_recv_msg.msg_id)
    #     self.assertEqual(client_send.msg_id, server_recv_msg.msg_id)
    #     self.assertEqual(client_send.type, server_recv_msg.type)
    #     self.assertIsInstance(server_recv_msg.payload, str)
    #     self.assertEqual(server_recv_msg.payload, send_txt)
    #     # Check the Context.
    #     self.assertIsInstance(server_recv_ctx, MessageContext)
    #     self.assertEqual(server_recv_ctx.id, ack_id)

    #     # ---
    #     # Server -> Client: TEXT
    #     # ---

    #     self.log_debug("test_text: server_send/client_recv...")
    #     # Tell our server to send a reply to the client's text.
    #     recv_txt = f"Hello from {self.proc.server.name}!"
    #     server_send = Message(server_recv_ctx.id, MsgType.TEXT,
    #                           payload=recv_txt,
    #                           user_id=client.user_id,
    #                           user_key=client.user_key)

    #     client_recv_msg = None
    #     client_recv_ctx = None
    #     with log.LoggingManager.on_or_off(self.debugging, True):
    #         # Make something for server to send and client to recvive.
    #         self.log_debug("test_text: server_send...")
    #         self.log_debug("test_text: pipe to game: {}", server_send)
    #         self.proc.server.pipe.send((server_send, server_recv_ctx))
    #         self.log_debug("test_text: client_recv...")
    #         client_recv_msg, client_recv_ctx = client.pipe.recv()

    #     self.log_debug("server_sent/client_recv: {}", client_recv_msg)
    #     self.assertIsNotNone(client_recv_ctx)
    #     self.assertIsInstance(client_recv_ctx, MessageContext)

    #     self.assertIsInstance(client_recv_msg, Message)
    #     self.assertEqual(ack_id, client_recv_msg.msg_id)
    #     self.assertEqual(server_send.msg_id, client_recv_msg.msg_id)
    #     self.assertEqual(server_send.type, client_recv_msg.type)
    #     self.assertIsInstance(client_recv_msg.payload, str)
    #     self.assertEqual(client_recv_msg.payload, recv_txt)

    #     # ---
    #     # Server -> Client: ACK
    #     # ---

    #     # Client automatically sent an ACK_ID, need to check server for it.
    #     server_recv = self.proc.server.pipe.recv()

    #     self.log_debug("server sent msg: {}", server_send)
    #     self.log_debug("server recv ack: {}", server_recv)
    #     # Make sure that the server received the correct thing.
    #     self.assertIsNotNone(server_recv)
    #     self.assertIsInstance(server_recv, tuple)
    #     self.assertEqual(len(server_recv), 2)  # Make sure next line is sane...
    #     server_recv_msg, server_recv_ctx = server_recv
    #     # Make sure that the server received their ACK_ID.
    #     self.assertIsNotNone(server_recv_msg)
    #     self.assertIsInstance(server_recv_msg, Message)
    #     self.assertIsNotNone(server_recv_ctx)
    #     self.assertIsInstance(server_recv_ctx, MessageContext)
    #     self.assertEqual(mid, server_recv_msg.msg_id)
    #     self.assertEqual(server_send.msg_id, server_recv_msg.msg_id)
    #     self.assertEqual(server_recv_msg.type, MsgType.ACK_ID)
    #     ack_id = mid.decode(server_recv_msg.payload)
    #     self.assertIsInstance(ack_id, type(mid))

    #     # Make sure we don't have anything in the queues...
    #     self.assert_empty_pipes()

    # def test_text(self):
    #     self.assert_test_ran(
    #         self.runner_of_test(self.do_test_text, *self.proc.clients))

    # # -------------------------------------------------------------------------
    # # -------------------------------------------------------------------------
    # # This is brittle - it can cause whatever runs next to get stuck in some
    # # weird infinite loop of runner_of_test() calls.
    # #
    # # Since this is now eclipsed by test_logging(), which also checks ignoring
    # # logs, I'm just commenting it out.
    # #
    # # Next person (me) to come along should put it out of its misery.
    # #
    # # # ------------------------------
    # # # Test Ignoring Logs...
    # # # ------------------------------
    # #
    # # def do_test_logs_ignore(self):
    # #     self.assertIsNotNone(self.proc.log)
    # #
    # #     self.assertEqual(self.proc.log.ignored_counter.value, 0)
    # #
    # #     self.proc.log.ignore_logs.set()
    # #
    # #     # Does this not get printed and does this increment our counter?
    # #     self.assertEqual(self.proc.log.ignored_counter.value, 0)
    # #
    # #     # Connect this process to the log server, do a long that should be
    # #     # ignored, and then disconnect.
    # #     log_client.init()
    # #     self.log_critical("You should not see this.")
    # #     log_client.close()
    # #     # Gotta wait a bit for the counter to sync back to this process,
    # #     # I guess.
    # #     self.wait(1)  # 0.1)
    # #     self.assertEqual(self.proc.log.ignored_counter.value, 1)
    # #
    # # def test_logs_ignore(self):
    # #     self.assert_test_ran(
    # #         self.runner_of_test(self.do_test_logs_ignore))
    # # -------------------------------------------------------------------------
    # # -------------------------------------------------------------------------

    # # ------------------------------
    # # Test Server sending LOGGING to client.
    # # ------------------------------

    # def _check_ignored_counter(self,
    #                            assert_eq_value=None,
    #                            assert_gt_value=None):
    #     # Check counter if asked.
    #     if assert_eq_value is not None:
    #         self.assertEqual(self.proc.log.ignored_counter.value,
    #                          assert_eq_value)

    #     if assert_gt_value is not None:
    #         self.assertGreater(self.proc.log.ignored_counter.value,
    #                            assert_gt_value)

    # def ignore_logging(self,
    #                    enable,
    #                    assert_eq_value=None,
    #                    assert_gt_value=None):
    #     '''
    #     Instruct log_server to start or stop ignoring log messages. Will
    #     assertEqual() or assertGreater() on the ignored_counter if those values
    #     are not None.

    #     `enable` should be:
    #       - True or False to toggle. Asserts before and after values.
    #       - None to leave alone.
    #     '''
    #     if enable is True:
    #         # Sanity check.
    #         self.assertFalse(self.proc.log.ignore_logs.is_set())
    #         was = self.proc.log.ignore_logs.is_set()

    #         # Check counter if asked.
    #         self._check_ignored_counter(assert_eq_value, assert_gt_value)

    #         # Start ignoring logs.
    #         self.proc.log.ignore_logs.set()

    #         # print('\n\n'
    #         #       + ('-=' * 40) + '-\n'
    #         #       + '<logging="IGNORE"'
    #         #       + f'was="{was}" '
    #         #       + f'set="{self.proc.log.ignore_logs.is_set()}" '
    #         #       + f'count="{self.proc.log.ignored_counter.value}>'
    #         #       + '\n'
    #         #       + ('-=' * 40) + '-'
    #         #       '\n\n')
    #         self.log_debug('\n\n'
    #                        + ('-=' * 40) + '-\n'
    #                        + '<logging="IGNORE"'
    #                        + f'was="{was}" '
    #                        + f'set="{self.proc.log.ignore_logs.is_set()}" '
    #                        + f'count="{self.proc.log.ignored_counter.value}>'
    #                        + '\n'
    #                        + ('-=' * 40) + '-'
    #                        '\n\n')

    #     elif enable is False:
    #         # Sanity check.
    #         self.assertTrue(self.proc.log.ignore_logs.is_set())

    #         # Stop ignoring logs.
    #         was = self.proc.log.ignore_logs.is_set()
    #         self.proc.log.ignore_logs.clear()

    #         # print('\n\n'
    #         #       + ('-=' * 40) + '-\n'
    #         #       + '</logging="IGNORE" '
    #         #       + f'was="{was}" '
    #         #       + f'set="{self.proc.log.ignore_logs.is_set()}" '
    #         #       + f'count="{self.proc.log.ignored_counter.value}>'
    #         #       + '\n'
    #         #       + ('-=' * 40) + '-'
    #         #       '\n\n')
    #         self.log_debug('\n\n'
    #                        + ('-=' * 40) + '-\n'
    #                        + '</logging="IGNORE" '
    #                        + f'was="{was}" '
    #                        + f'set="{self.proc.log.ignore_logs.is_set()}" '
    #                        + f'count="{self.proc.log.ignored_counter.value}>'
    #                        + '\n'
    #                        + ('-=' * 40) + '-'
    #                        '\n\n')

    #         # Check counter if asked.
    #         self._check_ignored_counter(assert_eq_value, assert_gt_value)

    #     elif enable is None:
    #         # Check counter if asked.
    #         self._check_ignored_counter(assert_eq_value, assert_gt_value)

    #     # Um... what?
    #     else:
    #         self.fail(f'enabled must be True/False/None. Got: {enable}')

    #     # Wait a bit so flag propogates to log_server? Maybe? Why isn't
    #     # this working?
    #     # It wasn't working because a LogRecordSocketReceiver's 'request' is a
    #     # whole client, actually, whereas I thought it was a log record.
    #     self.wait(0.1)

    # def do_test_logging(self, client):
    #     # Get the connect out of the way.
    #     self.client_connect(client)

    #     # Start ignoring logs.
    #     self.ignore_logging(True, assert_eq_value=0)

    #     # Have a client adjust its log level to debug. Should spit out a lot of
    #     # logs then.
    #     payload = LogPayload()
    #     payload.request_level(log.Level.DEBUG)

    #     mid = self._msg_id.next()
    #     send_msg = Message.log(mid,
    #                            client.user_id, client.user_key,
    #                            payload)

    #     send_ctx = self.msg_context(mid)
    #     # server -> client
    #     self.proc.server.pipe.send((send_msg, send_ctx))
    #     # Server should have put client's reply into the unit test pipe so we
    #     # can check it.
    #     ut_msg = self.proc.server.ut_pipe.recv()

    #     # Make sure we got a LOGGING message reply back.
    #     self.assertTrue(ut_msg)
    #     self.assertIsInstance(ut_msg, Message)
    #     # Sent logging... right?
    #     self.assertEqual(send_msg.type, MsgType.LOGGING)
    #     # Got logging... right?
    #     self.assertEqual(ut_msg.type, MsgType.LOGGING)

    #     # Got logging response?
    #     self.assertIsInstance(ut_msg.payload, LogPayload)
    #     report = ut_msg.payload.report
    #     self.assertIsNotNone(report)
    #     level = report[LogField.LEVEL]

    #     # Got reply for our level request?
    #     self.assertIsInstance(level, LogReply)
    #     self.assertEqual(level.valid, LogReply.Valid.VALID)

    #     # Got /valid/ reply?
    #     self.assertTrue(LogReply.validity(level.value, _NC_LEVEL),
    #                     LogReply.Valid.VALID)

    #     # Client reports they're now at the level we requested?
    #     self.assertEqual(level.value, log.Level.DEBUG)

    #     # Client should have push into the ut_pipe too.
    #     # Don't really care, at the moment, but we do care to
    #     # assert_empty_pipes() for other reasons so get this one out.
    #     ut_msg_client = client.ut_pipe.recv()
    #     self.assertTrue(ut_msg_client)
    #     self.assertIsInstance(ut_msg_client, Message)
    #     self.assertEqual(ut_msg_client.type, MsgType.LOGGING)

    #     self.wait(0.1)
    #     # Stop ignoring logs and make sure we ignored something, at least,
    #     # right? Well... either have to tell client to go back to previous
    #     # logging level or we have to keep ignoring. Clean-up / tear-down has
    #     # logs too.
    #     self.ignore_logging(None, assert_gt_value=2)

    #     # Make sure we don't have anything in the queues...
    #     self.assert_empty_pipes()

    # def test_logging(self):
    #     self.assert_test_ran(
    #         self.runner_of_test(self.do_test_logging, *self.proc.clients))


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.zest.functional.communication.zest_websocket_and_cmds

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
