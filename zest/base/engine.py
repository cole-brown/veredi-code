# coding: utf-8

'''
Base Veredi Class for Testing ECS Engine.
  - Helpful functions.
  - Set-up / Tear-down for global Veredi stuff.
    - config registry
    - yaml codec tag registry
    - etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional

from veredi.logger                      import log
from .ecs                               import ZestEcs
from ..                                 import zload
from ..zpath                            import TestType
from veredi.base.const                  import VerediHealth

from veredi.game.engine        import (Engine,
                                       EngineLifeCycle)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Base Class
# -----------------------------------------------------------------------------

class ZestEngine(ZestEcs):
    '''
    Base Veredi Class for Testing ECS Engine.

    Internal (probably) helpers/functions/variables - that is ones subclasses
    probably won't need to use directly - are prefixed with '_'. The
    helpers/functions/variables useddirectly are not prefixed.

    Or in regex terms:
      -  r'[a-z][a-zA-Z_]*[a-z]': Called by subclasses for actual unit tests.
      - r'_[a-z_][a-zA-Z_]*[a-z]': Just used by this internally, most likely.
    '''

    _REQUIRE_ENGINE = True

    # -------------------------------------------------------------------------
    # Set-Up
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Defines ZestSystem's instance variables with type hinting, docstrs.
        '''
        super()._define_vars()

        self.engine_ready = False
        '''
        Flag we set after we initialize the engine in engine_set_up(). Prevents
        double-init of engine via programmer stupidity... >.>
        '''

    def set_up(self) -> None:
        '''
        Override this!

        super().set_up()
        <your test stuff>
        '''
        super().set_up()

        # ---
        # Set-Up subclasses might want to do:
        # ---
        #
        # self.set_up_input()
        #   - Create an InputSystem for self.input_system.
        #   - Subscribes self._eventsub_cmd_reg to CommandRegistrationBroadcast
        #
        # self.set_up_output()
        #   - Create an OutputSystem for self.output_system.
        #
        # self.set_up_events()
        #   - Subscribes to test's desired events, tells ECS to subscribe.

    # -------------------------------------------------------------------------
    # Tear-Down
    # -------------------------------------------------------------------------

    def tear_down(self) -> None:
        '''
        Override this!

        <your stuff here>
        super().tear_down()
        '''

        # ---
        # Tell ECS systems to go into their shut-down/tear-down/whatever mode.
        # Apoptosis mode, I suppose. Or maybe just apoptosis.
        # Structured death, basically.
        # ---
        self._apoptosis()

        self.engine_ready = False
        self.engine = None
        super().tear_down()

    def _apoptosis(self) -> None:
        '''
        Tells engine to go into structured shutdown.
        '''
        if not self.engine:
            return

        # TODO [2020-08-24]: Make sure managers and systems get apoptosis
        # calls.

        self.engine.apoptosis()

    # -----------------------------------------------------------------------
    # Engine
    # -----------------------------------------------------------------------

    def engine_set_up(self) -> None:
        '''
        Get engine through creation ticks and ready for normal operation.
        '''
        if self.engine_ready:
            self.fail("Engine is already set up, so... fail? "
                      f"engine_ready: {self.engine_ready}")
        if self.reg_open:
            self.fail("Registration is already set up, so engine cannot "
                      "do all of its setup properly. "
                      f"systems subbed: {self.events_ready}, "
                      f"reg open: {self.reg_open}")

        # Not life'd or registration'd yet.
        self.assertEqual(self.engine.life_cycle, EngineLifeCycle.INVALID)
        self.assertFalse(self.reg_open)

        # Run create ticks.
        self.engine._run_create()

        # Life'd, registration'd, and some commands exist now.
        self.assertEqual(self.engine.life_cycle, EngineLifeCycle.CREATING)
        self.assertTrue(self.reg_open)
        self.assertTrue(self.input_system._commander._commands)
        self.engine_ready = True

    def engine_tick(self, num_ticks=1) -> None:
        '''
        Tick through `num_ticks` cycles of the normal game tick phases.
        '''
        if not num_ticks:
            return

        if self.engine.life_cycle == EngineLifeCycle.CREATING:
            # Stop puts us in APOPTOSIS, which is to avoid getting into
            # _run_alive's infinite run loop.
            self.engine.stop()
            self.assertEqual(self.engine.engine_health,
                             VerediHealth.APOPTOSIS)
            self.engine._run_alive()
            # So set our engine back to healthy now that it's ALIVE.
            self.assertEqual(self.engine.life_cycle, EngineLifeCycle.ALIVE)
            self.assertEqual(self.engine.engine_health,
                             VerediHealth.APOPTOSIS)
            self.engine.health = VerediHealth.HEALTHY

        for i in range(num_ticks):
            self.engine.tick()
