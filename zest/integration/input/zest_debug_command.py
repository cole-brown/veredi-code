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

from ..integrate import IntegrationTest

from veredi.base.null import Null
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
# import veredi.zest.debug.background
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

    def tearDown(self):
        super().tearDown()

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
        # Not life'd or registration'd yet.
        self.assertEqual(self.engine.life_cycle, EngineLifeCycle.INVALID)
        self.assertFalse(self.reg_open)

        # Run create ticks.
        self.engine._run_create()

        # Life'd, registration'd, and some commands exist now.
        self.assertEqual(self.engine.life_cycle, EngineLifeCycle.CREATING)
        self.assertTrue(self.reg_open)
        self.assertTrue(self.input_system._commander._commands)

    # def test_skill_cmd(self):
    #     # Set up entity with skill data
    #     entity = self.per_test_setup()

    #     # Let the commands register
    #     self.allow_registration()

    #     # Ok... test the skill command.
    #     context = UnitTestContext(
    #         self.__class__.__name__,
    #         'input-event',
    #         {})  # no initial sub-context

    #     # Do the test command event.
    #     event = CommandInputEvent(
    #         entity.id,
    #         entity.type_id,
    #         context,
    #         "/skill $perception + 4")
    #     self.trigger_events(event, expected_events=0)
