# coding: utf-8

'''
Base Veredi Class for Testing ECS Engine.
  - Helpful functions.
  - Set-up / Tear-down for global Veredi stuff.
    - config registry
    - yaml serdes tag registry
    - etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Dict, Set

from veredi.logger               import log
from .ecs                        import ZestEcs

from veredi.game.ecs.base.system import System
from veredi.game.ecs.const       import (SystemTick,
                                         game_loop_start,
                                         game_loop_end,
                                         _GAME_LOOP_SEQUENCE)


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
    _ENGINE_TICKS_DEFAULT_START_END = 1_000_000  # A million ticks or timeout.

    _ENGINE_BAD_TICKS = (SystemTick.FUNERAL, SystemTick.ERROR)
    _ENGINE_BAD_LIFE_CYCLE = (SystemTick.FUNERAL, SystemTick.ERROR)

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

        self._required_systems: Set[System] = set({
            # InputSystem:  Covered by ZestIntegrateEngine.set_up()
            # OutputSystem: Covered by ZestIntegrateEngine.set_up()
        })
        '''Extra systems we need to fill in this game's systems.'''

        self._in_shutdown: bool = False
        '''
        Set to True while in ending ticks.
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

    def engine_life_start(self,
                          tick_amounts: Optional[Dict[SystemTick, int]] = None
                          ) -> Dict[SystemTick, int]:
        '''
        Run Engine through TICKS_BIRTH life-cycle.

        If `tick_amounts` is defined, this will use the number of ticks
        allowabled in TICKS_BIRTH, and in specific starting ticks (SYNTHESIS,
        etc) as a maximum. See here for an example:
          veredi.game.zest_engine.ZestEngine.test_ticks_birth()

        If `tick_amounts` is None, we will allow a whole lotta ticks and trust
        in the engine to timeout of TICKS_BIRTH if something is amiss.

        Returns a dictionary of ticks/life-cycles ran. Layout is the same as
        the input `tick_amounts` dict.
        '''
        self.assertEqual(self.engine.life_cycle, SystemTick.INVALID)
        self.assertEqual(self.engine.tick, SystemTick.INVALID)

        if not tick_amounts:
            tick_amounts = {
                # ---
                # Life-Cycle
                # ---
                # Max ticks in start life-cycle.
                SystemTick.TICKS_BIRTH: self._ENGINE_TICKS_DEFAULT_START_END,

                # ---
                # Ticks
                # ---
                # Max ticks for each tick in TICKS_BIRTH.
                SystemTick.SYNTHESIS: self._ENGINE_TICKS_DEFAULT_START_END,
                SystemTick.MITOSIS:   self._ENGINE_TICKS_DEFAULT_START_END,
            }

        # If we fail starting the engine somewhere along the way, try to stop
        # it. Maybe some systems can run through shutdown and clean up for the
        # next test.
        #
        # Only an issue (so far) for multiprocess stuff, but we have that.
        try:
            return self.engine_run(SystemTick.TICKS_BIRTH,
                                   tick_amounts)
        except:
            # Attempt emergency shutdown.
            self.engine_emergency_stop()
            raise

    def start_engine_and_events(
            self,
            skip_event_setup: bool                            = False,
            tick_amounts:     Optional[Dict[SystemTick, int]] = None
    ) -> Dict[SystemTick, int]:
        '''
        Sets up events and runs Engine through TICKS_BIRTH life-cycle.
          - Calls self.engine_life_start(`tick_amounts`)
          - Calls self.set_up_events()

        If `tick_amounts` is defined, this will use the number of ticks
        allowabled in TICKS_BIRTH, and in specific starting ticks (SYNTHESIS,
        etc) as a maximum. See here for an example:
          veredi.game.zest_engine.ZestEngine.test_ticks_birth()

        If `tick_amounts` is None, we will allow a whole lotta ticks and trust
        in the engine to timeout of TICKS_BIRTH if something is amiss.

        Returns a dictionary of ticks/life-cycles ran. Layout is the same as
        the input `tick_amounts` dict.
        '''
        if not skip_event_setup:
            self.set_up_events()
        result = self.engine_life_start(tick_amounts)

        return result

    def start_engine_events_systems_etc(
            self,
            skip_event_setup: bool                            = False,
            tick_amounts:     Optional[Dict[SystemTick, int]] = None
    ) -> Dict[SystemTick, int]:
        '''
        Sets up events and runs Engine through TICKS_BIRTH life-cycle.
        Calls:
          - self.engine_life_start(`tick_amounts`)
          - self.init_many_systems(*self._required_systems)
          - if not skip_event_setup:
            - self.set_up_events()
          - self.allow_registration()

        If `tick_amounts` is defined, this will use the number of ticks
        allowabled in TICKS_BIRTH, and in specific starting ticks (SYNTHESIS,
        etc) as a maximum. See here for an example:
          veredi.game.zest_engine.ZestEngine.test_ticks_birth()

        If `tick_amounts` is None, we will allow a whole lotta ticks and trust
        in the engine to timeout of TICKS_BIRTH if something is amiss.

        Returns a dictionary of ticks/life-cycles ran. Layout is the same as
        the input `tick_amounts` dict.
        '''
        if not skip_event_setup:
            self.set_up_events()
        if self._required_systems:
            self.init_many_systems(*self._required_systems)
        result = self.engine_life_start(tick_amounts)

        # Engine and InputSystem should have opened up registration on their
        # own as part of engine_life_start().
        # self.allow_registration()
        return result

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
        # Autophagy mode, I suppose. Or maybe just autophagy.
        # Structured death, basically.
        # ---
        # if (self.engine.life_cycle != SystemTick.INVALID
        #         and self.engine.life_cycle != SystemTick.FUNERAL):
        #     # Not dead yet, so do the TICKS_DEATH life_cycle.
        #     self.engine_life_end()

        self.engine_ready = False
        self.engine = None
        super().tear_down()

    def engine_emergency_stop(self) -> None:
        '''
        Run engine through TICKS_DEATH due to bad things happening.
        '''
        # Something bad happened during shutdown? Nothing we can do.
        if self._in_shutdown:
            return

        try:
            # Attempt the end-of-life stuff.
            self.engine_life_end()
        except:
            # Don't care about any exceptions. Just trying to clean up engine
            # as much as possible.
            pass

    def engine_life_end(self,
                        tick_amounts: Optional[Dict[SystemTick, int]] = None
                        ) -> Dict[SystemTick, int]:
        '''
        Does nothing if engine is in INVALID life-cycle, as we assume that
        means it never started.

        Run Engine through TICKS_DEATH life-cycle.

        If `tick_amounts` is defined, this will use the number of ticks
        allowabled in TICKS_DEATH, and in specific starting ticks (AUTOPHAGY,
        etc) as a maximum. See here for an example:
          veredi.game.zest_engine.ZestEngine.test_ticks_death()

        If `tick_amounts` is None, we will allow a whole lotta ticks and trust
        in the engine to timeout of TICKS_DEATH if something is amiss.

        Returns a dictionary of ticks/life-cycles ran. Layout is the same as
        the input `tick_amounts` dict.
        '''
        # No need... never started?
        if self.engine.life_cycle == SystemTick.INVALID:
            return

        if not tick_amounts:
            tick_amounts = {
                # ---
                # Life-Cycle
                # ---
                # Max ticks in end life-cycle.
                SystemTick.TICKS_DEATH: self._ENGINE_TICKS_DEFAULT_START_END,

                # ---
                # Ticks
                # ---
                # Max ticks for each tick in TICKS_DEATH.
                SystemTick.AUTOPHAGY: self._ENGINE_TICKS_DEFAULT_START_END,
                SystemTick.APOPTOSIS: self._ENGINE_TICKS_DEFAULT_START_END,
                SystemTick.NECROSIS:  1,
                SystemTick.FUNERAL:   1,
            }

        # Stop engine, then send it through its ending life-cycle of ticks.
        self.engine.stop()
        return self.engine_run(SystemTick.TICKS_DEATH,
                               tick_amounts)

    # -------------------------------------------------------------------------
    # Engine
    # -------------------------------------------------------------------------

    def engine_tick(self,
                    amount: int = 1) -> bool:
        '''
        Ticks engine `amount` times. Does whatever engine life-cycle/tick have
        it set to do next tick.

        Returns 'success'. False means we got a bad return value from the
        engine for one of the ticks.
        '''
        tick = self.engine.tick
        if self._in_shutdown:
            # Check for good health through shutdown specifically. Some bugs
            # have happened about this.
            self.assertFalse(self.engine._stopped_healths(),
                            ("ZestEngine thinks engine is in shutdown, but "
                             "Engine's health has failed? "
                             f"Life-Cycle is: {self.engine.life_cycle}, "
                             f"Tick is: {self.engine.tick}, "
                             f"engine health is: "
                             f"{str(self.engine.engine_health)} "
                             "tick health is: "
                             f"{str(self.engine.tick_health)}"))

            # Check for whether the engine thinks it is stopped for whatever
            # reasons it has. Currently [2021-01-12] it's health and
            # life-cycle.
            self.assertFalse(self.engine.stopped(),
                            ("ZestEngine thinks engine is in shutdown, but "
                             "Engine is stopped()? "
                             f"Life-Cycle is: {self.engine.life_cycle}, "
                             f"Tick is: {self.engine.tick}, "
                             f"engine health is: "
                             f"{str(self.engine.engine_health)} "
                             "tick health is: "
                             f"{str(self.engine.tick_health)}"))

            # ---
            # Can't check that it's always in "stopping()" if our
            # `_in_shutdown` is True. For example, Engine will finish off a
            # TICKS_LIFE cycle before transitioning into TICKS_DEATH when asked to
            # stop.
            # ---
            # self.assertTrue(self.engine.stopping(),
            #                 ("ZestEngine thinks engine is in shutdown, but "
            #                  "Engine is not stopping(). "
            #                  f"Life-Cycle is: {self.engine.life_cycle}, "
            #                  f"Tick is: {self.engine.tick}, "
            #                  "engine health is: "
            #                  f"{str(self.engine.engine_health)} "
            #                  "tick health is: "
            #                  f"{str(self.engine.tick_health)}"))
            # ---

        emergency_stop = False
        for i in range(amount):
            health = self.engine.run_tick()
            # health == None means engine refused to run a tick due to being in
            # a bad state. If we are in shutdown, no point doing emergency
            # stop. But otherwise, try to have the engine do it's TICKS_DEATH so
            # things have a chance to clean up.
            if self.engine._stopped_healths(health):
                # Do emergency stop if not already stopping...
                emergency_stop = not self._in_shutdown
                break

        if emergency_stop:
            self.engine_emergency_stop()
        return not emergency_stop

    def engine_run(self,
                   run_life_cycle:      SystemTick,
                   tick_amounts:        Dict[SystemTick, int]
                   ) -> Dict[SystemTick, int]:
        '''
        Run a number of `run_life_cycle` ticks/life-cycles as indicated in
        `tick_amounts`.

        For TICKS_BIRTH/TICKS_DEATH, can specify (the maximum number of) each
        individual tick.

        For TICKS_LIFE, the individual ticks will be ignored in `tick_amounts`.

        Returns a dictionary of number of ticks/life-cycles actually ran.
        '''
        result = {}

        # ---
        # Run a vaild life-cycle or error.
        # ---
        if run_life_cycle == SystemTick.TICKS_BIRTH:
            result = self._engine_run_start(tick_amounts)
            self._engine_check()
        elif run_life_cycle == SystemTick.TICKS_LIFE:
            self._engine_check()
            result = self._engine_run_run(tick_amounts)
        elif run_life_cycle == SystemTick.TICKS_DEATH:
            if self.engine.tick != SystemTick.NECROSIS:
                self._engine_check()
            result = self._engine_run_end(tick_amounts)
        else:
            self.assertIn(run_life_cycle,
                          (SystemTick.TICKS_BIRTH,
                           SystemTick.TICKS_LIFE,
                           SystemTick.TICKS_DEATH))

        return result

    def _engine_check(self) -> None:
        '''
        Checks engine_ready, self.engine.life_cycle, and self.reg_open.
        '''
        if (self.engine_ready
                and (self.engine.life_cycle == SystemTick.INVALID
                     or self.engine.life_cycle == SystemTick.TICKS_BIRTH)):
            self.fail("We think engine is ready but it is not past "
                      "TICKS_BIRTH life-cycle. Engine is already set up, "
                      "so... fail? engine_ready: ready?: "
                      f"{self.engine_ready}, life-cycle: "
                      f"{self.engine.life_cycle}")

    def _increment_tick_dict(self,
                             values: Dict[SystemTick, int],
                             *ticks):
        '''
        Increment each index in `ticks`. If not in `values` dict, will be set
        to 0 and incremented to 1.
        '''
        for each in ticks:
            current = values.setdefault(each, 0)
            values[each] = current + 1

    def _engine_run_start(self,
                          ticks: Dict[SystemTick, int]
                          ) -> Dict[SystemTick, int]:
        '''
        Do the engine's TICKS_BIRTH life-cycle.

        Will run/verify each tick cycle in start for UP TO as many times as set
        in `ticks[<tick>]`.

        Will let the TICKS_BIRTH life-cycle go for UP TO as many times as set
        in `ticks[SystemTick.TICKS_BIRTH]`, or at a minimum once per start-up
        tick type (SYNTHESIS, MITOSIS...).
        '''
        ran_ticks = {}
        self.assertEqual(self.engine.life_cycle, SystemTick.INVALID)
        self.assertEqual(self.engine.tick, SystemTick.INVALID)

        # Tick a maximum of: what's been requested, or the number of
        # start_ticks we have.

        start_ticks = (SystemTick.SYNTHESIS, SystemTick.MITOSIS)
        requested_ticks = ticks.get(SystemTick.TICKS_BIRTH, None)
        if requested_ticks is not None:
            # Fail out with an explanation if unhappy.
            if len(start_ticks) > requested_ticks:
                self.fail("Currently don't support running less than one "
                          "tick per TICKS_BIRTH tick. requested: "
                          f"{requested_ticks}, min: {len(start_ticks)}. "
                          f"Start-up ticks: {start_ticks}")

        # ---
        # Tick: Synthesis
        # ---
        # Tick SYNTHESIS for up to as many times as requested.
        tick_num = ticks.get(SystemTick.SYNTHESIS, 1)
        last_tick = tick_num - 1
        for i in range(tick_num):
            success = self.engine_tick()

            # Update our ticks counter...
            self._increment_tick_dict(
                ran_ticks,
                self.engine.life_cycle,
                self.engine.tick)

            self.assertTrue(success)
            self.assertEqual(self.engine.life_cycle,
                             SystemTick.TICKS_BIRTH)
            self.assertEqual(self.engine.tick,
                             SystemTick.SYNTHESIS)

            # Always in TICKS_BIRTH after SYNTHESIS. MITOSIS is next and
            # it's TICKS_BIRTH too.
            self.assertEqual(self.engine._life_cycle.next,
                             SystemTick.TICKS_BIRTH)
            # We MUST be headed for MITOSIS.
            if i == last_tick:
                self.assertEqual(self.engine._tick.next,
                                 SystemTick.MITOSIS)

            # We CAN be headed into MITOSIS, but staying in SYNTHESIS is
            # also acceptable.
            else:
                self.assertIn(self.engine._tick.next,
                              start_ticks)
                if self.engine._tick.next != SystemTick.SYNTHESIS:
                    break

        # ---
        # Tick: Mitosis
        # ---
        # Tick MITOSIS for up to as many times as requested.
        tick_num = ticks.get(SystemTick.MITOSIS, 1)
        last_tick = tick_num - 1
        for i in range(tick_num):
            success = self.engine_tick()

            # Update our ticks counter...
            self._increment_tick_dict(
                ran_ticks,
                self.engine.life_cycle,
                self.engine.tick)

            self.assertTrue(success)
            self.assertEqual(self.engine.life_cycle,
                             SystemTick.TICKS_BIRTH)
            self.assertEqual(self.engine.tick,
                             SystemTick.MITOSIS)

            if i == last_tick:
                # We MUST be headed for TICKS_LIFE & TIME.
                self.assertEqual(self.engine._life_cycle.next,
                                 SystemTick.TICKS_LIFE)
                self.assertEqual(self.engine._tick.next,
                                 SystemTick.TIME)
            else:
                # We CAN be headed into TICKS_LIFE & TIME, but staying in
                # TICKS_BIRTH & MITOSIS is also acceptable.
                if self.engine._life_cycle.next == SystemTick.TICKS_BIRTH:
                    self.assertEqual(self.engine._life_cycle.next,
                                     SystemTick.TICKS_BIRTH)
                    self.assertEqual(self.engine._tick.next,
                                     SystemTick.MITOSIS)

                elif self.engine._life_cycle.next == SystemTick.TICKS_LIFE:
                    self.assertEqual(self.engine._life_cycle.next,
                                     SystemTick.TICKS_LIFE)
                    self.assertEqual(self.engine._tick.next,
                                     SystemTick.TIME)
                    break

                else:
                    # In a bad place. Fail out.
                    self.assertIn(self.engine._life_cycle.next,
                                  (SystemTick.TICKS_BIRTH,
                                   SystemTick.TICKS_LIFE))

        return ran_ticks

    def _engine_run_run(self,
                        ticks: Dict[SystemTick, int]
                        ) -> Dict[SystemTick, int]:
        '''
        Do some normal engine game-loops.

        Will run up to `ticks[TICKS_LIFE]` number of ticks. Will stop early if
        engine is exiting TICKS_LIFE.
        '''
        ran_ticks = {
            SystemTick.TICKS_LIFE: 0,

            SystemTick.TIME: 0,
            SystemTick.CREATION: 0,
            SystemTick.PRE: 0,
            SystemTick.STANDARD: 0,
            SystemTick.POST: 0,
            SystemTick.DESTRUCTION: 0,
        }
        # Must be about to run first tick of a game-loop in order to run.
        self.assertEqual(self.engine._life_cycle.next, SystemTick.TICKS_LIFE)
        self.assertEqual(self.engine._tick.next, SystemTick.TIME)

        # Tick a maximum of: what's been requested, or until engine says it's
        # not going to be in TICKS_LIFE anymore.
        requested_ticks = ticks.get(SystemTick.TICKS_LIFE, None)
        if not requested_ticks or requested_ticks < 1:
            self.fail("Can only run one or more TICKS_LIFE cycles. Requested: "
                      f"{requested_ticks}. ")

        for i in range(requested_ticks):
            success = self.engine_tick()

            # Update our ticks counter...
            # Assume we ran one of each standard tick in the TICKS_LIFE cycle,
            ran_list = [each[0] for each in _GAME_LOOP_SEQUENCE]
            # and get the actual cycle we ran.
            ran_list.append(self.engine.life_cycle)
            self._increment_tick_dict(
                ran_ticks,
                *ran_list)

            self.assertTrue(success)

            # Should have just done a TICKS_LIFE
            self.assertEqual(self.engine.life_cycle,
                             SystemTick.TICKS_LIFE)

            # If we're not in TICKS_LIFE cycle anymore, we're done here...
            if self.engine.life_cycle != SystemTick.TICKS_LIFE:
                # TODO: do we need to test/assert anything here?
                break

            # Make sure we ended at final game loop tick and are set up to wrap
            # back around to the starting game loop tick.
            self.assertEqual(self.engine.tick,
                             game_loop_end())
            self.assertEqual(self.engine._tick.next,
                             game_loop_start())

        return ran_ticks

    def _engine_run_end(self,
                        ticks: Dict[SystemTick, int]
                        ) -> Dict[SystemTick, int]:
        '''
        Do the engine's TICKS_DEATH life-cycle.

        Will run/verify each tick cycle in end for UP TO as many times as set
        in `ticks[<tick>]`.

        Will let the TICKS_DEATH life-cycle go for UP TO as many times as set
        in `ticks[SystemTick.TICKS_DEATH]`, or at a minimum once per start-up
        tick type (AUTOPHAGY, APOPTOSIS...).
        '''
        ran_ticks = {}
        self._in_shutdown = True

        # Don't care where we start out.
        # self.assertEqual(self.engine.life_cycle, SystemTick.INVALID)
        # self.assertEqual(self.engine.tick, SystemTick.INVALID)

        # Tick a maximum of: what's been requested, or the number of
        # end_ticks we have.

        end_ticks = (SystemTick.AUTOPHAGY,
                     SystemTick.APOPTOSIS,
                     SystemTick.NECROSIS,
                     SystemTick.FUNERAL)
        requested_ticks = ticks.get(SystemTick.TICKS_DEATH, None)
        if requested_ticks is not None:
            # Fail out with an explanation if unhappy.
            if len(end_ticks) > requested_ticks:
                self.fail("Currently don't support running less than one "
                          "tick per TICKS_DEATH tick. requested: "
                          f"{requested_ticks}, min: {len(end_ticks)}. "
                          f"End ticks: {end_ticks}")

        # Currently, NECROSIS can only be ticked once, so make sure of that.
        requested_necrosis = ticks.get(SystemTick.NECROSIS, 0)
        if requested_necrosis > 1:
            self.fail("Currently don't support running more than one "
                      "tick of NECROSIS. requested: "
                      f"{requested_necrosis}.")
        # Currently, FUNERAL can only be ticked once, so make sure of that.
        requested_funeral = ticks.get(SystemTick.FUNERAL, 0)
        if requested_funeral > 1:
            self.fail("Currently don't support running more than one "
                      "tick of FUNERAL. requested: "
                      f"{requested_funeral}.")

        # ---
        # Tick: Autophagy
        # ---
        # Tick AUTOPHAGY for up to as many times as requested.
        tick_num = ticks.get(SystemTick.AUTOPHAGY, 1)
        last_tick = tick_num - 1
        for i in range(tick_num):
            success = self.engine_tick()

            # Update our ticks counter...
            self._increment_tick_dict(
                ran_ticks,
                self.engine.life_cycle,
                self.engine.tick)

            self.assertTrue(success)
            self.assertEqual(self.engine.life_cycle,
                             SystemTick.TICKS_DEATH)
            self.assertEqual(self.engine.tick,
                             SystemTick.AUTOPHAGY)

            # Always in TICKS_DEATH after AUTOPHAGY. APOPTOSIS is next and
            # it's TICKS_DEATH too.
            self.assertEqual(self.engine._life_cycle.next,
                             SystemTick.TICKS_DEATH)
            if i == last_tick:
                # We MUST be headed for APOPTOSIS.
                self.assertEqual(self.engine._tick.next,
                                 SystemTick.APOPTOSIS)
            else:
                # We CAN be headed into APOPTOSIS, but staying in AUTOPHAGY is
                # also acceptable.
                self.assertIn(self.engine._tick.next,
                              (SystemTick.AUTOPHAGY, SystemTick.APOPTOSIS))
                if self.engine._tick.next != SystemTick.AUTOPHAGY:
                    break

        # ---
        # Tick: Apoptosis
        # ---
        # Tick APOPTOSIS for up to as many times as requested.
        tick_num = ticks.get(SystemTick.APOPTOSIS, 1)
        last_tick = tick_num - 1
        for i in range(tick_num):
            success = self.engine_tick()

            # Update our ticks counter...
            self._increment_tick_dict(
                ran_ticks,
                self.engine.life_cycle,
                self.engine.tick)

            self.assertTrue(success)
            self.assertEqual(self.engine.life_cycle,
                             SystemTick.TICKS_DEATH)
            self.assertEqual(self.engine.tick,
                             SystemTick.APOPTOSIS)

            # Always in TICKS_DEATH after APOPTOSIS. NECROSIS is next and
            # it's TICKS_DEATH too.
            self.assertEqual(self.engine._life_cycle.next,
                             SystemTick.TICKS_DEATH)
            if i == last_tick:
                # We MUST be headed for NECROSIS.
                self.assertEqual(self.engine._tick.next,
                                 SystemTick.NECROSIS)
            else:
                # We CAN be headed into NECROSIS, but staying in
                # APOPTOSIS is also acceptable.
                self.assertIn(self.engine._tick.next,
                              (SystemTick.APOPTOSIS, SystemTick.NECROSIS))
                if self.engine._tick.next != SystemTick.APOPTOSIS:
                    break

        # ---
        # Tick: The End
        # ---
        # Tick NECROSIS for up to as many times as requested.
        tick_num = ticks.get(SystemTick.NECROSIS, 1)
        if tick_num:
            success = False
            if tick_num != 1:
                self.fail("Got a request for NECROSIS != 1 tick. This is not "
                          "currently how the engine works. "
                          f"NECROSIS ticks: {tick_num}")
            else:
                # Do the one tick.
                success = self.engine_tick()

            # Update our ticks counter...
            self._increment_tick_dict(
                ran_ticks,
                self.engine.life_cycle,
                self.engine.tick)

            self.assertTrue(success)
            self.assertEqual(self.engine.life_cycle,
                             SystemTick.TICKS_DEATH)
            self.assertEqual(self.engine.tick,
                             SystemTick.NECROSIS)

            # Always in TICKS_DEATH/FUNERAL after TICKS_DEATH/NECROSIS.
            self.assertEqual(self.engine._life_cycle.next,
                             SystemTick.TICKS_DEATH)
            self.assertEqual(self.engine._tick.next,
                             SystemTick.FUNERAL)

        # ---
        # Tick: Funeral
        # ---
        # Tick Funeral for up to as many times as requested.
        tick_num = ticks.get(SystemTick.FUNERAL, 1)
        if tick_num:
            success = False
            if tick_num != 1:
                self.fail("Got a request for FUNERAL != 1 tick. This is not "
                          "currently how the engine works. "
                          f"FUNERAL ticks: {tick_num}")
            else:
                # Do the one tick.
                success = self.engine_tick()

            # Update our ticks counter...
            self._increment_tick_dict(
                ran_ticks,
                self.engine.life_cycle,
                self.engine.tick)

            self.assertTrue(success)
            self.assertEqual(self.engine.life_cycle,
                             SystemTick.TICKS_DEATH)
            self.assertEqual(self.engine.tick,
                             SystemTick.FUNERAL)

            # Always in FUNERAL|NECROSIS / FUNERAL|NECROSIS
            # after TICKS_DEATH/FUNERAL.
            self.assertEqual(self.engine._life_cycle.next,
                             SystemTick.FUNERAL | SystemTick.NECROSIS)
            self.assertEqual(self.engine._tick.next,
                             SystemTick.FUNERAL | SystemTick.NECROSIS)

        return ran_ticks
