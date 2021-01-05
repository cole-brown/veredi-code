# coding: utf-8

'''
Timing info for game.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, NewType, Tuple, Dict
from veredi.base.null import NullNoneOr

import numbers
from datetime import datetime
from decimal import Decimal

from veredi.logger           import log
from veredi.base.assortments import CurrentNext, DeltaNext
from veredi.data             import background
from veredi.data.exceptions  import ConfigError
from veredi.base.const       import VerediHealth
from veredi.debug.const      import DebugFlag

from .const                  import SystemTick
from .manager                import EcsManager
from .base.exceptions        import EcsSystemError

from veredi.time.machine     import MachineTime
from veredi.time.timer       import MonotonicTimer
from ..time.clock            import Clock
from ..time.tick.round       import TickRounds, TickTypes


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO [2020-06-29]: Move time classes to time module.

TimerInput = NewType('TimerInput', Union[MonotonicTimer, str, None])
TimeoutInput = NewType('TimeoutInput', Union[str, float, int, None])


# --------------------------------TimeManager----------------------------------
# --                               Dr. Time?                                 --
# ------------------------------"Just the Time."-------------------------------

class TimeManager(EcsManager):
    '''
    This class has the potential to be saved to data fields. Let it control its
    timezones. Convert to user-friendly elsewhere.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    _DEFAULT_TICK_STEP = Decimal(6)
    _DEFAULT_TIMEOUT_SEC = 10
    _SHORT_TIMEOUT_SEC = 1

    _METER_TIMEOUT_NS = MachineTime.sec_to_ns(_DEFAULT_TICK_STEP * 4)

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        super()._define_vars()

        self.clock: Clock = Clock()
        '''
        'Game Time' clock. For any in-game time tracking needed.
        DOES NOT:
          - Change itself over time.
          - Track/follow real calendar/time.

        Defaults to midnight (00:00:00.0000) of current UTC date.
        '''

        self.tick: TickRounds = None
        '''
        'Game Tick' timer. Keeps track of number of ticks, 'game time' per
        tick, etc.
        '''

        self._engine_tick: CurrentNext[SystemTick] = None
        '''
        Engine's current/next tick. 'next' will likely not be accurate as it is
        set by the engine whenever it feels like it - usually at the end of a
        tick.

        Should be a specific tick like:
          SystemTick.GENESIS
          SystemTick.STANDARD

        Do not ever set current/next.
        '''

        self._engine_life_cycle: CurrentNext[SystemTick] = None
        '''
        Engine's current/next Life-Cycle. 'next' will likely not be accurate as
        it is set by the engine whenever it feels like it - usually at the end
        of a tick.

        Should be a group of ticks like:
          SystemTick.TICKS_START
          SystemTick.TICKS_RUN
          SystemTick.TICKS_END

        Do not ever set current/next.
        '''

        self.machine: MachineTime = MachineTime()
        '''
        Computer's time. Real-world, actual time.
        '''

        self._timers: Dict[str, MonotonicTimer] = {}
        '''
        Timers for things, registered by some sort of name string.
        Dotted maybe.
        '''

        self._timer_name_default: str = None
        '''
        Name of the default timer.
        '''

    def __init__(self,
                 tick_amount: Optional[TickTypes] = None,
                 debug_flags: NullNoneOr[DebugFlag] = None) -> None:
        super().__init__(debug_flags)

        # TODO: Get our clocks, ticks, etc from config data?

        # defaults to zero start time, _DEFAULT_TICK_STEP tick step
        # zero is not an allowed tick amount so...
        tick_amount = tick_amount or self._DEFAULT_TICK_STEP
        if tick_amount <= 0:
            self.log_error("tick_amount should be `None` or a "
                           "non-zero, positive amount.")
            raise EcsSystemError("tick_amount should be `None` or a "
                                 "non-zero, positive amount.",
                                 None, None)
        self.tick  = TickRounds(tick_amount)

        self.machine = MachineTime()

    def engine_init(self,
                    cn_ticks:     CurrentNext[SystemTick],
                    cn_life:      CurrentNext[SystemTick],
                    timers:       Optional[Dict[str, MonotonicTimer]] = None,
                    default_name: Optional[str]                       = None
                    ) -> None:
        '''
        Engine will give us a pointer to its ticks/life-cycle objects so we can
        have getters.

        Do not ever set these ourself.

        `timers` and `default_name` will be used to populate our timers and set
        our default timer, if provided.
        '''
        self._engine_tick = cn_ticks
        self._engine_life_cycle = cn_life

        valid_default_name = False
        if timers:
            for name in timers:
                self._timers[name] = timers[name]
                if name == default_name:
                    valid_default_name = True

        if default_name:
            if not valid_default_name:
                msg = (f"default name '{default_name}' not found in "
                       "provided timers.")
                error = KeyError(default_name, msg, timers)
                raise self._log_exception(error,
                                          msg + ' timers: {}', timers)
            else:
                self._timer_name_default = default_name

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @classmethod
    def dotted(klass: 'TimeManager') -> str:
        '''
        The dotted name this Manager has.
        '''
        return 'veredi.game.ecs.manager.time'

    def get_background(self):
        '''
        Data for the Veredi Background context.
        '''
        return {
            background.Name.DOTTED.key: self.dotted(),
        }

    # ---
    # Engine's Ticks / Life-Cycles
    # ---

    @property
    def engine_tick_current(self) -> SystemTick:
        '''Get engine's current tick.'''
        if not self._engine_tick:
            return SystemTick.INVALID
        return self._engine_tick.current

    # Almost never valid, so... do we want to expose it?
    # Don't think so right now.
    # @property
    # def engine_tick_next(self) -> SystemTick:
    #     '''Get engine's next tick. This is hardly ever valid.'''
    #     return self._engine_tick.current

    @property
    def engine_life_cycle_current(self) -> SystemTick:
        '''Get engine's current life-cycle.'''
        if not self._engine_life_cycle:
            return SystemTick.INVALID
        return self._engine_life_cycle.current

    # Almost never valid, so... do we want to expose it?
    # Don't think so right now.
    # @property
    # def engine_life_cycle_next(self) -> SystemTick:
    #     '''Get engine's next life-cycle. This is hardly ever valid.'''
    #     return self._engine_tick.current

    # ---
    # Timer
    # ---

    def make_timer(self,
                   save_name:  Optional[str]  = None,
                   is_default: Optional[bool] = False) -> MonotonicTimer:
        '''
        Returns a new, realtime MonotonicTimer.

        If `save_name` is provided, TimeManager will save the timer into its
        dictionary. If a timer already exists with that name, this will throw a
        ValueError.


        If `is_default` is set and `save_name` is set, the timer's name will be
        saved to `self._timer_name_default` and used as the default in timer
        functions.

        Returns the timer created.
        '''
        timer = MonotonicTimer()
        if save_name:
            if save_name in self._timers:
                msg = (f"{self.__class__.__name__}.make_timer: Timer "
                       f"'{save_name}' already exists in our dictionary "
                       f"of timers. Cannot overwrite. {self._timers}")
                error = ValueError(msg, save_name, self._timers)
                raise self._log_exceptions(error, msg)
            self._timers[save_name] = timer

            # Now, we have a valid name and a timer. Is it the default?
            # If so, just set our default name - overwriting any previous.
            if is_default:
                if self._timer_name_default:
                    self._log_warning("Changing default timer from: "
                                      f"{self._timer_name_default} to "
                                      f"{save_name}.")
                self._timer_name_default = save_name

        return timer

    def get_timer(self, timer: TimerInput) -> MonotonicTimer:
        '''
        Returns a timer. If supplied with a timer, just returns it.

        If supplied with a string, looks for a timer with that name in the
        timers collection.

        If nothing is supplied, uses the default timer.

        What the timer is and what it does are decided by whoever made/controls
        it. Probably the Engine, in the default timer's case.

        If no timer is found, raises KeyError.

        Use make_timer() if you need your own timer for special cases.
        '''
        # 'timer' is an ok param name for callers who don't care, but for in
        # here, I want to tell what's what.
        timer_input = timer
        timer_output = None

        # Timer input param is Falsy - try to use our default timer.
        if not timer_input:
            if self._timer_name_default:
                timer_output = self._timers[self._timer_name_default]
            else:
                msg = ("get_timer(): No 'timer' supplied and no default timer "
                       f"exists. timer: {timer_input}, default_timer_name: "
                       f"{self._timer_name_default}")
                error = KeyError(timer_input, msg)
                raise self._log_exception(error, msg + ' timers: {}',
                                          self._timers)

        # No-op - allow callers to work equally well with actual timers and
        # timer names.
        elif isinstance(timer_input, MonotonicTimer):
            # We're a helper function so... just be hepful and give it back.
            timer_output = timer_input

        # Find a timer by name.
        elif isinstance(timer_input, str):
            timer_output = self._timers.get(timer_input, None)

            if not timer_output:
                msg = (f"get_timer(): No timer found for name '{timer_input}' "
                       "in timer collection.")
                error = KeyError(timer_input, msg)
                raise self._log_exception(error, msg + ' timers: {}',
                                          self._timers)

        # timer_input wasn't understood - error out.
        else:
            msg = (f"{self.__class__.__name__}.get_timer: No timer found for "
                   f"input '{timer_input}'.")
            error = ValueError(msg, timer_input, self._timers)
            raise self._log_exceptions(error, msg)

        # We got here, so success! Give back valid timer.
        return timer_output

    def start_timeout(self, timer: TimerInput) -> None:
        '''
        Calls `get_timer(timer)` on str/timer/None provided. See `get_timer`
        for details.
        TL;DR:
          - None  -> Get/use default timer.
          - str   -> Get/use timer by name.
          - timer -> Use that timer.

        Starts timing with that timer.
        '''
        timer = self.get_timer(timer)
        timer.start()

    def end_timeout(self, timer: TimerInput) -> float:
        '''
        Calls `get_timer(timer)` on str/timer/None provided. See `get_timer`
        for details.
        TL;DR:
          - None  -> Get/use default timer.
          - str   -> Get/use timer by name.
          - timer -> Use that timer.

        Stops timing with that timer and returns timer.elapsed property value.
        '''
        timer = self.get_timer(timer)
        timer.end()
        elapsed = timer.elapsed
        timer.reset()
        return elapsed

    @property
    def timing(self, timer: TimerInput):
        '''
        Not stopped and have a start time means probably timing something.
        '''
        return self._timer.timing

    def is_timed_out(self,
                     timer:   TimerInput,
                     timeout: TimeoutInput = None) -> bool:
        '''
        Calls `get_timer(timer)` on str/timer/None provided. See `get_timer`
        for details.
        TL;DR:
          - None  -> Get/use default timer.
          - str   -> Get/use timer by name.
          - timer -> Use that timer.

        If `timeout` is None, uses _DEFAULT_TIMEOUT_SEC.
        If `timeout` is a number, uses that.
        If `timeout` is a string, checks config for a setting associated with
        that key under the TimeManager's settings.

        Returns true if timeout timer is:
          - Not timing.
          - Past timeout value.
            - (Past _DEFAULT_TIMEOUT_SEC if timeout value is None.)
        '''
        # ------------------------------
        # Get a Timer based on input.
        # ------------------------------
        check_timer = self.get_timer(timer)
        if not check_timer:
            msg = ("is_timed_out() requires a timer or timer name. "
                   f"Got '{timer}' which didn't resolve to a timer: "
                   f"{check_timer}")
            raise self._log_exception(ValueError(msg, timer, timeout),
                                      msg + f", timeout: {timeout}")
        # Verified it, so we can assign it `timer` since we don't need to know
        # what the input value was anymore.
        timer = check_timer

        # Not timing - not sure? Returning timed out is a good bet for figuring
        # out who forgot to start their timer, so use that.
        if not timer.timing:
            return True

        # ------------------------------
        # Figure out the timeout.
        # ------------------------------
        if timeout and isinstance(timeout, str):
            config = background.config.config
            if not config:
                self._log_info("TimeManager cannot get config for checking "
                               "timeout value of '{}'",
                               timeout)
                timeout = self._DEFAULT_TIMEOUT_SEC
            else:
                try:
                    timeout = config.get('engine', 'time', 'timeouts', timeout)
                    # If it's not a number and falsy, set to default.
                    if not isinstance(timeout, numbers.Number) and not timeout:
                        timeout = self._DEFAULT_TIMEOUT_SEC
                    # If it's not a float, (try to) convert it to one.
                    if not isinstance(timeout, float):
                        timeout = float(timeout)
                except ConfigError:
                    self._log_info("TimeManager cannot get config "
                                   "for checking timeout value of '{}'",
                                   timeout)
                    timeout = self._DEFAULT_TIMEOUT_SEC

            # Timeout should be a float now.

        # ------------------------------
        # Use default?
        # ------------------------------
        if not timeout or timeout <= 0:
            timeout = self._DEFAULT_TIMEOUT_SEC

        # ------------------------------
        # Now we can finally check if timed out.
        # ------------------------------
        timed_out = timer.timed_out(timeout)
        return timed_out

    # ---
    # Ticking Time
    # ---

    def step(self) -> Decimal:
        return self.tick.step()

    # ---
    # Getters & Setters - Game Time
    # ---

    @property
    def seconds(self) -> Decimal:
        return self.tick.seconds

    @seconds.setter
    def seconds(self, value: TickTypes) -> None:
        self.tick.seconds = value

    @property
    def tick_num(self) -> int:
        return self.tick.tick_num

    @tick_num.setter
    def tick_num(self, value: int) -> None:
        self.tick.tick_num = value

    @property
    def datetime(self) -> datetime:
        return self.clock.datetime

    @datetime.setter
    def datetime(self, value: datetime) -> None:
        self.clock.datetime = value

    @property
    def error_game_time(self) -> str:
        '''
        Returns tick, tick num, machine time.
        '''
        return (f"Time: {self.seconds} tick seconds, "
                f"{self.tick_num} tick number, "
                f"{self.machine.stamp_to_str()}")

    # ---
    # Getters - System Time
    # ---

    # Use self.machine.jeff()

    # ---
    # Logging Despamifier Help
    # ---

    def metered(self, meter: Optional[int]) -> Tuple[bool, int]:
        '''
        Takes in a `metered` value from last call.
        Returns a tuple of:
          - bool:  True if meter is up and you can do a thing.
                   False if you should keep not doing a thing.
          - value: Meter value from last time we said you could do a thing.
                   You don't have to care about this; just keep passing and
                   updating it like:
                     do_the_thing, idk = self._time_manager.metered(idk)
                     if do_the_thing:
                         self.the_thing()
        '''
        # Zero or None? Allow log and init to "now".
        if not meter:
            return True, self.machine.monotonic_ns

        # Do the math; return true/future or false/past.
        now = self.machine.monotonic_ns
        if now > meter + self._METER_TIMEOUT_NS:
            return True, now
        return False, meter

    # -------------------------------------------------------------------------
    # Reduced Ticking
    # -------------------------------------------------------------------------

    def set_reduced_tick_rate(self,
                              tick: SystemTick,
                              rate: int,
                              reduced: Dict[SystemTick, DeltaNext]) -> None:
        '''
        Set an entry into the provided reduced tick rate dict. This does
        nothing on its own. Callers must also use `is_reduced_tick()` to check
        for if/when they want to do their reduced processing.
        '''
        reduced[tick] = DeltaNext(rate,
                                  self.tick_num)

    def is_reduced_tick(self,
                        tick:    SystemTick,
                        reduced: Dict[SystemTick, DeltaNext]) -> bool:
        '''
        Checks to see if this tick is the reduced-tick-rate tick.
        '''
        reduced_tick = reduced.get(tick, None)
        if not reduced_tick:
            return False

        if self.tick_num >= reduced_tick.next:
            # Update our DeltaNext to the next reduced tick number.
            reduced_tick.cycle(self.tick_num)
            return True

        return False

    # -------------------------------------------------------------------------
    # Life-Cycle Transitions
    # -------------------------------------------------------------------------

    def _cycle_apoptosis(self) -> VerediHealth:
        '''
        Game is ending gracefully. Be responsive and still alive in apoptosis.

        Default: do nothing and return that we're done with a successful
        apoptosis.
        '''
        return VerediHealth.APOPTOSIS_SUCCESSFUL

    def _cycle_apocalypse(self) -> VerediHealth:
        '''
        Game is ending gracefully. Systems are now shutting down, goinging
        unresponsive, whatever. The managers should probably still be up and
        alive until the very end, though.

        Default: do nothing and return that we're done with the apocalypse.
        '''
        return VerediHealth.APOCALYPSE_DONE

    def _cycle_the_end(self) -> VerediHealth:
        '''
        Game is at the end. This is called once. Managers can probably die
        out now.

        Default: do nothing and return that we're done with a successful
        end of the world as we know it.
        '''
        return VerediHealth.THE_END
