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

# ---
# Type Hinting
# ---
from typing import Optional, Set


# ---
# Python
# ---
import multiprocessing
import multiprocessing.connection


# ---
# Veredi
# ---
from veredi.zest                                import zontext
from veredi.zest.zpath                          import TestType
from veredi.zest.base.multiproc                 import (ZestIntegrateMultiproc,
                                                        Processes,
                                                        ProcTest,
                                                        ClientProcToSubComm)
from veredi.logs                                import (log,
                                                        log_client)
from veredi.debug.const                         import DebugFlag
from veredi.base.context                        import UnitTestContext
from veredi.base.identity                       import (MonotonicId,
                                                        MonotonicIdGenerator)
from veredi.data                                import background
from veredi.data.identity                       import (UserId,
                                                        UserIdGenerator,
                                                        UserKey,
                                                        UserKeyGenerator)
from veredi.parallel                            import multiproc
from veredi.base.context                        import VerediContext
from veredi.data.config.context                 import ConfigContext


# ---
# Mediation
# ---
from veredi.interface.mediator.const            import MsgType
from veredi.interface.user                      import UserPassport
from veredi.interface.mediator.message          import Message
from veredi.interface.mediator.websocket.client import WebSocketClient
from veredi.interface.mediator.context          import MessageContext
from veredi.interface.mediator.system           import MediatorSystem
from veredi.interface.mediator.event            import GameToMediatorEvent

from veredi.interface.output.event              import OutputEvent, Recipient


# ---
# Game
# ---
from veredi.data.exceptions                     import LoadError
from veredi.game.ecs.base.identity              import ComponentId
from veredi.game.ecs.base.entity                import Entity
from veredi.game.ecs.base.system                import System
from veredi.rules.d20.pf2.ability.system        import AbilitySystem
from veredi.rules.d20.pf2.ability.component     import AbilityComponent
from veredi.rules.d20.pf2.health.component      import HealthComponent
from veredi.math.system                         import MathSystem
# from veredi.interface.output.event            import Recipient
from veredi.math.event                          import MathOutputEvent


from veredi.game.data.event                     import (DataLoadedEvent,
                                                        DataLoadRequest)
from veredi.game.data.identity.component        import IdentityComponent
from veredi.data.context                        import (DataGameContext,
                                                        DataLoadContext)
from veredi.game.ecs.base.component             import ComponentLifeCycle

from veredi.math.parser                         import MathTree
from veredi.math.d20                            import tree
from veredi.rules.d20.pf2.game                  import PF2Rank

# ---
# Registry
# ---
from veredi.data.serdes.json                    import serdes
from veredi.rules.d20.pf2.health.component      import HealthComponent
import veredi.interface.mediator.websocket.server
import veredi.interface.mediator.websocket.client
# Should be all our Encodables.
import veredi.data.codec.provide


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

LOG_LEVEL = log.Level.INFO  # DEBUG
'''Test should set this to desired during set_up()'''


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
            TypeError,
            "MediatorClient requires a SubToProcComm; received None.")

    log_level = ConfigContext.log_level(context)
    lumberjack = log.get_logger(comms.name,
                                min_log_level=log_level)
    lumberjack.setLevel(log_level)

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
    # Import Encodables for Registry?
    # ------------------------------
    # TODO: better import?
    import veredi.math.d20.tree

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

        # Was using during debugging, but don't think I need this. Does the
        # log_server need any extra time for anything our other processes sent
        # to it just now?
        # self.wait_on_nothing(0.5)

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

    def sub_events(self) -> None:
        self.manager.event.subscribe(OutputEvent,
                                     self._eventsub_generic_append)
        self.manager.event.subscribe(GameToMediatorEvent,
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
        request = self.data_request(entity.id,
                                    PF2Rank.Phylum.MONSTER,
                                    'Dragon',
                                    'Aluminum Dragon')

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
        self.assertIsNotNone(self.manager.system.get(MathSystem))
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
        event_math = None
        event_mediator = None
        for i in range(max_ticks):
            self.engine_tick()
            ticked += 1

            # Check for the MathOutputEvent and GameToMediatorEvent. Once we
            # get the GameToMediatorEvent we can stop ticking the engine.
            for event in self.events:
                if isinstance(event, MathOutputEvent):
                    event_math = event
                elif isinstance(event, GameToMediatorEvent):
                    event_mediator = event
                    break
            if event_mediator:
                break

        input_history = self.input_system.historian.most_recent(self.entity.id)

        # Client should have received a follow-up from server with results.
        self.assertIsNotNone(input_history)
        self.assertIsNotNone(input_history.status)
        # We should have the MathOutputEvent.
        self.assertIsNotNone(event_math)
        self.assertIsInstance(event_math, MathOutputEvent)
        # We should also have the GameToMediatorEvent.
        self.assertIsNotNone(event_mediator)
        self.assertIsInstance(event_mediator, GameToMediatorEvent)

        # Check that envelope is addressed to our (only) user.
        address = event_mediator.payload.address(Recipient.BROADCAST)
        self.assertEqual(len(address.user_ids), 1)
        for uid in address.user_ids:
            user_list = background.users.connected(uid)
            self.assertIsNotNone(user_list)
            self.assertIsInstance(user_list, list)
            # Should only have one user with this UserId.
            self.assertEqual(len(user_list), 1)
            user = user_list[0]
            self.assertIsNotNone(user)
            self.assertIsInstance(user, UserPassport)
            self.assertEqual(user.id, client.user_id)
            self.assertEqual(user.key, client.user_key)
            self.assertEqual(event_mediator.id, self.entity.id)

        # We have the GameToMediatorEvent, which means MediatorSystem has
        # gotten it to (hopefully), and sent something to MediatorServer
        # (hopefully). Wait a bit for MediatorServer to do stuff in its
        # process.
        self.wait(0.5)
        self.assertTrue(client.has_data())

        # Get the message from the client.
        recv, ctx = client.recv()

        # Check message recived.
        self.assertTrue(recv)
        self.assertIsInstance(recv, Message)

        # Does the context look ok?
        self.assertTrue(ctx)
        self.assertTrue(ctx, MessageContext)

        # Do the Message IDs look right?
        self.assertIsNotNone(mid)
        self.assertIsInstance(mid, MonotonicId)
        # TODO [2020-11-08]: FIX MONOTONIC ID INVALID. It is mid:001 right here.
        # log.ultra_hyper_debug(f"mid: {mid}\ninv: {MonotonicId.INVALID}")
        # self.assertNotEqual(mid, MonotonicId.INVALID)
        self.assertIsNotNone(msg.msg_id)
        self.assertIsInstance(msg.msg_id, MonotonicId)
        # self.assertNotEqual(msg.msg_id, MonotonicId.INVALID)

        # Currently context doesn't have message id. Think it's ok?
        # self.assertEqual(msg.msg_id, ctx.id)

        # Does the Message type look right?
        self.assertEqual(recv.type, MsgType.ENCODED)

        # We sent text, but we want back a message type for a math tree result.
        # So they should not be equal.
        self.assertNotEqual(msg.type, recv.type)

        # Does the message payload look right?
        # Should be a MathTree. Should be an Add at the root.
        self.assertIsInstance(recv.payload, MathTree)
        self.assertIsInstance(recv.payload, tree.OperatorAdd)
        self.assertIsNotNone(recv.payload.children)
        self.assertEqual(len(recv.payload.children), 2)
        self.assertIsInstance(recv.payload.children[0], tree.Variable)
        self.assertIsInstance(recv.payload.children[1], tree.Constant)

        self.assertEqual(recv.payload.value, 34)

        # Server should get an ACK...
        mediator_system = self.manager.system.get(MediatorSystem)
        self.assertTrue(mediator_system.server.has_data())
        server_recv, server_ctx = mediator_system.server.recv()
        self.assertTrue(server_recv)
        self.assertTrue(server_ctx)
        self.assertEqual(server_recv.type, MsgType.ACK_ID)

        # Make sure we don't have anything in the queues.
        self.assert_empty_pipes()

    def test_ability_cmd(self):
        if self.disabled():
            return

        self.assert_test_ran(
            self.runner_of_test(self.do_test_ability_cmd, *self.proc.clients))


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.zest.functional.communication.zest_websocket_and_cmds

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
