# coding: utf-8

'''
"If you want to make an apple pie from scratch, you must first invent
the universe."
  - Carl Sagan

So... this test shows how to invent the game from scratch.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, Optional, List
if TYPE_CHECKING:
    from veredi.game.ecs.event     import Event


import unittest
import sys


# ------------------------------
# Testing Help (Unavoidable?)
# ------------------------------
from veredi.zest               import zinit, zpath
from veredi.zest.timing        import ZestTiming
from veredi.zest.base.unit     import ZestDottedDescriptor

# For asserting.
from veredi.data.config.config import Configuration
from veredi.game.ecs.meeting   import Meeting
from veredi.game.engine        import Engine
from veredi.game.ecs.const     import SystemTick


# ------------------------------
# Debugging Help
# ------------------------------
from veredi.logs               import log
from veredi.debug.const        import DebugFlag


# ------------------------------
# Veredi Misc
# ------------------------------
from veredi.base.strings       import label
from veredi.data               import background


# ------------------------------
# What we're testing:
# ------------------------------
from veredi                    import run
# Also testing dynamic registration (on import) for this, so do not import
# until after registration has initialized registrars.
#   from .system                   import TestSystem


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


class Test_From_Scratch(unittest.TestCase):
    '''
    Test starting/running Veredi from scratch (that is, no unit test helpers).

    This tests creating/starting a game the "correct" way. The way users of
    veredi should be creating/starting it.
    '''

    dotted: ZestDottedDescriptor = ZestDottedDescriptor(__file__)

    # -------------------------------------------------------------------------
    # Set-Up
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Defines any instance variables with type hinting, docstrs.
        Happens ASAP during unittest.setUp().
        '''
        # ---------------------------------------------------------------------
        # Create self vars.
        # ---------------------------------------------------------------------

        # -
        # ---
        # Just define the variables here for name, type hinting, and docstr.
        # Set to empty/None/False/default. Actual setup of the variables
        # should be done elsewhere.
        # ---
        # -

        # ------------------------------
        # Debugging
        # ------------------------------

        self._ut_is_verbose = ('-v' in sys.argv) or ('--verbose' in sys.argv)
        '''
        True if unit tests were run with the 'verbose' flag from
        command line/whatever.

        Pretty stupid hack to get at verbosity since unittest doesn't provide
        it anywhere. :(
        '''

        self.debugging: bool = False
        '''
        Use as a flag for turning on/off extra debugging stuff.
        Mainly used with log.LoggingManager.on_or_off() context manager.
        '''

        self.debug_flags: Optional[DebugFlag] = (DebugFlag.RAISE_ERRORS
                                                 | DebugFlag.RAISE_HEALTH)
        '''
        Debug flags to pass on to things that use them, like:
        Engine, Systems, Mediators, etc.
        '''

        # ------------------------------
        # Time (logging/debug help)
        # ------------------------------
        self._timing: ZestTiming = ZestTiming(tz=True)  # True -> local tz
        '''
        Timing info helper. Auto-starts timer when created, or can restart with
        self._timing.test_start(). Call self._timing.test_end() and check it
        whenever you want to see timing info.
        '''

        # ------------------------------
        # Events
        # ------------------------------

        self.events: List['Event'] = []
        '''
        Simple queue for receiving events.
        '''

        # ------------------------------
        # ECS
        # ------------------------------

        self.config: 'Configuration' = None
        '''
        Configuration for the game.
        '''

        self.manager: 'Meeting' = None
        '''
        Meeting of Managers for the engine/game.
        '''

        # ------------------------------
        # Engine
        # ------------------------------

        self.engine: 'Engine' = None
        '''
        The Game Engine.
        '''

    # -------------------------------------------------------------------------
    # Properties & Such
    # -------------------------------------------------------------------------

    def set_background_testing_flag(self, flag: bool) -> None:
        '''
        Set background context's unit_testing flag to True/False.
        '''
        background.testing.set_unit_testing(flag)

    # -------------------------------------------------------------------------
    # Set-Up: Unit Test
    # -------------------------------------------------------------------------

    def setUp(self) -> None:
        '''
        Very basic set-up. Actual game set-up all happens in test function.
        '''
        self._define_vars()

    # -------------------------------------------------------------------------
    # Tear-Down: Unit Test
    # -------------------------------------------------------------------------

    def tearDown(self) -> None:
        '''
        unittest.TestCase tearDown function.

        First calls `tear_down()`, then does general test tear-down afterwards.
        '''

        # ---
        # Reset or unset our variables for fastidiousness's sake.
        # ---
        self._ut_is_verbose = False
        self.debugging      = False
        self.debug_flags    = None
        self._timing        = None
        self.events         = []
        self.config         = None
        self.manager        = None
        self.engine         = None

        # ---
        # Other tear-downs.
        # ---
        log.ut_tear_down()
        zinit.tear_down_registries()
        zinit.tear_down_background()

    # -------------------------------------------------------------------------
    # Set-Up: Real, Actual Veredi
    # -------------------------------------------------------------------------

    def registration(self, test_name: str) -> bool:
        '''
        Do the "officially, this is how you set up a game" up to
        run.registration (which is called by run.init).
        '''
        with self.subTest(f"{self.__class__.__name__}.{test_name}() "
                          "-> set_up():"):
            # ---
            # Configuration from config file.
            # ---
            rules = 'veredi.rules.d20.pf2'
            game_id = 'test-campaign'
            path = zpath.config(None, zpath.TestType.FUNCTIONAL)
            self.config = run.configuration(rules, game_id, path)
            self.assertIsNotNone(self.config)
            self.assertIsInstance(self.config, Configuration)

            # ---
            # Registries of various types... config, encodables, etc.
            # ---
            run.init(self.config)

        return True

    def set_up(self,
               test_name: str,
               *systems:  Optional['run.system.SysCreateType']) -> bool:
        '''
        Do the "officially, this is how you set up a game" stuff.

        Returns success/failure.
        '''
        with self.subTest(f"{self.__class__.__name__}.{test_name}() "
                          "-> set_up():"):
            # ---
            # Meeting of Managers from config settings.
            # ---
            self.manager = run.managers(self.config,
                                        debug_flags=self.debug_flags)
            self.assertIsNotNone(self.manager)
            self.assertIsInstance(self.manager, Meeting)

            # ---
            # Systems
            # ---
            if systems:
                # Our generic context...
                context = self.config.make_config_context()
                sids = run.system.many(self.config,
                                       context,
                                       *systems,
                                       debug_flags=self.debug_flags)
                self.assertIsNotNone(sids)
                self.assertIsInstance(sids, list)
                self.assertEqual(len(sids), len(systems))

            # self.input_system = self.init_one_system(InputSystem)
            # self.output_system = self.init_one_system(OutputSystem)

            # ---
            # Engine from config settings.
            # ---
            self.engine = run.engine(self.config,
                                     self.manager,
                                     debug_flags=self.debug_flags)
            self.assertIsNotNone(self.engine)
            self.assertIsInstance(self.engine, Engine)

            # ---
            # Got to end of 'subTest' -> success
            # ---
            return True

        # ---
        # Failed somewhere in 'subTest' -> failure
        # ---
        return False

    # -------------------------------------------------------------------------
    # Tear-Down: Real, Actual Veredi
    # -------------------------------------------------------------------------

    def tear_down(self) -> None:
        '''
        Put engine into TICKS_DEATH and run until it's dead.
        '''
        # Test stopped engine. Anything else to do to tear it all down?
        pass

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_from_scratch(self) -> None:
        # Set-up Veredi game with our TestSystem.
        self.registration("test_from_scratch")

        # Import the testing system and see if its decorator registers it.
        from .system import TestSystem

        # Now we're ready to test.
        self.assertTrue(
            self.set_up("test_from_scratch", TestSystem))
        system = self.manager.system.get(TestSystem)
        self.assertIsNotNone(system)
        self.assertIsInstance(system, TestSystem)
        countdown = system._countdown
        self.assertGreater(countdown, 0)
        self.assertFalse(system.ticks_seen)

        # Run the engine!
        run.start(self.engine)

        # Our test system should stop the engine after it counts the right
        # number of run-cycle ticks. Check how it did.
        self.assertLessEqual(system._countdown, 0)
        self.assertTrue(system.ticks_seen)

        # ---
        # Make sure the ticks are sane.
        # ---
        # - Should only be 1 of SYNTHESIS, APOPTOSIS, and NECROSIS.
        # - Should be 0 of FUNERAL.
        #   - Technically 1... However, FUNERAL tick doesn't call systems, so
        #     we don't get to counted it. So zero.
        # - Should be 1 or more MITOSIS and AUTOPHAGY.
        # - Should be `countdown` number of all TICKS_LIFE ticks.
        # - Should NOT have "ticked" any life-cycles.

        self.assertEqual(system.ticks_seen[SystemTick.SYNTHESIS], 1)
        self.assertEqual(system.ticks_seen[SystemTick.APOPTOSIS], 1)
        self.assertEqual(system.ticks_seen[SystemTick.NECROSIS], 1)

        self.assertGreater(system.ticks_seen[SystemTick.MITOSIS], 0)
        self.assertGreater(system.ticks_seen[SystemTick.AUTOPHAGY], 0)

        self.assertEqual(system.ticks_seen[SystemTick.TIME], countdown)
        self.assertEqual(system.ticks_seen[SystemTick.CREATION], countdown)
        self.assertEqual(system.ticks_seen[SystemTick.PRE], countdown)
        self.assertEqual(system.ticks_seen[SystemTick.STANDARD], countdown)
        self.assertEqual(system.ticks_seen[SystemTick.POST], countdown)
        self.assertEqual(system.ticks_seen[SystemTick.DESTRUCTION], countdown)

        # We don't add ticks until they're seen.
        self.assertNotIn(SystemTick.FUNERAL, system.ticks_seen)

        # "Ticking" the Life-Cycles is a big no-no.
        self.assertNotIn(SystemTick.TICKS_BIRTH, system.ticks_seen)
        self.assertNotIn(SystemTick.TICKS_LIFE, system.ticks_seen)
        self.assertNotIn(SystemTick.TICKS_DEATH, system.ticks_seen)
        self.assertNotIn(SystemTick.TICKS_AFTERLIFE, system.ticks_seen)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.zest.functional.zest_from_scratch

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
