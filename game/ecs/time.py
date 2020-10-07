# coding: utf-8

'''
Timing info for game.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Tuple
import numbers

from datetime import datetime

from decimal import Decimal

from veredi.base.assortments import CurrentNext
from veredi.data             import background
from veredi.data.exceptions  import ConfigError
from veredi.logger           import log
from veredi.base.const       import VerediHealth
from .                       import exceptions

from .const                  import SystemTick
from .event                  import EcsManagerWithEvents

from ..time.clock            import Clock
from veredi.time.machine     import MachineTime
from veredi.time.timer       import MonotonicTimer
from ..time.tick.round       import TickRounds, TickTypes


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO [2020-06-29]: Move time classes to time module.


# --------------------------------TimeManager----------------------------------
# --                               Dr. Time?                                 --
# ------------------------------"Just the Time."-------------------------------

class TimeManager(EcsManagerWithEvents):
    '''
    This class has the potential to be saved to data fields. Let it control its
    timezones. Convert to user-friendly elsewhere.
    '''
    _DEFAULT_TICK_STEP = Decimal(6)
    _DEFAULT_TIMEOUT_SEC = 10
    _SHORT_TIMEOUT_SEC = 1

    _METER_TIMEOUT_SEC = _DEFAULT_TICK_STEP * 4

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

        self._timer: MonotonicTimer = None
        '''
        A timer available for short thing.
        '''

    def __init__(self, tick_amount: Optional[TickTypes] = None) -> None:
        super().__init__()

        # TODO: Get our clocks, ticks, etc from config data?

        # defaults to zero start time, _DEFAULT_TICK_STEP tick step
        # zero is not an allowed tick amount so...
        tick_amount = tick_amount or self._DEFAULT_TICK_STEP
        if tick_amount <= 0:
            log.error("tick_amount should be `None` or a "
                      "non-zero, positive amount.")
            raise exceptions.SystemErrorV("tick_amount should be `None` or a "
                                          "non-zero, positive amount.",
                                          None, None)
        self.tick  = TickRounds(tick_amount)

        self.machine = MachineTime()
        self._timer = None

    def engine_init(self,
                    cn_ticks: CurrentNext[SystemTick],
                    cn_life: CurrentNext[SystemTick]) -> None:
        '''
        Engine will give us a pointer to its ticks/life-cycle objects so we can
        have getters.

        Do not ever set these.
        '''
        self._engine_tick = cn_ticks
        self._engine_life_cycle = cn_life

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

    def make_timer(self) -> MonotonicTimer():
        '''
        Returns a new, realtime MonotonicTimer. This is not TimeManager's timer
        in any way and does not interact with any of TimeManager's
        timer/timeout functions.
        '''
        return MonotonicTimer()

    @property
    def timer(self) -> MonotonicTimer:
        '''
        Returns TimeManager's only owned/life-time timer. Use care with this
        one - it's used by the game Engine and/or SystemManager to do offical
        stuff.

        Use make_timer() or get your own timer for special cases.
        '''
        if not self._timer:
            self._timer = MonotonicTimer()
        return self._timer

    def start_timeout(self) -> None:
        if not self._timer:
            self._timer = MonotonicTimer()

        self._timer.start()

    def end_timeout(self) -> float:
        if not self._timer:
            return

        self._timer.end()
        elapsed = self._timer.elapsed
        self._timer.reset()
        return elapsed

    @property
    def timing(self):
        '''
        Not stopped and have a start time means probably timing something.
        '''
        return self._timer.timing

    def is_timed_out(self,
                     timer:            Optional[MonotonicTimer],
                     timeout:          Union[str, float, int, None] = None,
                     use_engine_timer: bool = False) -> bool:
        '''
        If `use_engine_timer` is true /and/ `timer` is None, this will check
        self.timer, which the engine is in charge of for the engine
        ticks/life-cycle, to check against the timeout. Otherwise it requires a
        timer to be passed in.

        If `timeout` is None, uses _DEFAULT_TIMEOUT_SEC.
        If `timeout` is a number, uses that.
        If `timeout` is a string, checks config for a setting associated with
        that key under the TimeManager's settings.

        Returns true if timeout timer is:
          - Falsy.
          - Not timing.
          - Past timeout value.
            - or past _DEFAULT_TIMEOUT_SEC if timeout value is None.
        '''
        if not timer:
            if use_engine_timer and self.timer:
                timer = self.timer
            else:
                msg = f"is_timed_out() requires a timer. Got: {timer}"
                raise log.exception(ValueError(msg, timer, timeout),
                                    None,
                                    msg + f", timeout: {timeout}")

        if not timer.timing:
            return True

        # ------------------------------
        # Get a timeout setting from config?
        # ------------------------------
        if timeout and isinstance(timeout, str):
            config = background.config.config
            if not config:
                log.info("TimeManager cannot get config for checking "
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
                    log.info("TimeManager cannot get config for checking "
                             "timeout value of '{}'",
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

    def metered(self, meter: Optional[Decimal]) -> Tuple[bool, Decimal]:
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
        if not meter:
            return True, self.seconds

        now = self.seconds
        if now > meter + self._METER_TIMEOUT_SEC:
            return True, now
        return False, meter

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
