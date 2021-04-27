# coding: utf-8

'''
Timing info for game.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, Optional, Union, NewType, Tuple, Dict
from veredi.base.null import NullNoneOr, null_or_none
if TYPE_CHECKING:
    from ..data.manager      import DataManager

from decimal import Decimal


from veredi.base.strings       import label
from veredi.base.strings.mixin import NamesMixin
from veredi.base.assortments   import CurrentNext, DeltaNext
from veredi.base.context       import UnitTestContext
from veredi.data               import background
from veredi.data.exceptions    import ConfigError
from veredi.base.const         import VerediHealth
from veredi.debug.const        import DebugFlag

from .const                    import SystemTick
from .manager                  import EcsManager

from veredi.time.machine       import MachineTime
from veredi.time.timer         import MonotonicTimer
from veredi                    import time
from ..time.clock              import Clock
from ..time.tick.round         import TickBase


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO [2020-06-29]: Move time classes to time module.

TimerInput = NewType('TimerInput', Union[MonotonicTimer, str, None])
TimeoutInput = NewType('TimeoutInput', Union[str, float, int, None])


# --------------------------------TimeManager----------------------------------
# --                               Dr. Time?                                 --
# ------------------------------"Just the Time."-------------------------------

class TimeManager(EcsManager,
                  name_dotted='veredi.game.ecs.manager.time',
                  name_string='manager.time'):
    '''
    This class has the potential to be saved to data fields. Let it control its
    timezones. Convert to user-friendly elsewhere.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    _DEFAULT_TIMEOUT_SEC = 10
    _SHORT_TIMEOUT_SEC = 1

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        super()._define_vars()

        # TODO: Reorder? Underscores first?

        self._bg_data: Dict[Any, Any] = {}
        '''
        Our background context info. Store it so we can add more to it as
        needed.
        '''

        self.clock: Clock = Clock()
        '''
        'Game Time' clock. For any in-game time tracking needed.
        DOES NOT:
          - Change itself over time.
          - Track/follow real calendar/time.

        Defaults to midnight (00:00:00.0000) of current UTC date.
        '''

        self.tick: TickBase = None
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
          SystemTick.SYNTHESIS
          SystemTick.STANDARD

        Do not ever set current/next.
        '''

        self._engine_life_cycle: CurrentNext[SystemTick] = None
        '''
        Engine's current/next Life-Cycle. 'next' will likely not be accurate as
        it is set by the engine whenever it feels like it - usually at the end
        of a tick.

        Should be a group of ticks like:
          SystemTick.TICKS_BIRTH
          SystemTick.TICKS_LIFE
          SystemTick.TICKS_DEATH

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
                 debug_flags: NullNoneOr[DebugFlag] = None) -> None:
        super().__init__(debug_flags)

        self.machine = MachineTime()

    def finalize_init(self,
                      data_manager: 'DataManager',
                      _unit_test:   Optional['UnitTestContext'] = None
                      ) -> None:
        '''
        Complete any init/config that relies on other Managers.
        '''
        # ---
        # Get our clocks, ticks, etc from config/definitions/saves.
        # ---
        # Have to wait on this one due to needing definitions/saves, which
        # DataManager is in charge of.
        self._configure(data_manager, _unit_test)
        self._finalize_background()

    def _configure(self,
                   data_manager: 'DataManager',
                   _ut_context:   Optional['UnitTestContext'] = None
                   ) -> None:
        '''
        Make our stuff from context/config data.

        NOTE: REQUIRES DataManager to be initialized!
        NOTE: DataManager may not be in background yet!
        '''
        # ------------------------------
        # UNIT-TEST HACKS
        # ------------------------------
        if isinstance(_ut_context, UnitTestContext):
            # If constructed specifically with a UnitTestContext, don't do
            # _configure() as we have no DataManager.
            ctx = _ut_context.sub_get(self.dotted)
            self.tick = ctx['tick']
            return

        # ------------------------------
        # Config Stuff
        # ------------------------------
        config = background.config.config(self.klass,
                                          self.dotted,
                                          None)
        # No config stuff at the moment.

        # ------------------------------
        # Grab Game Rules from DataManager.
        # ------------------------------
        # Game Rules has the game's definition data, which we need to know what
        # tick to use.
        rules = data_manager.game
        key_ticker = ('time', 'tick')  # definition.game -> time.tick
        ticker_dotted = rules.definition.get(*key_ticker)
        self.tick = config.create_from_label(ticker_dotted)
        if not self.tick:
            raise background.config.exception(
                None,
                "Failed to create our Tick object from the game rules "
                "Definition data: key: {}, value: {}, tick: {}",
                key_ticker, ticker_dotted, self.tick)

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

    def get_background(self) -> None:
        '''
        Data for the Veredi Background context.
        '''
        if not self._bg_data:
            # Init our data.
            self._bg_data = {
                background.Name.DOTTED.key: self.dotted,
                'clock': {
                    'dotted': self.clock.dotted,
                },
                # 'tick': Don't add 'tick' until finalize_background().
                'engine': {
                    'tick': self._engine_tick,
                    'life-cycle': self._engine_life_cycle,
                },
                'machine': {
                    'dotted': self.machine.dotted,
                },
            }

        return self._bg_data

    def _finalize_background(self) -> None:
        '''
        Add stuff from finalize_init() to our background data.
        '''
        self._bg_data['tick'] = self.tick.get_background()

    # -------------------------------------------------------------------------
    # Engine's Ticks / Life-Cycles
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Timer
    # -------------------------------------------------------------------------

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
                msg = (f"{self.klass}.make_timer: Timer "
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
            msg = (f"{self.klass}.get_timer: No timer found for "
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
            config = background.config.config(self.klass,
                                              self.dotted,
                                              None,
                                              raises_error=False)
            if not config:
                self._log_info("TimeManager cannot get config for checking "
                               "timeout value of '{}'",
                               timeout)
                timeout = self._DEFAULT_TIMEOUT_SEC
            else:
                try:
                    timeout = config.get('engine', 'time', 'timeouts', timeout)
                    if null_or_none(timeout):
                        timeout_dotted = label.normalize('engine',
                                                         'time',
                                                         'timeouts',
                                                         timeout)
                        self._log_warning("TimeManager didn't find timeout "
                                          f"for '{timeout_dotted}' in the "
                                          "config.")
                        timeout = self._DEFAULT_TIMEOUT_SEC

                    # If it's not a duration, set to the default.
                    elif not time.is_duration(timeout):
                        timeout = self._DEFAULT_TIMEOUT_SEC

                    # If it's not a float, (try to) convert it to one.
                    if not isinstance(timeout, float):
                        timeout = time.to_float(timeout)
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

    # -------------------------------------------------------------------------
    # Ticking Time
    # -------------------------------------------------------------------------

    def delta(self) -> Decimal:
        '''
        Ticks our tick object one delta.
        '''
        return self.tick.delta()

    @property
    def count(self) -> int:
        '''
        Returns the number of delta ticks since the engine started ticking us.
        Returns negative if we haven't started doing anything yet or if we
        don't even have our tick object yet.
        '''
        return (self.tick.count
                if self.tick else
                -1)

    # -------------------------------------------------------------------------
    # Error Helper
    # -------------------------------------------------------------------------

    @property
    def error_game_time(self) -> str:
        '''
        Returns tick info and machine time for error string information.
        '''
        return (f"{self.dotted}: "
                f"{str(self.tick)}, "
                f"{self.machine.stamp_to_str()}")

    @property
    def error_game_data(self) -> str:
        '''
        Returns tick info, machine time, etc as a dict for error info (e.g. in
        a VerediError.data dict).
        '''
        # Update our background data and return that as useful error data.
        return self._bg_data_current()

    # -------------------------------------------------------------------------
    # System Time
    # -------------------------------------------------------------------------

    # Use self.machine.jeff()

    # -------------------------------------------------------------------------
    # Logging Despamifier Help
    # -------------------------------------------------------------------------

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
                                  self.count)

    def is_reduced_tick(self,
                        tick:    SystemTick,
                        reduced: Dict[SystemTick, DeltaNext]) -> bool:
        '''
        Checks to see if this tick is the reduced-tick-rate tick.
        '''
        reduced_tick = reduced.get(tick, None)
        if not reduced_tick:
            return False

        if self.count >= reduced_tick.next:
            # Update our DeltaNext to the next reduced tick number.
            reduced_tick.cycle(self.count)
            return True

        return False

    # -------------------------------------------------------------------------
    # Life-Cycle Transitions
    # -------------------------------------------------------------------------

    def _cycle_autophagy(self) -> VerediHealth:
        '''
        Game is ending gracefully. Be responsive and still alive in autophagy.

        Default: do nothing and return that we're done with a successful
        autophagy.
        '''
        return VerediHealth.AUTOPHAGY_SUCCESSFUL

    def _cycle_apoptosis(self) -> VerediHealth:
        '''
        Game is ending gracefully. Systems are now shutting down, goinging
        unresponsive, whatever. The managers should probably still be up and
        alive until the very end, though.

        Default: do nothing and return that we're done with the apoptosis.
        '''
        return VerediHealth.APOPTOSIS_DONE

    def _cycle_necrosis(self) -> VerediHealth:
        '''
        Game is at the end. This is called once. Managers can probably die
        out now.

        Default: do nothing and return that we're done with a successful
        end of the world as we know it.
        '''
        return VerediHealth.NECROSIS
