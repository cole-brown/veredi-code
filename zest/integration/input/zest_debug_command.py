# coding: utf-8

'''
Integration Test for:
  - Engine running systems through start up steps.
    - This causing command registration.
  - input -> command -> command invokee -> debug command.

Make engine from config data, run it through its startup steps/ticks.
  - Check that this caused registration broadcast.
    - Check that this caused our command(s) to register.

Test debug command(s).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import sys

from ..integrate import IntegrationTest

from veredi.base.null import Null
from veredi.logger import log
from veredi.game.ecs.const import DebugFlag
from veredi.base.context import UnitTestContext
from veredi.data.context                import DataGameContext, DataLoadContext
from veredi.data.exceptions             import LoadError

from veredi.game.engine      import Engine, EngineLifeCycle
from veredi.game.ecs.base.identity      import ComponentId

from veredi.game.data.event             import DataLoadRequest, DataLoadedEvent

from veredi.input.system import InputSystem
from veredi.input.event                              import CommandInputEvent
from veredi.game.data.identity.system import IdentitySystem

# import veredi.zest.debug.debug
import veredi.zest.debug.background
# import veredi.data.background


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_EngineStart_DebugCmds(IntegrationTest):

    # ---
    # Set-Up & Tear-Down
    # --
    # Leaving here even if only calling super(). So I remember about them
    # when next I stumble in here.
    # ---

    def setUp(self):
        super().setUp()

        self.debug_flags = DebugFlag.UNIT_TESTS
        self.init_required(True)
        self.init_input()
        self.init_many_systems(IdentitySystem)
        # self.whatever = self.init_a_system(...)
        self._logs = []

        # Stupid hack to get at verbosity since unittest doesn't provide it
        # anywhere. :(
        self._ut_is_verbose = ('-v' in sys.argv) or ('--verbose' in sys.argv)

    def tearDown(self):
        super().tearDown()
        self._logs = None
        # Just in case anyone forgot to do this when they're done.
        log.ut_tear_down()

    def apoptosis(self):
        super().apoptosis()

    # ---
    # Events
    # ---

    # No result event... yet.

    # def _sub_events_test(self) -> None:
    #     self.sub_loaded()
    #     self.manager.event.subscribe(SkillResult, self.event_skill_res)

    # def event_skill_res(self, event):
    #     self.events.append(event)

    # ---
    # Engine
    # ---
    def _engine_start(self):
        # Not life'd or registration'd yet.
        self.assertEqual(self.engine.life_cycle, EngineLifeCycle.INVALID)
        self.assertFalse(self.reg_open)

        # Run create ticks.
        self.engine._run_create()

        # Life'd, registration'd, and some commands exist now.
        self.assertEqual(self.engine.life_cycle, EngineLifeCycle.CREATING)
        self.assertTrue(self.reg_open)
        self.assertTrue(self.input_system._commander._commands)


    # -------------------------------------------------------------------------
    # Log Capture
    # -------------------------------------------------------------------------

    def receive_log(self,
                    level: log.Level,
                    output: str) -> None:
        '''
        Callback for log.ut_set_up().
        '''
        self._logs.append((level, output))

        # I want to eat the logs and not let them into the output.
        # ...unless verbose tests, then let it go through.
        return not self._ut_is_verbose

    def capture_logs(self, enabled: bool):
        if enabled:
            log.ut_set_up(self.receive_log)
        else:
            log.ut_tear_down()

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_init(self):
        self.assertTrue(self.manager)
        self.assertTrue(self.manager.time)
        self.assertTrue(self.manager.event)
        self.assertTrue(self.manager.component)
        self.assertTrue(self.manager.entity)
        self.assertTrue(self.manager.system)
        self.assertTrue(self.engine)

    def test_engine_start(self):
        '''
        We're using a full game environment. That is, we're using the engine to
        do its part of set-up instead of skipping around all unity-testy like
        doing whatever.

        So make sure engine can set up all the stuff we need.
          - e.g.: Does it trigger command registration?
        '''

        # Not life'd or registration'd yet.
        self.assertEqual(self.engine.life_cycle, EngineLifeCycle.INVALID)
        self.assertFalse(self.reg_open)

        # Run create ticks.
        self.engine._run_create()

        # Life'd, registration'd, and some commands exist now.
        self.assertEqual(self.engine.life_cycle, EngineLifeCycle.CREATING)
        self.assertTrue(self.reg_open)
        self.assertTrue(self.input_system._commander._commands)

    def test_background_cmd(self):
        self._engine_start()

        # Set up entity. Not much use right now but we need to test debug
        # command permissions someday so hi there debug guy.
        admin = self.create_entity()

        # Ok... test the background debug command
        context = UnitTestContext(
            self.__class__.__name__,
            'input-event',
            {})  # no initial sub-context

        # Do the test command event.
        event = CommandInputEvent(
            admin.id,
            admin.type_id,
            context,
            "/background")
        self.capture_logs(True)
        self.trigger_events(event, expected_events=0)
        self.capture_logs(False)

        self.assertTrue(self._logs)

        # Look through any received logs for our command output.
        log_level = None
        log_msg = None
        for captured_log in self._logs:
            if veredi.zest.debug.background._LOG_TITLE in captured_log[1]:
                log_level = captured_log[0]
                log_msg = captured_log[1]
                break

        # TODO: Check output more, somehow?
        self.assertEqual(log_level, log.Level.CRITICAL)
        self.assertIn(veredi.zest.debug.background._LOG_TITLE,
                      log_msg)

    def test_debug_background_cmd(self):
        self._engine_start()

        # Set up entity. Not much use right now but we need to test debug
        # command permissions someday so hi there debug guy.
        admin = self.create_entity()

        # Ok... test the background debug command
        context = UnitTestContext(
            self.__class__.__name__,
            'input-event',
            {})  # no initial sub-context

        # Do the test command event.
        event = CommandInputEvent(
            admin.id,
            admin.type_id,
            context,
            "/debug background")
        self.capture_logs(True)
        self.trigger_events(event, expected_events=0)
        self.capture_logs(False)

        self.assertTrue(self._logs)

        # Look through any received logs for our command output.
        log_level = None
        log_msg = None
        for captured_log in self._logs:
            if veredi.zest.debug.background._LOG_TITLE in captured_log[1]:
                log_level = captured_log[0]
                log_msg = captured_log[1]
                break

        # TODO: Check output more, somehow?
        self.assertEqual(log_level, log.Level.CRITICAL)
        self.assertIn(veredi.zest.debug.background._LOG_TITLE,
                      log_msg)