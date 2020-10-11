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
        Run Engine through TICKS_START life-cycle.

        If `tick_amounts` is defined, this will use the number of ticks
        allowabled in TICKS_START, and in specific starting ticks (GENESIS,
        etc) as a maximum. See here for an example:
          veredi.game.zest_engine.ZestEngine.test_ticks_start()

        If `tick_amounts` is None, we will allow a whole lotta ticks and trust
        in the engine to timeout of TICKS_START if something is amiss.

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
                SystemTick.TICKS_START: self._ENGINE_TICKS_DEFAULT_START_END,

                # ---
                # Ticks
                # ---
                # Max ticks for each tick in TICKS_START.
                SystemTick.GENESIS:      self._ENGINE_TICKS_DEFAULT_START_END,
                SystemTick.INTRA_SYSTEM: self._ENGINE_TICKS_DEFAULT_START_END,
            }

        # If we fail starting the engine somewhere along the way, try to stop
        # it. Maybe some systems can run through shutdown and clean up for the
        # next test.
        #
        # Only an issue (so far) for multiprocess stuff, but we have that.
        try:
            return self.engine_run(SystemTick.TICKS_START,
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
        Sets up events and runs Engine through TICKS_START life-cycle.
          - Calls self.engine_life_start(`tick_amounts`)
          - Calls self.set_up_events()

        If `tick_amounts` is defined, this will use the number of ticks
        allowabled in TICKS_START, and in specific starting ticks (GENESIS,
        etc) as a maximum. See here for an example:
          veredi.game.zest_engine.ZestEngine.test_ticks_start()

        If `tick_amounts` is None, we will allow a whole lotta ticks and trust
        in the engine to timeout of TICKS_START if something is amiss.

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
        Sets up events and runs Engine through TICKS_START life-cycle.
        Calls:
          - self.engine_life_start(`tick_amounts`)
          - self.init_many_systems(*self._required_systems)
          - if not skip_event_setup:
            - self.set_up_events()
          - self.allow_registration()

        If `tick_amounts` is defined, this will use the number of ticks
        allowabled in TICKS_START, and in specific starting ticks (GENESIS,
        etc) as a maximum. See here for an example:
          veredi.game.zest_engine.ZestEngine.test_ticks_start()

        If `tick_amounts` is None, we will allow a whole lotta ticks and trust
        in the engine to timeout of TICKS_START if something is amiss.

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
        # Apoptosis mode, I suppose. Or maybe just apoptosis.
        # Structured death, basically.
        # ---
        # if (self.engine.life_cycle != SystemTick.INVALID
        #         and self.engine.life_cycle != SystemTick.FUNERAL):
        #     # Not dead yet, so do the TICKS_END life_cycle.
        #     self.engine_life_end()

        self.engine_ready = False
        self.engine = None
        super().tear_down()

    def engine_emergency_stop(self) -> None:
        '''
        Run engine through TICKS_END due to bad things happening.
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

        Run Engine through TICKS_END life-cycle.

        If `tick_amounts` is defined, this will use the number of ticks
        allowabled in TICKS_END, and in specific starting ticks (APOPTOSIS,
        etc) as a maximum. See here for an example:
          veredi.game.zest_engine.ZestEngine.test_ticks_end()

        If `tick_amounts` is None, we will allow a whole lotta ticks and trust
        in the engine to timeout of TICKS_END if something is amiss.

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
                SystemTick.TICKS_END: self._ENGINE_TICKS_DEFAULT_START_END,

                # ---
                # Ticks
                # ---
                # Max ticks for each tick in TICKS_END.
                SystemTick.APOPTOSIS:  self._ENGINE_TICKS_DEFAULT_START_END,
                SystemTick.APOCALYPSE: self._ENGINE_TICKS_DEFAULT_START_END,
                SystemTick.THE_END:    1,
                SystemTick.FUNERAL:    1,
            }

        # Stop engine, then send it through its ending life-cycle of ticks.
        self.engine.stop()
        return self.engine_run(SystemTick.TICKS_END,
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
            self.assertTrue(self.engine.running(),
                            ("ZestEngine thinks engine is in shutdown, but "
                             "Engine is not running() (anymore?). "
                             f"Tick is: {self.engine.tick}, engine health is: "
                             f"{str(self.engine.engine_health)} "
                             "tick health is: "
                             f"{str(self.engine.tick_health)}"))

        emergency_stop = False
        for i in range(amount):
            health = self.engine.run_tick()
            # health == None means engine refused to run a tick due to being in
            # a bad state. If we are in shutdown, no point doing emergency
            # stop. But otherwise, try to have the engine do it's TICKS_END so
            # things have a chance to clean up.
            if not self.engine.running():
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

        For TICKS_START/TICKS_END, can specify (the maximum number of) each
        individual tick.

        For TICKS_RUN, the individual ticks will be ignored in `tick_amounts`.

        Returns a dictionary of number of ticks/life-cycles actually ran.
        '''
        result = {}

        # ---
        # Run a vaild life-cycle or error.
        # ---
        if run_life_cycle == SystemTick.TICKS_START:
            result = self._engine_run_start(tick_amounts)
            self._engine_check()
        elif run_life_cycle == SystemTick.TICKS_RUN:
            self._engine_check()
            result = self._engine_run_run(tick_amounts)
        elif run_life_cycle == SystemTick.TICKS_END:
            if self.engine.tick != SystemTick.THE_END:
                self._engine_check()
            result = self._engine_run_end(tick_amounts)
        else:
            self.assertIn(run_life_cycle,
                          (SystemTick.TICKS_START,
                           SystemTick.TICKS_RUN,
                           SystemTick.TICKS_END))

        return result

    def _engine_check(self) -> None:
        '''
        Checks engine_ready, self.engine.life_cycle, and self.reg_open.
        '''
        if (self.engine_ready
                and (self.engine.life_cycle == SystemTick.INVALID
                     or self.engine.life_cycle == SystemTick.TICKS_START)):
            self.fail("We think engine is ready but it is not past "
                      "TICKS_START life-cycle. Engine is already set up, "
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
        Do the engine's TICKS_START life-cycle.

        Will run/verify each tick cycle in start for UP TO as many times as set
        in `ticks[<tick>]`.

        Will let the TICKS_START life-cycle go for UP TO as many times as set
        in `ticks[SystemTick.TICKS_START]`, or at a minimum once per start-up
        tick type (GENESIS, INTRA_SYSTEM...).
        '''
        ran_ticks = {}
        self.assertEqual(self.engine.life_cycle, SystemTick.INVALID)
        self.assertEqual(self.engine.tick, SystemTick.INVALID)

        # Tick a maximum of: what's been requested, or the number of
        # start_ticks we have.

        start_ticks = (SystemTick.GENESIS, SystemTick.INTRA_SYSTEM)
        requested_ticks = ticks.get(SystemTick.TICKS_START, None)
        if requested_ticks is not None:
            # Fail out with an explanation if unhappy.
            if len(start_ticks) > requested_ticks:
                self.fail("Currently don't support running less than one "
                          "tick per TICKS_START tick. requested: "
                          f"{requested_ticks}, min: {len(start_ticks)}. "
                          f"Start-up ticks: {start_ticks}")

        # ---
        # Tick: Genesis
        # ---
        # Tick GENESIS for up to as many times as requested.
        tick_num = ticks.get(SystemTick.GENESIS, 1)
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
                             SystemTick.TICKS_START)
            self.assertEqual(self.engine.tick,
                             SystemTick.GENESIS)

            # Always in TICKS_START after GENESIS. INTRA_SYSTEM is next and
            # it's TICKS_START too.
            self.assertEqual(self.engine._life_cycle.next,
                             SystemTick.TICKS_START)
            # We MUST be headed for INTRA_SYSTEM.
            if i == last_tick:
                self.assertEqual(self.engine._tick.next,
                                 SystemTick.INTRA_SYSTEM)

            # We CAN be headed into INTRA_SYSTEM, but staying in GENESIS is
            # also acceptable.
            else:
                self.assertIn(self.engine._tick.next,
                              start_ticks)
                if self.engine._tick.next != SystemTick.GENESIS:
                    break

        # ---
        # Tick: Intra-system
        # ---
        # Tick INTRA_SYSTEM for up to as many times as requested.
        tick_num = ticks.get(SystemTick.INTRA_SYSTEM, 1)
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
                             SystemTick.TICKS_START)
            self.assertEqual(self.engine.tick,
                             SystemTick.INTRA_SYSTEM)

            if i == last_tick:
                # We MUST be headed for TICKS_RUN & TIME.
                self.assertEqual(self.engine._life_cycle.next,
                                 SystemTick.TICKS_RUN)
                self.assertEqual(self.engine._tick.next,
                                 SystemTick.TIME)
            else:
                # We CAN be headed into TICKS_RUN & TIME, but staying in
                # TICKS_START & INTRA_SYSTEM is also acceptable.
                if self.engine._life_cycle.next == SystemTick.TICKS_START:
                    self.assertEqual(self.engine._life_cycle.next,
                                     SystemTick.TICKS_START)
                    self.assertEqual(self.engine._tick.next,
                                     SystemTick.INTRA_SYSTEM)

                elif self.engine._life_cycle.next == SystemTick.TICKS_RUN:
                    self.assertEqual(self.engine._life_cycle.next,
                                     SystemTick.TICKS_RUN)
                    self.assertEqual(self.engine._tick.next,
                                     SystemTick.TIME)
                    break

                else:
                    # In a bad place. Fail out.
                    self.assertIn(self.engine._life_cycle.next,
                                  (SystemTick.TICKS_START,
                                   SystemTick.TICKS_RUN))

        return ran_ticks

    def _engine_run_run(self,
                        ticks: Dict[SystemTick, int]
                        ) -> Dict[SystemTick, int]:
        '''
        Do some normal engine game-loops.

        Will run up to `ticks[TICKS_RUN]` number of ticks. Will stop early if
        engine is exiting TICKS_RUN.
        '''
        ran_ticks = {
            SystemTick.TICKS_RUN: 0,

            SystemTick.TIME: 0,
            SystemTick.CREATION: 0,
            SystemTick.PRE: 0,
            SystemTick.STANDARD: 0,
            SystemTick.POST: 0,
            SystemTick.DESTRUCTION: 0,
        }
        # Must be about to run first tick of a game-loop in order to run.
        self.assertEqual(self.engine._life_cycle.next, SystemTick.TICKS_RUN)
        self.assertEqual(self.engine._tick.next, SystemTick.TIME)

        # Tick a maximum of: what's been requested, or until engine says it's
        # not going to be in TICKS_RUN anymore.
        requested_ticks = ticks.get(SystemTick.TICKS_RUN, None)
        if not requested_ticks or requested_ticks < 1:
            self.fail("Can only run one or more TICKS_RUN cycles. Requested: "
                      f"{requested_ticks}. ")

        for i in range(requested_ticks):
            success = self.engine_tick()

            # Update our ticks counter...
            # Assume we ran one of each standard tick in the TICKS_RUN cycle,
            ran_list = [each[0] for each in _GAME_LOOP_SEQUENCE]
            # and get the actual cycle we ran.
            ran_list.append(self.engine.life_cycle)
            self._increment_tick_dict(
                ran_ticks,
                *ran_list)

            self.assertTrue(success)

            # Should have just done a TICKS_RUN
            self.assertEqual(self.engine.life_cycle,
                             SystemTick.TICKS_RUN)

            # If we're not in TICKS_RUN cycle anymore, we're done here...
            if self.engine.life_cycle != SystemTick.TICKS_RUN:
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
        Do the engine's TICKS_END life-cycle.

        Will run/verify each tick cycle in end for UP TO as many times as set
        in `ticks[<tick>]`.

        Will let the TICKS_END life-cycle go for UP TO as many times as set
        in `ticks[SystemTick.TICKS_END]`, or at a minimum once per start-up
        tick type (APOPTOSIS, APOCALYPSE...).
        '''
        ran_ticks = {}
        self._in_shutdown = True

        # Don't care where we start out.
        # self.assertEqual(self.engine.life_cycle, SystemTick.INVALID)
        # self.assertEqual(self.engine.tick, SystemTick.INVALID)

        # Tick a maximum of: what's been requested, or the number of
        # end_ticks we have.

        end_ticks = (SystemTick.APOPTOSIS,
                     SystemTick.APOCALYPSE,
                     SystemTick.THE_END,
                     SystemTick.FUNERAL)
        requested_ticks = ticks.get(SystemTick.TICKS_END, None)
        if requested_ticks is not None:
            # Fail out with an explanation if unhappy.
            if len(end_ticks) > requested_ticks:
                self.fail("Currently don't support running less than one "
                          "tick per TICKS_END tick. requested: "
                          f"{requested_ticks}, min: {len(end_ticks)}. "
                          f"End ticks: {end_ticks}")

        # Currently, THE_END can only be ticked once, so make sure of that.
        requested_the_end = ticks.get(SystemTick.THE_END, 0)
        if requested_the_end > 1:
            self.fail("Currently don't support running more than one "
                      "tick of THE_END. requested: "
                      f"{requested_the_end}.")
        # Currently, FUNERAL can only be ticked once, so make sure of that.
        requested_funeral = ticks.get(SystemTick.FUNERAL, 0)
        if requested_funeral > 1:
            self.fail("Currently don't support running more than one "
                      "tick of FUNERAL. requested: "
                      f"{requested_funeral}.")

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
                             SystemTick.TICKS_END)
            self.assertEqual(self.engine.tick,
                             SystemTick.APOPTOSIS)

            # Always in TICKS_END after APOPTOSIS. APOCALYPSE is next and
            # it's TICKS_END too.
            self.assertEqual(self.engine._life_cycle.next,
                             SystemTick.TICKS_END)
            if i == last_tick:
                # We MUST be headed for APOCALYPSE.
                self.assertEqual(self.engine._tick.next,
                                 SystemTick.APOCALYPSE)
            else:
                # We CAN be headed into APOCALYPSE, but staying in APOPTOSIS is
                # also acceptable.
                self.assertIn(self.engine._tick.next,
                              (SystemTick.APOPTOSIS, SystemTick.APOCALYPSE))
                if self.engine._tick.next != SystemTick.APOPTOSIS:
                    break

        # ---
        # Tick: Apocalypse
        # ---
        # Tick APOCALYPSE for up to as many times as requested.
        tick_num = ticks.get(SystemTick.APOCALYPSE, 1)
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
                             SystemTick.TICKS_END)
            self.assertEqual(self.engine.tick,
                             SystemTick.APOCALYPSE)

            # Always in TICKS_END after APOCALYPSE. THE_END is next and
            # it's TICKS_END too.
            self.assertEqual(self.engine._life_cycle.next,
                             SystemTick.TICKS_END)
            if i == last_tick:
                # We MUST be headed for THE_END.
                self.assertEqual(self.engine._tick.next,
                                 SystemTick.THE_END)
            else:
                # We CAN be headed into THE_END, but staying in
                # APOCALYPSE is also acceptable.
                self.assertIn(self.engine._tick.next,
                              (SystemTick.APOCALYPSE, SystemTick.THE_END))
                if self.engine._tick.next != SystemTick.APOCALYPSE:
                    break

        # ---
        # Tick: The End
        # ---
        # Tick THE_END for up to as many times as requested.
        tick_num = ticks.get(SystemTick.THE_END, 1)
        if tick_num:
            success = False
            if tick_num != 1:
                self.fail("Got a request for THE_END != 1 tick. This is not "
                          "currently how the engine works. "
                          f"THE_END ticks: {tick_num}")
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
                             SystemTick.TICKS_END)
            self.assertEqual(self.engine.tick,
                             SystemTick.THE_END)

            # Always in TICKS_END/FUNERAL after TICKS_END/THE_END.
            self.assertEqual(self.engine._life_cycle.next,
                             SystemTick.TICKS_END)
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
                             SystemTick.TICKS_END)
            self.assertEqual(self.engine.tick,
                             SystemTick.FUNERAL)

            # Always in FUNERAL|THE_END / FUNERAL|THE_END
            # after TICKS_END/FUNERAL.
            self.assertEqual(self.engine._life_cycle.next,
                             SystemTick.FUNERAL | SystemTick.THE_END)
            self.assertEqual(self.engine._tick.next,
                             SystemTick.FUNERAL | SystemTick.THE_END)

        return ran_ticks
