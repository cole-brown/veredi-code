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

from veredi.zest.base.integrate   import ZestIntegrateEngine
from veredi.zest.zpath            import TestType


from veredi.logs                  import log
from veredi.debug.const           import DebugFlag
from veredi.base.context          import UnitTestContext

from veredi.interface.input.event import CommandInputEvent
from veredi.game.ecs.const        import SystemTick

# import veredi.zest.debug.debug
import veredi.zest.debug.background
import veredi.data.background


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_EngineStart_DebugCmds(ZestIntegrateEngine):

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = __file__

    def set_up(self):
        self.debug_flags = DebugFlag.GAME_ALL
        super().set_up()

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
        self.assertEqual(self.engine.life_cycle, SystemTick.INVALID)
        self.assertFalse(self.reg_open)

        # Run create ticks.
        self.engine_life_start()

        # Life'd, registration'd, and some commands exist now.
        self.assertEqual(self.engine.life_cycle, SystemTick.TICKS_BIRTH)
        self.assertTrue(self.reg_open)
        self.assertTrue(self.input_system._commander._commands)

    def create_entity(self):
        admin = super().create_entity()
        self.create_identity(admin,
                             data={
                                 'identity': {
                                     'name': 'Miss GM Sir',
                                     'group': 'admin',
                                     'owner': 'u/gm_dm',
                                     'display-name': 'Her Excellency The Rev Sir Doctor Game Master',
                                     'title': '(Do Not Anger)',
                                 },
                             })
        return admin

    def test_background_cmd(self):
        self.engine_life_start()

        # Set up entity. Not much use right now but we need to test debug
        # command permissions someday so hi there debug guy.
        admin = self.create_entity()

        # Ok... test the background debug command
        context = UnitTestContext(self)  # no initial sub-context

        # Do the test command event.
        event = CommandInputEvent(
            admin.id,
            admin.type_id,
            context,
            "/background")
        self.capture_logs(True)
        self.trigger_events(event, expected_events=0)
        self.capture_logs(False)

        self.assertTrue(self.logs)

        # Look through any received logs for our command output.
        log_level = None
        log_msg = None
        for captured_log in self.logs:
            if veredi.zest.debug.background._LOG_TITLE in captured_log[1]:
                log_level = captured_log[0]
                log_msg = captured_log[1]
                break
        else:
            self.fail("No background debug log found. log level: "
                      f"{log_level}, log msg: {log_msg}")

        # TODO: Check output more, somehow?
        self.assertEqual(log_level, log.Level.CRITICAL)
        self.assertIn(veredi.zest.debug.background._LOG_TITLE,
                      log_msg)

    def test_debug_background_cmd(self):
        self.engine_life_start()

        # Set up entity. Not much use right now but we need to test debug
        # command permissions someday so hi there debug guy.
        admin = self.create_entity()

        # Ok... test the background debug command
        context = UnitTestContext(self)  # no initial sub-context

        # Do the test command event.
        event = CommandInputEvent(
            admin.id,
            admin.type_id,
            context,
            "/debug background")
        self.capture_logs(True)
        self.trigger_events(event, expected_events=0)
        self.capture_logs(False)

        self.assertTrue(self.logs)

        # Look through any received logs for our command output.
        log_level = None
        log_msg = None
        for captured_log in self.logs:
            if veredi.zest.debug.background._LOG_TITLE in captured_log[1]:
                log_level = captured_log[0]
                log_msg = captured_log[1]
                break
        else:
            self.fail("No background debug log found. log level: "
                      f"{log_level}, log msg: {log_msg}")

        # TODO: Check output more, somehow?
        self.assertEqual(log_level, log.Level.CRITICAL)
        self.assertIn(veredi.zest.debug.background._LOG_TITLE,
                      log_msg)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.zest.integration.interface.zest_debug_command

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
