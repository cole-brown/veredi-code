# coding: utf-8

'''
A game of something or other.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Type, Any, Iterable, Dict)
if TYPE_CHECKING:
    from decimal             import Decimal
    from veredi.base.context import VerediContext
import collections  # collections.Iterable

from veredi.base.null          import NullNoneOr, null_or_none


# Error Handling
from veredi.logs               import log
from veredi.logs.metered       import MeteredLog
from veredi.logs.mixin         import LogMixin
from veredi.base.exceptions    import VerediError, HealthError
from veredi.base.strings       import label
from veredi.base.strings.mixin import NamesMixin
from .ecs.exceptions           import TickError
from .exceptions               import EngineError

# Other More Basic Stuff
from veredi.data               import background
from veredi.base.const         import VerediHealth
from veredi.base.assortments   import CurrentNext
from veredi.data.config.config import Configuration
from veredi.debug.const        import DebugFlag
from veredi.time.timer         import MonotonicTimer

# ECS Managers & Systems
from .ecs.const                import (SystemTick,
                                       game_loop_start,
                                       game_loop_end,
                                       game_loop_next,
                                       _GAME_LOOP_SEQUENCE,
                                       tick_health_init,
                                       tick_healthy)
from .ecs.meeting              import Meeting
from .event                    import EngineStopRequest

# ECS Minions
from .ecs.base.entity          import Entity


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# General Notes
# -----------------------------------------------------------------------------

# combat? time?
#   timing phase - touch stuff that deals with times, make buffs fall off, etc.
#   recalc - hp and stats

# combat
#   turn
#     preparation # better word?
#       - spells and stuff that are 'at the start of your turn'
#     actions
#     consequences # better word?
#       - spells and stuff that are 'at the end of your turn'


# TODO: This stuff?

# ------------------
# Engine Management
# ------------------

# add player to session
#   invite?
# add player to game/campaign
#   invite?
# add monster(s)
# add other stuff... items, currency...
# remove *
#   cancel invite?


# ------------------
# Combat
# ------------------

# start encounter/fight
#   initiatives - let players roll if they desired, or auto
# end encounter/fight
# round:
#   next/prev? - go there but don't change things
#   undo/redo? - follow trail of actions to do/undo things
# turn:
#   next/prev?
#   undo/redo?
# give loot
# give xp


# ------------------
# Most of these are probably campaign/dm/session/player things...
# ------------------

# ---
# Session.Location?
# ---

# party location in: universe, region, local group, galaxy, region, system,
# region, planet, region, subregion, continent, etc etc...
#  - they can split the party, so...

# encounter locations?

# points of interest...
#   stuff there: NPCs, treasure, dungeons, encounters, shops, whatever
#   DM notes

# ---
# Session.Time
# ---
# time related things for Session
#  - in game: curr datetime, datetime for each session, duration of
#    each session, etc...
#  - IRL: ditto

# ---
# Campaign.Time
# ---
# time related things for whole campaign...
#   - in game: start datetime, curr datetime, etc?
#   - IRL: ditto

# ---
# DM
# ---
# any and all DM actions/interactions not covered already

# ---
# Monsters
# ---
# any and all NPC/Monster actions/interactions not covered already...

# ---
# Players
# ---
# any and all Player actions/interactions not covered already


# Game is:
#   manager of whole shebang
#   very good at delegation
#
# game should get:
#   campaign info (name, owner?, system?, ...)
#   repo... types?
#   managers of the ECS ecosystem
#
# game should then:
#   load campaign from repo into Campaign obj
#   get player infos (user & player names, ...)
#   load players
#
# then...?
#   make or load Session
#     w/ campaign, players, etc?
#
# then...?
#   be ready to do shit?


# Scene: some... sub-part of a game.
# an encounter or battle or social situation or skill challenge maybe?


# Campaign: setting of game. saved state of game. ids of entities/systems tied
# to game

# Setting: d20 or whatever?
#   - "rule-set"?

# Session: one sit-down's worth of a game.
#   collection of scenes?
#   ids of entities/systems used in that session?

# Entity: just an id?

# Component: a thing an entity has

# System: a thing that triggers off of component(s) to update an entity

# NOTE: Owner is DM. But someone else could be DM too...
#     : Maybe a session DM list or something to keep track?
#     : Can a player be a DM too (e.g. to help newbie DM)?
#       - At the same time as they're playing?

# NOTE: DM is god. They must be able to change everything, ideally on a
# temporary OR permanent basis.


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# TODO [2020-09-27]: Check function names. Only used-externally should
# start with a letter. All internal-onyl should be "_blank".

# TODO: log.Groups: Do we switch all? Some?
# Do we make ours in their own ENGINE_* groups? Use more general groups?


class Engine(LogMixin, NamesMixin,
             name_dotted='veredi.game.engine',
             name_string='engine'):
    '''
    Implements an ECS-powered game engine with just
    one time-step loop (currently).
    '''

    # SYSTEMS_REQUIRED = frozenset((OneSystem,
    #                               TwoSystem,
    #                               RedSystem,
    #                               BlueSystem,
    # ))
    SYSTEMS_REQUIRED = frozenset()
    '''
    The systems that this engine cannot run without.
    '''

    _METER_LOG_AMT = 10  # seconds
    '''
    Amount of time (in seconds) that we want our MeteredLog to squelch/ignore
    the same/similar logging messages.
    '''

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''

        self._engine_health_: VerediHealth = VerediHealth.INVALID
        '''
        Overall engine health. Do not use directly. Get/set via
        properties/helper functions.
        '''

        self._tick_health_: VerediHealth = VerediHealth.INVALID
        '''
        Engine health of last/current tick. Do not use directly. Get/set via
        properties/helper functions.
        '''

        self._life_cycle: CurrentNext[SystemTick] = CurrentNext(
            SystemTick.INVALID,
            SystemTick.INVALID)
        '''
        Current Life-Cycle of engine. Should be a group of ticks like:
          SystemTick.TICKS_BIRTH
          SystemTick.TICKS_LIFE
          SystemTick.TICKS_DEATH
        '''

        self._tick: CurrentNext[SystemTick] = CurrentNext(
            SystemTick.INVALID,
            SystemTick.INVALID)
        '''Current individual tick (e.g. SystemTick.STANDARD).'''

        self._timer_life: MonotonicTimer = None
        '''
        Timer for Engine's Life-Cycles.

        TICKS_BIRTH:
          - Resets on each tick transition and times each start-up tick.

        TICKS_LIFE:
          - Times from entrance into this life-cycle until exit.

        TICKS_DEATH:
          - Resets on each tick transition and times each ending tick.
        '''

        self._timer_init: MonotonicTimer = None
        '''
        Timer that starts in init and just keeps going.
        '''

        self._debug: DebugFlag = None
        '''Debugging flags.'''

        self.meeting: Meeting = None
        '''ECS Managers'''

        self._metered_log: MeteredLog = None
        '''Metered logging for things that could be spammy, like tick logs.'''

    def __init__(self,
                 owner:         Entity,
                 campaign_id:   int,
                 configuration: Configuration,
                 managers:      Meeting,
                 debug:         NullNoneOr[DebugFlag] = None
                 ) -> None:
        # ---
        # Define Our Vars.
        # ---
        self._define_vars()

        # ---
        # LogMixin!
        # ---
        # Set up ASAP so we have self._log_*() working ASAP.

        # Config our LogMixin.
        self._log_config(self.dotted)

        # ---
        # Ye Olde Todoses
        # ---
        # # TODO: Make session a System, put these in there?
        # self.repo = repo_manager
        # self.owner = owner
        # self.campaign = repo_manager.campaign.load_by_id(campaign_id)

        # TODO: load/make session based on... campaign and.... parameter?
        #   - or is that a second init step?

        # ---
        # Debugging...
        # ---
        self._debug = debug

        # ---
        # Managers' Meeting...
        # ---
        self.meeting = managers

        # ---
        # Time & Timer Set-Up
        # ---
        # Init Timer starts timing here and then just runs, so this is all we
        # really need to do with it.
        timer_run_name = label.normalize(self.dotted, 'time', 'run')
        self._timer_run = self.meeting.time.make_timer(timer_run_name)

        # Life Timer times specific life-cycles (or specific parts of them).
        # We'll reset it in transition places.
        timer_life_name = label.normalize(self.dotted, 'time', 'life_cycle')
        self._timer_life = self.meeting.time.make_timer(timer_life_name)

        # Init TimeManager with our tick objects and our timers.
        self.meeting.time.engine_init(self._tick, self._life_cycle,
                                      timers={
                                          timer_run_name: self._timer_run,
                                          timer_life_name: self._timer_life,
                                      },
                                      default_name=timer_life_name)

        # ---
        # Metered Logging
        # ---
        self._metered_log = MeteredLog(self.dotted,
                                       log.Level.NOTSET,
                                       self.meeting.time.machine,
                                       fingerprint=True)
        # Tick Life-Cycles
        self._metered_log.meter(SystemTick.TICKS_BIRTH, self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.TICKS_LIFE,  self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.TICKS_DEATH, self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.TICKS_AFTERLIFE,
                                self._METER_LOG_AMT)

        # Ticks
        self._metered_log.meter(SystemTick.SYNTHESIS,   self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.MITOSIS,     self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.TIME,        self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.CREATION,    self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.PRE,         self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.STANDARD,    self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.POST,        self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.DESTRUCTION, self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.AUTOPHAGY,   self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.APOPTOSIS,   self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.NECROSIS,    self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.FUNERAL,     self._METER_LOG_AMT)

        # ---
        # Systems
        # ---
        self._create_required_systems(configuration)
        self._create_systems(configuration)

    def _create_required_systems(self, config: Configuration) -> None:
        '''
        Creates systems that cannot be setup via config and are just required.
        '''
        context = config.make_config_context()
        for sys_type in self.SYSTEMS_REQUIRED:
            self.meeting.system.create(sys_type, context)

    def _create_systems(self, config: Configuration) -> None:
        '''
        Creates systems that are set up via config (and systems they depend
        on if possible).
        '''
        # ---
        # Add Config's 'engine.systems'.
        # ---
        from_config = set()
        context = config.make_config_context()
        requested_systems = config.get('engine', 'systems')
        if not null_or_none(requested_systems):
            for name in requested_systems:
                sys_dotted = requested_systems[name]
                sys_type = config.get_registered(sys_dotted, context)
                self._log_debug("Engine config system: {} -> {} -> {}",
                                name, sys_dotted, sys_type)

                # Already exists? Uh... ok?
                if self.meeting.system.get(sys_type):
                    continue

                # Add to our set of systems to create.
                from_config.add(sys_type)

        # ---
        # Add dependencies to the required set.
        # ---
        all_required = self.SYSTEMS_REQUIRED.union(from_config)
        from_systems = set()
        for required_type in all_required:
            dependencies = required_type.dependencies()
            # No requirements - ok.
            if not dependencies:
                continue

            for name in dependencies:
                sys_dotted = requested_systems[name]
                sys_type = config.get_registered(sys_dotted, context)
                self._log_debug("{} depends on: {} -> {} -> {}",
                                required_type, name, sys_dotted, sys_type)

                # Already exists? Ok.
                if self.meeting.system.get(sys_type):
                    continue

                # Else, add to our set of systems to create.
                from_systems.add(sys_type)

        # ---
        # Create the systems we gathered.
        # ---
        for sys_type in from_systems:
            self._log_debug("Creating system from dependency: {}", sys_type)
            self.meeting.system.create(sys_type, context)

        for sys_type in from_config:
            self._log_debug("Creating system from config: {}", sys_type)
            self.meeting.system.create(sys_type, context)

    # -------------------------------------------------------------------------
    # Debug Stuff
    # -------------------------------------------------------------------------

    def debug_flagged(self, desired) -> bool:
        '''
        Returns true if Engine's debug flags are set to something and that
        something has the desired flag. Returns false otherwise.
        '''
        return self._debug and self._debug.has(desired)

    @property
    def debug(self) -> DebugFlag:
        '''Returns current debug flags.'''
        return self._debug

    @debug.setter
    def debug(self, value: DebugFlag) -> None:
        '''
        Set current debug flags. No error/sanity checks.
        Universe could explode; use wisely.
        '''
        self._debug = value

    def _dbg_tick(self,
                  msg: str,
                  *args: Any,
                  **kwargs: Any) -> None:
        '''
        Debug Log output if DebugFlag has the LOG_TICK flag set.
        '''
        if not self.debug_flagged(DebugFlag.LOG_TICK):
            return

        # Bump up stack by one so it points to our caller.
        kwargs = self._log_stack(**kwargs)
        self._log_debug(msg, *args, **kwargs)

    def _raise_health(self,
                      tick:        SystemTick,
                      curr_health: VerediHealth,
                      prev_health: VerediHealth,
                      info:        str,
                      *args:       Any,
                      never_raise: bool = False,
                      **kwargs:    Any) -> None:
        '''
        Raises an error if health is less than the minimum for runnable engine.
        This gets downgraded to a debug message if `never_raise` is True.

        Adds:
          "Engine's health became unrunnable: {prev} -> {curr}."
          to info/args/kwargs for log message.
        '''
        # If we're fine, ignore.
        if (not self.debug_flagged(DebugFlag.RAISE_HEALTH)
                or tick_healthy(tick, curr_health)):
            return

        # If we're ok with weird 'current tick' to 'current health' tuples,
        # just debug log them.
        if never_raise:
            self._log_debug(f"Engine's health became unrunnable during "
                            f"{tick}: {str(prev_health)} -> "
                            f"{str(curr_health)}.")
            return

        # Else raise the health exception.
        msg = (f"Engine's health became unrunnable during {tick}: "
               f"{str(prev_health)} -> {str(curr_health)}. ")
        error = HealthError(curr_health, prev_health, msg, None)
        raise self._log_exception(error,
                                  msg + info,
                                  *args,
                                  **kwargs)

    # -------------------------------------------------------------------------
    # Log Stuff
    # -------------------------------------------------------------------------

    def log_tick(self,
                 tick:     SystemTick,
                 level:    log.Level,
                 msg:      str,
                 *args:    Any,
                 **kwargs: Any) -> bool:
        '''
        Use our MeteredLog to log this tick-related log message. Will be logged
        under our dotted name (that is, the logger is named by the
        self.dotted attribute).

        WARNING: Log may be squelched if its too similar to other recent log
        messages in the `tick`.

        Returns True if logged, False if squelched.
        '''
        kwargs = kwargs or {}
        kwargs = self._log_stack(**kwargs)
        logged = self._metered_log.log(tick,
                                       level,
                                       msg,
                                       *args,
                                       **kwargs)

        # Raise **IF WE LOGGED** and if we are flagged to raise on logging.
        #   - Could be convinced to ignore that "if we logged"...
        if logged and self.debug_flagged(DebugFlag.RAISE_LOGS):
            raise_log_msg = (f"Engine's {DebugFlag.RAISE_LOGS} promoted "
                             "this log to an exception. Raising an error. "
                             f"Tick: {self.tick} at "
                             f"{self.meeting.time.error_game_time}.")
            error = TickError(raise_log_msg,
                              data={
                                  'tick': tick,
                                  'log_level': level,
                                  'log_msg': msg,
                                  'log_msg_args': args,
                                  'log_msg_kwargs': kwargs,
                              })
            raise error

        # Return whether it was logged or not.
        return logged

    def log_tick_error(self,
                       tick:         SystemTick,
                       error:        Exception,
                       msg:          Optional[str],
                       *args:        Any,
                       context:      Optional['VerediContext'] = None,
                       always_raise: bool                      = False,
                       **kwargs:     Any):
        '''
        Log a tick-related error via log_tick().

        Regardless of whether the log message was squelched, this will decided
        whether or not to raise a new error from the passed in error based on
        `self.debug_flags`.

        If `always_raise` is True, this will disregard DebugFlags. Otherwise
        this only raises if it has the DebugFlag to do so
        (DebugFlag.RAISE_ERRORS).
        '''
        kwargs = kwargs or {}
        kwargs = self._log_stack(**kwargs)

        # Send everything to MeteredLog. Don't care whether it logged or
        # ignored. Do care about the error it gives back - we'll reraise that
        # if needed.
        _, logged_error = self._metered_log.exception(tick,
                                                      error,
                                                      msg,
                                                      *args,
                                                      context=context,
                                                      **kwargs)

        if self.debug_flagged(DebugFlag.RAISE_ERRORS):
            raise logged_error from error

    # -------------------------------------------------------------------------
    # Engine Overall Health
    # -------------------------------------------------------------------------

    def set_all_health(self,
                       value: VerediHealth,
                       forced: bool = True) -> None:
        '''
        Set all healths to the value indicated. This is usually for when things
        go south and we want the engine to die.

        If `forced`, just straight up sets it.
        Else, uses VerediHealth.set() to pick the worst of current and value.
        '''
        prev_tick = self.tick_health
        prev_engine = self.engine_health
        self.set_engine_health(value, forced, never_raise=True)
        self.set_tick_health(value, forced, never_raise=True)
        # Only raise health exception if DebugFlag is set AND if we are not
        # forcing it. If we are forcing it, it'll only log.
        self._raise_health(self.tick,
                           value,
                           VerediHealth.set(prev_tick, prev_engine),
                           (f"set_all_health "
                            f"{'forcing' if forced else 'setting'} "
                            f"to poor value: {value}."),
                           never_raise=forced)

    @property
    def engine_health(self) -> VerediHealth:
        '''
        Overall health of the engine itself.
        '''
        return self._engine_health_

    def set_engine_health(self,
                          value:       VerediHealth,
                          forced:      bool,
                          never_raise: bool = False) -> None:
        '''
        Set the current health of the engine overall.
        If `forced`, just straight up sets it.
        Else, uses VerediHealth.set() to pick the worst of current and value.
        '''
        prev_health = self._engine_health_
        if forced:
            self._engine_health_ = value
        self._engine_health_ = self._engine_health_.update(value)

        # ---
        # Log if bad. Let MeteredLog filter down on the spam.
        # ---
        if not value.in_runnable_health:
            self.log_tick(self.tick,
                          log.Level.ERROR,
                          "Setting Engine Health to an unrunnable value! "
                          "Being set to {} minimum resulted in "
                          "current engine health of {} (previously {}). {}",
                          str(value),
                          str(self._engine_health_),
                          str(prev_health),
                          self.meeting.time.error_game_time)

        elif not self._engine_health_.in_runnable_health:
            self.log_tick(self.tick,
                          log.Level.ERROR,
                          "Setting Engine Health... but already at an "
                          "unrunnable value! Setter desired {}, but "
                          "current engine health is {} (previously {}). {}",
                          str(value),
                          str(self._engine_health_),
                          str(prev_health),
                          self.meeting.time.error_game_time)

        # ---
        # Raise if flagged to do so.
        # ---
        if not never_raise and not self._engine_health_.in_runnable_health:
            self._raise_health(self.tick,
                               self.engine_health,
                               prev_health,
                               (f"set_all_health "
                                f"{'forcing' if forced else 'setting'} "
                                f"to poor value: {value}."))

    @property
    def tick_health(self) -> VerediHealth:
        '''
        Health of current tick.
        '''
        return self._tick_health_

    def set_tick_health(self,
                        value:       VerediHealth,
                        forced:      bool,
                        never_raise: bool = False) -> None:
        '''
        Set the health of current tick.
        If `forced`, just straight up sets it.
        Else, uses VerediHealth.set() to pick the worst of current and value.
        '''
        prev_health = self._tick_health_
        if forced:
            self._tick_health_ = value
        self._tick_health_ = self._tick_health_.update(value)

        # ---
        # Log if bad. Let MeteredLog filter down on the spam.
        # ---
        if not value.in_runnable_health:
            self.log_tick(self.tick,
                          log.Level.ERROR,
                          f"{'Forcing' if forced else 'Setting'} "
                          "Tick Health to an unrunnable value! "
                          "Being set to {} minimum resulted in "
                          "current tick health of {} (previously {}). {}",
                          str(value),
                          str(self._tick_health_),
                          str(prev_health),
                          self.meeting.time.error_game_time)

        elif not self._tick_health_.in_runnable_health:
            self.log_tick(self.tick,
                          log.Level.ERROR,
                          f"{'Forcing' if forced else 'Setting'} "
                          "Tick Health... but already at an "
                          "unrunnable value! Setter desired {}, but "
                          "current tick health is {} (previously {}). {}",
                          str(value),
                          str(self._tick_health_),
                          str(prev_health),
                          self.meeting.time.error_game_time)

        # ---
        # Raise if flagged to do so.
        # ---
        if not never_raise and not self._tick_health_.in_runnable_health:
            self._raise_health(self.tick,
                               self.engine_health,
                               prev_health,
                               (f"set_all_health "
                                f"{'forcing' if forced else 'setting'} "
                                f"to poor value: {value}."))

    # -------------------------------------------------------------------------
    # Life / Tick
    # -------------------------------------------------------------------------

    @property
    def life_cycle(self) -> SystemTick:
        '''Current life cycle of engine.'''
        return self._life_cycle.current

    @property
    def tick(self) -> SystemTick:
        '''Current tick of engine.'''
        return self._tick.current

    # -------------------------------------------------------------------------
    # Game Start / Run / Stop
    # -------------------------------------------------------------------------

    def _run_ok(self) -> bool:
        '''
        Returns True if this tick can proceed.

        Returns False if something is preventing tick, like bad tick health,
        bad engine health, etc.
          - This return value indicates that the caller should put the engine
            into shutdown or stop or something.
        '''
        # Currently, both INVALID means 'about to run first tick ever'.
        if (self.tick == SystemTick.INVALID
                and self.life_cycle == SystemTick.INVALID):
            self._dbg_tick(
                "Engine tick/life-cycle both INVALID - starting up? {} {} {}",
                self.tick, self._life_cycle,
                str(self.engine_health))
            return True

        healthy = True
        if self._stopped_health(self.engine_health):
            self.log_tick(self.life_cycle,
                          log.Level.CRITICAL,
                          "Engine overall health is bad - "
                          "cannot run next tick: {} {}",
                          self.tick, str(self.engine_health))
            healthy = False

        if self._stopped_health(self.tick_health):
            self.log_tick(self.life_cycle,
                          log.Level.CRITICAL,
                          "Engine tick health is bad - "
                          "cannot run next tick: {} {}",
                          self.tick, str(self.engine_health))
            healthy = False

        return healthy

    def run(self) -> None:
        '''
        Loop of `self.run_tick()` until `self.stopped()` is True.
        '''
        while not self.stopped(log_stopped=True):
            self.run_tick()

    def run_tick(self) -> Optional[VerediHealth]:
        '''
        Run through one Tick Cycle of the Engine: START, RUN, STOP

        Engine.life_cycle must start in correct state to transition.
        Post-init: INVALID
          START:   INVALID    -> CREATING
          RUN:     CREATING   -> ALIVE
          STOP:    ALIVE      -> DESTROYING
        Post-STOP: DESTROYING -> DEAD

        Returns the health for the entire cycle.
        Returns None if it refused to run.
        '''
        # ------------------------------
        # Sanity checks.
        # ------------------------------
        bail_out_now = False
        if not self._run_ok():
            self.log_tick(self.life_cycle,
                          log.Level.CRITICAL,
                          "Engine.run() ignored due to engine being in "
                          "poor health. Health: {} {}. "
                          "Life-Cycle: {} -> {}",
                          str(self.engine_health),
                          str(self.tick_health),
                          str(self._life_cycle.current),
                          str(self._life_cycle.next))
            bail_out_now = True

        if self._should_stop_health():
            self.log_tick(self.life_cycle,
                          log.Level.CRITICAL,
                          "Engine.run() ignored due to engine being in "
                          "incorrect state for running. _should_stop_health() "
                          "returned True. Health is {} {}. ",
                          "Life-Cycle: {} -> {}",
                          str(self.engine_health),
                          str(self.tick_health),
                          str(self._life_cycle.current),
                          str(self._life_cycle.next))
            bail_out_now = True

        if bail_out_now:
            self.set_all_health(VerediHealth.set(self.engine_health,
                                                 self.tick_health))
            # TODO: set to be shutdown, or run shutdown, or something?
            return None

        # ------------------------------
        # Try to do tick; always do the time step after.
        # ------------------------------
        try:
            # ---
            # Promote next cycle & tick to current.
            # ---
            cycle = self._run_transition()

            # ---
            # Did we just cycle into fully dead?
            # ---
            if self._stopped_afterlife():
                return self.engine_health

            # ---
            # Run the cycle asked for!
            # ---
            health = self._run_cycle(cycle)
            # This has updated the engine health based on cycle health results.

        finally:
            # Time gets ticked at the start of _update_time(), not here.
            # self.meeting.time.delta()
            pass

        # We're going to return the actual run's health instead of the engine's
        # health since the caller can always get the latter themselves.
        return health

    def _run_transition(self) -> SystemTick:
        '''
        Checks for life-cycle transitions, errors/logs them, and starts the
        timer for life-cycle transitions.

        Update self._life_cycle and self._tick.

        Returns:
          - Not a Transition:
            - The new current life-cycle.
          - Valid Transition:
            - The new current life-cycle.
          - Invalid Transition:
            - SystemTick.ERROR
        '''
        # ------------------------------
        # Do they need initializing?
        # ------------------------------
        self._life_cycle.set_if_invalids(SystemTick.INVALID,
                                         SystemTick.TICKS_BIRTH)
        self._tick.set_if_invalids(SystemTick.INVALID,
                                   SystemTick.SYNTHESIS)

        # ------------------------------
        # Practice Safe Transitioning!
        # ------------------------------
        cycle_from = self._life_cycle.current
        cycle_to = self._life_cycle.next
        if cycle_from != cycle_to:
            # We're in a transition state. Validate it.
            valid = self._run_trans_validate(cycle_from, cycle_to)
            if valid == SystemTick.ERROR:
                return SystemTick.ERROR

        # If we have a life-cycle transition or a tick-cycle transition for a
        # serial/non-looping life cycle (e.g. TICKS_BIRTH: SYNTHESIS ->
        # MITOSIS), this will call any transition functions.
        #
        # It can be called during non-transitions - it will figure out if a
        # transition is happening that it cares about.
        self._run_trans_to(cycle_from, cycle_to)

        # ------------------------------
        # Pull next into current for the upcomming run.
        # ------------------------------
        cycle = self._life_cycle.cycle()
        self._tick.cycle()

        # Done; return the new current life cycle.
        return cycle

    def _run_trans_to(self,
                      cycle_from: SystemTick,
                      cycle_to:   SystemTick) -> VerediHealth:
        '''
        Calls any once-only, enter/exit engine life-cycle functions. For
        TICKS_BIRTH and TICKS_DEATH life-cycles, this calls specific tick cycle
        transitions too.

        Should only be called if not an /invalid/ transition. Can be called for
        non-transitions.

        Keeps a running health check of any tick transition functions called.
        Updates tick health with this, and returns our health (not overall tick
        health).
        '''
        health = VerediHealth.HEALTHY
        tick_from = self._tick.current
        tick_to = self._tick.next

        # ------------------------------
        # Life-Cycle: TICKS_BIRTH
        # ------------------------------
        # TICKS_BIRTH isn't what most things care about - they want
        # the specific start ticks...
        if cycle_to == SystemTick.TICKS_BIRTH:
            # ---
            # Not a Tick-Cycle: No-op.
            # ---
            if tick_from == tick_to:
                pass

            # ---
            # Tick-Cycles: SYNTHESIS, MITOSIS.
            # ---
            elif (tick_to == SystemTick.SYNTHESIS
                  or tick_to == SystemTick.MITOSIS):
                health = health.update(self.meeting.life_cycle(cycle_from,
                                                               cycle_to,
                                                               tick_from,
                                                               tick_to))

            # ---
            # Tick-Cycle: New Tick?
            # ---
            else:
                health = health.update(VerediHealth.HEALTHY_BUT_WARNING)
                # We're technically in between?
                # I guess where we were will be the squelch...
                self.log_tick(cycle_from,
                              log.Level.WARNING,
                              "_run_trans_to() does not know about life-cycle "
                              "{}->{} tick transition: {} -> {}",
                              cycle_from, cycle_to,
                              tick_from, tick_to)

        # ------------------------------
        # Life-Cycle: TICKS_LIFE
        # ------------------------------
        elif cycle_to == SystemTick.TICKS_LIFE and cycle_from != cycle_to:
            health = health.update(self.meeting.life_cycle(cycle_from,
                                                           cycle_to,
                                                           tick_from,
                                                           tick_to))

        # ------------------------------
        # Life-Cycle: TICKS_DEATH
        # ------------------------------
        elif cycle_to == SystemTick.TICKS_DEATH:
            # ===
            # Life-Cycled into TICKS_DEATH; tick could still be set up for
            # something else.
            # ===
            if tick_to not in SystemTick.TICKS_DEATH:
                # Fix the tick(s) first so we can just have one check.
                self._tick.next = tick_to = SystemTick.AUTOPHAGY
                # And unfreeze our life-cycle if it was frozen by e.g.
                # `self.stop()`.
                self._life_cycle.freeze(False)

                # Now we can go on to do the normal tick-cycle checks:

            # ---
            # Not a Tick-Cycle: No-op.
            # ---
            if tick_from == tick_to:
                pass

            # ---
            # Tick-Cycles: AUTOPHAGY, APOPTOSIS, NECROSIS, FUNERAL
            # ---
            elif (tick_to == SystemTick.AUTOPHAGY
                  or tick_to == SystemTick.APOPTOSIS
                  or tick_to == SystemTick.NECROSIS
                  or tick_to == SystemTick.FUNERAL):
                health = health.update(self.meeting.life_cycle(cycle_from,
                                                               cycle_to,
                                                               tick_from,
                                                               tick_to))

            # ---
            # Tick-Cycle: New Tick?
            # ---
            else:
                # We're technically in between ticks?
                # I guess where we were will be the squelch...
                self.log_tick(cycle_from,
                              log.Level.WARNING,
                              "_run_trans_to() does not know about life-cycle "
                              "{}->{} tick transition: {} -> {}",
                              cycle_from, cycle_to,
                              tick_from, tick_to)

    def _run_trans_validate(self,
                            cycle_from: SystemTick,
                            cycle_to: SystemTick) -> SystemTick:
        '''
        Checks that the transition is valid.

        NOTE: Expects to be /in/ a transition, so check that before calling
        this.

        Returns:
          SystemTick.ERROR:
            - Invalid transition.
              - Already dealt with in self._run_trans_error()
          `cycle_to`:
            - Valid Transition.
              - Already ran self._run_trans_log() for logging/timer.
        '''
        # ---
        # ----> TICKS_BIRTH
        # ---
        if cycle_to == SystemTick.TICKS_BIRTH:
            # Only Valid Transition: INVALID -> TICKS_BIRTH
            if cycle_from != SystemTick.INVALID:
                # Error on bad transition.
                return self._run_trans_error(cycle_from, cycle_to,
                                             SystemTick.INVALID)
            else:
                # Log/start timer on good transition.
                # We have the upcoming current cycle as `cycle_to`.
                # Get the upcoming current tick from `self._tick.next`.
                self._run_trans_log(cycle_to,
                                    self._tick.next)
                return cycle_to

        # ---
        # ----> TICKS_LIFE
        # ---
        elif cycle_to == SystemTick.TICKS_LIFE:
            # Only Valid Transition: TICKS_BIRTH -> TICKS_LIFE
            if cycle_from != SystemTick.TICKS_BIRTH:
                # Error on bad transition.
                return self._run_trans_error(cycle_from, cycle_to,
                                             SystemTick.TICKS_BIRTH)
            else:
                # Log/start timer on good transition.
                # We have the upcoming current cycle as `cycle_to`.
                # Get the upcoming current tick from `self._tick.next`.
                self._run_trans_log(cycle_to,
                                    self._tick.next)
                return cycle_to

        # ---
        # ----> TICKS_DEATH
        # ---
        elif cycle_to == SystemTick.TICKS_DEATH:
            # Valid Transitions: TICKS_BIRTH -> TICKS_DEATH
            #                    TICKS_LIFE  -> TICKS_DEATH
            if (cycle_from != SystemTick.TICKS_BIRTH
                    and cycle_from != SystemTick.TICKS_LIFE):
                # Error on bad transition.
                return self._run_trans_error(cycle_from, cycle_to,
                                             (SystemTick.TICKS_LIFE,
                                              SystemTick.TICKS_BIRTH))
            else:
                # Log/start timer on good transition.
                # We have the upcoming current cycle as `cycle_to`.
                # Get the upcoming current tick from `self._tick.next`.
                self._run_trans_log(cycle_to,
                                    self._tick.next)
                return cycle_to

        # ---
        # ----> NECROSIS | FUNERAL
        # ---
        elif cycle_to == SystemTick.FUNERAL | SystemTick.NECROSIS:
            # Valid Transitions: TICKS_DEATH -> NECROSIS | FUNERAL
            if (cycle_from != SystemTick.TICKS_DEATH):
                # Error on bad transition.
                return self._run_trans_error(cycle_from, cycle_to,
                                             SystemTick.TICKS_DEATH)
            else:
                # Log/start timer on good transition.
                # We have the upcoming current cycle as `cycle_to`.
                # Get the upcoming current tick from `self._tick.next`.
                self._run_trans_log(cycle_to,
                                    self._tick.next)
                return cycle_to

        # ---
        # ----> ???
        # ---
        else:
            # We're in some weird and wrong life-cycle transition. Error it.
            return self._run_trans_error(cycle_from, cycle_to,
                                         None)

    def _run_trans_log(self,
                       new_life: SystemTick,
                       new_tick: SystemTick) -> None:
        '''
        Log the start of a valid transition.
        Start the timer for the new life-cycle.
        '''
        # Log new life-cycle/tick.
        self._dbg_tick("Start life-cycle: {}...", new_life)
        self._dbg_tick("Start tick: {}...", new_tick)

        # And start the new life-cycle's timer.
        self._timer_life.start()

    def _run_trans_error(self,
                         cycle_from: SystemTick,
                         cycle_to: SystemTick,
                         valid: Union[SystemTick, Iterable[SystemTick], None]
                         ) -> SystemTick:
        '''
        Helper for formatting an error, logging and maybe raising it,
        updating tick health, etc.
        '''
        valid_str = None
        if (not isinstance(valid, str)
                and isinstance(valid, collections.abc.Iterable)):
            valid_str = ', '.join([str(each) for each in valid])
        else:
            valid_str = str(valid)

        msg = (f"Cannot transition to '{cycle_to}' from "
               f"'{cycle_from}'; only from '{valid_str}'")
        error = ValueError(msg)
        kwargs = {}
        kwargs = self._log_stack(**kwargs)
        self.log_tick_error(cycle_from, error, msg, **kwargs)
        self.set_tick_health(VerediHealth.FATAL, True)
        return SystemTick.ERROR

    def _run_cycle(self, cycle: SystemTick) -> None:
        '''
        Runs life-cycle function for the current `cycle`.

        Returns the life-cycle's health; set_engine_health() has already been
        called just before returning.

        !!NOTE!!: The returned value and self.engine_health could differ due to
        set_engine_health() preferring the worst health value it gets.
        '''
        run_health = VerediHealth.FATAL
        if cycle == SystemTick.TICKS_BIRTH:
            run_health = self._run_cycle_start()

        elif cycle == SystemTick.TICKS_LIFE:
            run_health = self._run_cycle_run()

        elif cycle == SystemTick.TICKS_DEATH:
            run_health = self._run_cycle_end()

        else:
            error = EngineError(
                f"{self.klass}._run_cycle() "
                f"received an un-runnable SystemTick cycle: {cycle}",
                data={
                    'cycle': cycle,
                })
            self.log_tick_error(
                cycle,
                error,
                "{}._run_cycle({}) received an un-runnable SystemTick: {}. "
                "Valid options are: {}",
                self.klass,
                cycle,
                cycle,
                (SystemTick.TICKS_BIRTH,
                 SystemTick.TICKS_LIFE,
                 SystemTick.TICKS_DEATH))

        self.set_engine_health(run_health, False)
        return run_health

    # -------------------------------------------------------------------------
    # Game Start
    # -------------------------------------------------------------------------

    def _run_cycle_start(self) -> VerediHealth:
        '''
        Will run a tick of start-up per call. Start Ticks loop independently
        until complete, then move on to the next (..., SYNTHESIS, SYNTHESIS, INTRA,
        INTRA, ...). This function will transitions from each start tick to the
        next automatically.

        We will time out if any one tick takes too long to finish and move on
        to the next.

        We will transition out of TICKS_BIRTH automatically when we finish
        successfully.

        Returns:
          - VerediHealth.PENDING if TICKS_BIRTH life-cycle is still in progress
          - VerediHealth.HEALTHY if we are done.
          - Some other health if we or our systems are going wrong.
        '''

        # ------------------------------
        # First tick: SYNTHESIS
        # ------------------------------
        if self.tick == SystemTick.SYNTHESIS:

            health = self._update_synthesis()
            # Health in general will be checked later...
            # Just check for other things and return it.

            # Allow a healthy tick that technically overran the timeout to
            # pass. It's close enough, right?
            if (health != VerediHealth.HEALTHY
                    and self.meeting.time.is_timed_out(self._timer_life,
                                                       'synthesis')):
                self.log_tick(self.tick,
                              log.Level.ERROR,
                              "FATAL: {}'s {} took too long "
                              "and timed out! (health: {}, took: {})",
                              self.klass,
                              self.tick,
                              str(health),
                              self._timer_life.elapsed_str)
                self.set_all_health(VerediHealth.FATAL, True)
                return self.tick_health

            # HEALTHY means done. Set up for our transition.
            if health == VerediHealth.HEALTHY:
                self._tick.next = SystemTick.MITOSIS
                # Leave life-cycle as-is.

            # Did a tick of synthesis; done for this time.
            return health

        # ------------------------------
        # Second tick: MITOSIS
        # ------------------------------
        elif self.tick == SystemTick.MITOSIS:

            health = self._update_mitosis()
            # Health in general will be checked later...
            # Just check for other things and return it.

            # Allow a healthy tick that technically overran the timeout to
            # pass. It's close enough, right?
            if (health != VerediHealth.HEALTHY
                    and self.meeting.time.is_timed_out(self._timer_life,
                                                       'mitosis')):
                self.log_tick(self.tick,
                              log.Level.ERROR,
                              "FATAL: {}'s {} took too long "
                              "and timed out! (health: {}, took: {})",
                              self.klass,
                              self.tick,
                              str(health),
                              self._timer_life.elapsed_str)
                self.set_all_health(VerediHealth.FATAL, True)
                return self.tick_health

            # HEALTHY means done. Set up for our transition.
            if health == VerediHealth.HEALTHY:
                # Set up for entering the standard game life-cycle and ticks.
                self._tick.next = SystemTick.TIME
                self._life_cycle.next = SystemTick.TICKS_LIFE

            # Did a tick of mitosis; done for this time.
            return health

        # Else, um... How and why are we here? This is a bad place.
        self.log_tick(self.tick,
                      log.Level.ERROR,
                      "FATAL: {} is in {} but not in any "
                      "creation/start-up ticks? {}",
                      self.klass,
                      self.tick,
                      self._timer_life.elapsed_str)
        self.set_all_health(VerediHealth.FATAL, True)
        return self.tick_health

    # -------------------------------------------------------------------------
    # Game Run
    # -------------------------------------------------------------------------

    def _run_cycle_run(self) -> VerediHealth:
        '''
        Will run one /FULL GAME-LOOP CYCLE/. That is, this runs all game-loop
        ticks in sequence for each call. We do not check/fail out (currently)
        for bad tick health during the run, just keep updating our cycle's
        health and the overall engine health based on each tick's results.

        There is currently no timeout for ticks here or for the game loop.

        There is also no automatic normal transition out of the TICKS_LIFE
        life-cycle. A system or something will need to trigger the engine's
        autophagy.

        !!NOTE!!: The returned value and self.engine_health could differ due to
        set_engine_health() preferring the worst health value it gets from
        anywhere, and our return value only paying attention to official tick
        health results.

        Returns:
          - Worst tick health. Could be different from self.engine_health.
        '''
        # ---
        # Sane start tick?
        # ---
        valid_start = game_loop_start()
        if self.tick != valid_start:
            msg = (f"_run_cycle_run must start in "
                   f"{str(valid_start)}, not {str(self.tick)}.")
            error = ValueError(msg)
            self.log_tick_error(self.tick, error, msg)
            health = VerediHealth.UNHEALTHY
            self.set_all_health(health)
            return health

        # ---
        # Run through tick sequence.
        # ---
        cycle_health = VerediHealth.INVALID
        for current_tick, next_tick in game_loop_next():
            # Ticks should set the tick health. We'll keep track of our own
            # overall cycle health. We don't currently bail out in the middle
            # due to health.
            self._tick.current = current_tick
            self._tick.next = next_tick
            health = self._update_game_loop()

            # Debug Health if flagged.
            self._raise_health(self.tick,
                               health,
                               cycle_health,
                               ("_run_cycle_run's tick health became "
                                f"too poor: {str(health)}."))
            cycle_health = cycle_health.update(health)

        # ---
        # Sane stop tick?
        # ---
        valid_end = game_loop_end()
        if self.tick != valid_end:
            msg = (f"_run_cycle_run must end at "
                   f"{str(valid_end)}, not {str(self.tick)}.")
            error = ValueError(msg)
            self.log_tick_error(self.tick, error, msg)
            health = VerediHealth.UNHEALTHY
            self.set_all_health(health)
            return health

        # ---
        # Done; return our cycle's health.
        # ---
        return cycle_health

    # -------------------------------------------------------------------------
    # Game End
    # -------------------------------------------------------------------------

    def _run_cycle_end(self) -> VerediHealth:
        '''
        Will run a tick of the end cycle per call. End Ticks loop independently
        until complete, then move on to the next (..., AUTOPHAGY, AUTOPHAGY,
        APOPTOSIS, ..., etc.) . This function will transitions from each start
        tick to the next automatically.

        We will time out if any one tick takes too long to finish and move on
        to the next.

        We will transition life-cycle and tick to FUNERAL after a successful
        finish.

        Returns:
          - A VerediHealth value.
        '''
        # ------------------------------
        # First tick: AUTOPHAGY
        # ------------------------------
        if self.tick == SystemTick.AUTOPHAGY:
            # THE END IS NIGH!

            health = self._update_autophagy()
            # Health in general will be checked later...
            # Just check for other things and return it.

            # Allow a healthy tick that technically overran the timeout to
            # pass. It's close enough, right?
            if ((health != VerediHealth.AUTOPHAGY_SUCCESSFUL
                 or health != VerediHealth.AUTOPHAGY_FAILURE)
                and self.meeting.time.is_timed_out(self._timer_life,
                                                   'autophagy')):
                self.log_tick(self.tick,
                              log.Level.ERROR,
                              "FATAL: {}'s {} took too long "
                              "and timed out! (health: {}, took: {})",
                              self.klass,
                              self.tick,
                              str(health),
                              self._timer_life.elapsed_str)
                self.set_all_health(VerediHealth.FATAL, True)
                return self.tick_health

            # Are we done? Set up for our transition.
            if (health == VerediHealth.AUTOPHAGY_SUCCESSFUL
                    or health == VerediHealth.AUTOPHAGY_FAILURE):
                # THE END TIMES ARE UPON US!
                self._tick.next = SystemTick.APOPTOSIS
                # Leave life-cycle as-is.

            # Did a tick of autophagy; done for this time.
            return health

        # ------------------------------
        # Second tick: APOPTOSIS
        # ------------------------------
        elif self.tick == SystemTick.APOPTOSIS:

            health = self._update_apoptosis()
            # Health in general will be checked later...
            # Just check for other things and return it.

            # Allow a healthy tick that technically overran the timeout to
            # pass. It's close enough, right?
            if (health != VerediHealth.APOPTOSIS_DONE
                    and self.meeting.time.is_timed_out(self._timer_life,
                                                       'apoptosis')):
                self.log_tick(self.tick,
                              log.Level.ERROR,
                              "FATAL: {}'s {} took too long "
                              "and timed out! (health: {}, took: {})",
                              self.klass,
                              self.tick,
                              str(self.health),
                              self._timer_life.elapsed_str)
                self.set_all_health(VerediHealth.FATAL, True)
                return self.tick_health

            # HEALTHY means done. Set up for our transition.
            if health == VerediHealth.APOPTOSIS_DONE:
                # THE END IS HERE!
                self._tick.next = SystemTick.NECROSIS
                # Leave life-cycle as-is.

            # Did a tick of apoptosis; done for this time.
            return health

        # ------------------------------
        # Final tick: NECROSIS
        # ------------------------------
        elif self.tick == SystemTick.NECROSIS:
            # There is only one pass through this tick.

            health = self._update_necrosis()
            # Health in general will be checked later...
            # Just check for other things and return it.

            # Do the health check for consistency with all the other ticks, but
            # really this is the end and whatever. The health is the health at
            # this point.
            if health != VerediHealth.NECROSIS:
                self.log_tick(self.tick,
                              log.Level.WARNING,
                              "{}'s {} completed with poor "
                              "or incorrect health. (time: {})",
                              self.klass,
                              self.tick,
                              self._timer_life.elapsed_str)
                self.set_all_health(VerediHealth.FATAL, True)
                return self.tick_health

            # Stay in TICKS_DEATH life-cycle.

            # Don't care about anything. We're done. Good day.
            self._tick.next = SystemTick.FUNERAL

            # Farewell.
            return health

        # ------------------------------
        # No, really. NECROSIS was the final tick.
        # This is just our FUNERAL tick...
        # ------------------------------
        elif self.tick == SystemTick.FUNERAL:
            # There is only one pass through this tick.

            health = self._update_funeral()
            # Health in general will be checked later...
            # Just check for other things and return it.

            # We're done. Park tick and life-cycle.
            self._tick.next = SystemTick.FUNERAL | SystemTick.NECROSIS
            self._life_cycle.next = SystemTick.FUNERAL | SystemTick.NECROSIS

            # Do the health check for consistency with all the other ticks, but
            # really this is the end and whatever. The health is the health at
            # this point.
            if health != VerediHealth.NECROSIS:
                self.log_tick(self.tick,
                              log.Level.WARNING,
                              "{}'s {} completed with poor "
                              "or incorrect health: {} (expected: {}). "
                              "(time: {})",
                              self.klass,
                              str(self.tick),
                              str(health),
                              str(VerediHealth.NECROSIS),
                              self._timer_life.elapsed_str)
                self.set_all_health(VerediHealth.FATAL, True)

            return health

        # Else, um... How and why are we here? This is a bad place.
        # TODO [2020-09-27]: Do we need to funeral ourselves here or anything?
        self.log_tick(self.tick,
                      log.Level.ERROR,
                      "FATAL: {} is in {} but not in any "
                      "tear-down/end ticks? tick: {}, timer-life: {}",
                      self.klass,
                      self.life_cycle,
                      self.tick,
                      self._timer_life.elapsed_str)
        self.set_all_health(VerediHealth.FATAL, True)
        return self.tick_health

    # -------------------------------------------------------------------------
    # Game Stopping
    # -------------------------------------------------------------------------

    def _should_stop_health(self):
        return self.engine_health.should_die

    def _event_request_stop(self, event: EngineStopRequest) -> None:
        '''
        Someone requested we kick into TICKS_DEATH.
        '''
        # TODO: log.Group.EVENTS
        self.stop()

    def stopped(self,
                log_stopped:     Optional[str] = None,
                log_not_stopped: Optional[str] = None) -> bool:
        '''
        Returns True if engine will not run.

        This checks the engine's health and its life-cycle.

        If `log_not_stopped` is a string, this will log when engine isn't in a
        'stopped' state at ERROR level with `log_not_stopped` as first part
        of the log, followed by " - it is not stopped.".

        If `log_stopped` is a string, this will log when engine /is/ in a
        'stopped' state at ERROR level with `log_stopped` as first part
        of the log, followed by " - it is stopped/stopped.".
        '''
        # TODO: log.Group.SHUT_DOWN

        # ---
        # Is the health in a runnable state?
        # ---
        health_stop = self._stopped_healths()
        if health_stop and log_stopped:
            self._log_info(f"Engine is stopped due to unrunnable health. "
                           f"life-cycle: {self.life_cycle}, "
                           f"tick: {self.tick}, "
                           f"tick health: {str(self.tick_health)}, "
                           f"engine health: {str(self.engine_health)} ")

        # ---
        # Is the life-cycle in a runnable state?
        # ---
        life_cycle_stop = self._stopped_life_cycle()
        if life_cycle_stop and log_stopped:
            self._log_info(f"Engine is stopped due to its life-cycle. "
                           f"life-cycle: {self.life_cycle}, "
                           f"tick: {self.tick}, "
                           f"tick health: {str(self.tick_health)}, "
                           f"engine health: {str(self.engine_health)} ")

        # ---
        # Put it together.
        # ---
        engine_stop = (health_stop or life_cycle_stop)

        # ---
        # Should we log that we're /NOT/ stopped? We haven't yet.
        # ---
        if log_not_stopped and not engine_stop:
            self._log_info(f"Engine is /NOT/ stopped! "
                           f"life-cycle [OK]: {self.life_cycle}, "
                           f"tick [OK]: {self.tick}, "
                           f"tick health [OK]: {str(self.tick_health)}, "
                           f"engine health [OK]: {str(self.engine_health)} ")

        # ---
        # Done.
        # ---
        return engine_stop

    def _stopped_health(self, health: VerediHealth) -> bool:
        '''
        Returns True if `health` is null/none, or is a health under the min
        for running healthfully.
        '''
        # ---
        # Bad value always means not runnable. -> True
        # ---
        if null_or_none(health):
            return True

        # ---
        # Good Health means not stopped (from health). -> False
        # ---
        return not health.in_runnable_health

    def _stopped_healths(self, *args: VerediHealth) -> bool:
        '''
        Returns True if any of these are unrunnable (determined by
        `self._stopped_health()`):
          - engine health
          - tick health
          - any of the `args`

        Returns False if all healths are runnable.
        '''
        stopped = (self._stopped_health(self.engine_health)
                   or self._stopped_health(self.tick_health))
        for each in args:
            stopped = stopped or self._stopped_health(each)
        return stopped

    def _stopped_afterlife(self) -> bool:
        '''
        Returns True if Engine's Life-Cycle is in the afterlife.

        Always logs.
        '''
        # TODO: log.Group.SHUT_DOWN

        # This is our stopped life-cycle.
        if self.life_cycle == SystemTick.TICKS_AFTERLIFE:
            self.log_tick(self.life_cycle,
                          log.Level.INFO,
                          f"{self.klass} is stopped and "
                          "in the afterlife. Current life-cycle: {}, tick: {}",
                          str(self.life_cycle), str(self.tick))
            return True
        return False

    def _stopped_life_cycle(self,
                            log_stopped:     Optional[str] = None,
                            log_not_stopped: Optional[str] = None) -> bool:
        '''
        Returns True if Engine's Life-Cycle is in a stopped state.

        If `log_not_stopped` is a string, this will log when engine isn't in a
        'stopped' state at ERROR level with `log_not_stopped` as first part
        of the log, followed by " - it is not stopped.".

        If `log_stopped` is a string, this will log when engine /is/ in a
        'stopped' state at ERROR level with `log_stopped` as first part
        of the log, followed by " - it is stopped/stopped.".
        '''
        # TODO: log.Group.SHUT_DOWN

        # This is our stopped life-cycle.
        if self.life_cycle == SystemTick.TICKS_AFTERLIFE:
            if log_stopped:
                self.log_tick(self.life_cycle,
                              log.Level.ERROR,
                              "{} - it is stopped. "
                              "Current life-cycle: {}, tick: {}",
                              str(self.life_cycle), str(self.tick))
            return True

        # These life-cycles are not stopped.
        if self.life_cycle in (SystemTick.INVALID,
                               SystemTick.TICKS_BIRTH,
                               SystemTick.TICKS_LIFE,
                               SystemTick.TICKS_DEATH):
            if log_not_stopped:
                self.log_tick(self.life_cycle,
                              log.Level.ERROR,
                              " - it is not stopped. "
                              "Current life-cycle: {}, tick: {}",
                              str(self.life_cycle), str(self.tick))
            return False

        # Should this raise or log?
        self.log_tick(self.life_cycle,
                      log.Level.ERROR,
                      "Engine stop/run unknown - it is in an unknown "
                      "state. Current life-cycle: {}, tick: {}",
                      str(self.life_cycle), str(self.tick))

        return False

    def stopping(self,
                 log_stopping:     Optional[str] = None,
                 log_not_stopping: Optional[str] = None) -> bool:
        '''
        Returns True if Engine's Life-Cycle is in a stopping state.
        Ignores any unrunnable healths.

        If `log_not_stopping` is a string, this will log when engine isn't in a
        'stopping' state at ERROR level with `log_not_stopping` as first part
        of the log, followed by " - it is not stopping.".

        If `log_stopping` is a string, this will log when engine /is/ in a
        'stopping' state at ERROR level with `log_stopping` as first part
        of the log, followed by " - it is stopping/stopped.".
        '''
        # TODO: log.Group.SHUT_DOWN

        # Definitely not stopping when we're in these life-cycles.
        if self.life_cycle in (SystemTick.INVALID,
                               SystemTick.TICKS_BIRTH,
                               SystemTick.TICKS_LIFE):
            if log_not_stopping:
                self.log_tick(self.life_cycle,
                              log.Level.ERROR,
                              " - it is not stopping. "
                              "Current life-cycle: {}, tick: {}",
                              str(self.life_cycle), str(self.tick))
            return False

        # Might be stopping when we're in these life-cycles?
        if self.life_cycle == SystemTick.TICKS_DEATH:
            if log_stopping:
                self.log_tick(self.life_cycle,
                              log.Level.ERROR,
                              "{} - it is stopping. "
                              "Current life-cycle: {}, tick: {}",
                              str(self.life_cycle), str(self.tick))
            return True

        if self.life_cycle == SystemTick.TICKS_AFTERLIFE:
            if log_stopping:
                self.log_tick(self.life_cycle,
                              log.Level.ERROR,
                              "{} - it is stopped. "
                              "Current life-cycle: {}, tick: {}",
                              str(self.life_cycle), str(self.tick))
            return True

        # Should this raise or log?
        self.log_tick(self.life_cycle,
                      log.Level.ERROR,
                      "Engine stop/run unknown - it is in an unknown "
                      "state. Current life-cycle: {}, tick: {}",
                      str(self.life_cycle), str(self.tick))

        return False

    def stop(self):
        '''
        Call if you want engine to stop after the end of this tick the graceful
        way - going into the TICKS_DEATH life-cycle and running all the
        end-of-life ticks.
        '''
        # ---
        # Can't Stop (already stopping/stopped) - Log and Leave.
        # ---
        # TODO: log.Group.SHUT_DOWN
        if self.stopping(log_stopping="Cannot stop engine"):
            return

        # ---
        # Stop it!
        # ---
        self._life_cycle.freeze(SystemTick.TICKS_DEATH)

        # # `set_all_health()` complains if health and tick mismatch, so change
        # # tick/life-cycle first.
        # self._tick.next = SystemTick.AUTOPHAGY
        # self.set_all_health(VerediHealth.AUTOPHAGY, True)

    # -------------------------------------------------------------------------
    # Tick Helpers
    # -------------------------------------------------------------------------

    def _update_init(self) -> None:
        '''
        Resets tick variables for the upcoming tick:
          self._tick_health
        '''
        self.set_tick_health(VerediHealth.INVALID, True)

    def _do_tick(self, tick: SystemTick) -> VerediHealth:
        '''
        Call EventManager's and SystemManager's update() functions with
        this tick.

        Currently [2020-12-11], used for everything past start-up ticks.
        '''
        health = VerediHealth.HEALTHY

        # Process our events.
        self.meeting.event.update(tick, self.meeting.time)

        # Let managers, systems do tick processing.
        health = health.update(self.meeting.identity.update(tick),
                               self.meeting.data.update(tick),
                               self.meeting.system.update(tick))
        return health

    # -------------------------------------------------------------------------
    # Life-Cycle: TICKS_BIRTH: Pre-Game Loading
    # -------------------------------------------------------------------------

    def _ticks_birth_in_progress(self,
                                 events_published: Union[int, bool],
                                 health:           VerediHealth) -> bool:
        '''
        We don't validate health - 'run' functions care about that. We only
        care about if it's PENDING and what the start-up ticks themselves /do/.

        `events_published` should either be number of events actually publish,
        or a bool: False for 'not yet', True for 'who cares'.

        `health` should be the tick's health.

        Still setting up if:
          - `events_published` is not zero and also not True
          - `health` is in "limbo"
            - That is, health is neither 'good' nor 'bad'.
              - E.g. VerediHealth.PENDING

        Succeed out of set-up if:
          - None of the above.
        '''
        # Events haven't started or haven't died down: keep going.
        if (events_published != 0
                and events_published is not True):
            self._dbg_tick("Events in progress. Published: {}",
                           events_published)
            return True

        # Systems that run in set up ticks aren't stabalized to a good or bad
        # health yet: keep going.
        if health.limbo:
            self._dbg_tick("Health in limbo: {}", health)
            return True

        # Else... Done I guess?
        self._dbg_tick("Successfully fell through to success case. health: {}",
                       health)
        return False

    def _update_synthesis(self) -> VerediHealth:
        '''
        Note: No EventManager in here as systems and such should be creating.
        EventManager will start processing events in next (MITOSIS) tick.

        Sets (and returns) engine's tick health every tick. Make sure to check
        it.

        Returns
          - tick's health - could differ from self.tick_health.
        '''
        self._update_init()

        # ---
        # Create systems.
        # ---
        # Call Systems'/Managers' loading functions until everyone
        # is done loading.
        self.set_tick_health(self.meeting.system.creation(self.meeting.time),
                             False)

        # ---
        # Tick systems.
        # ---
        # Let any systems that exist now have a SYNTHESIS tick.
        health = self.meeting.system.update(SystemTick.SYNTHESIS)
        self._dbg_tick("Tick: {}, Tick health: {}",
                       self.tick, health)

        # Tick DataManager after systems here for responses to data requests.
        health = health.update(self.meeting.data.update(SystemTick.SYNTHESIS))

        events_dont_care = True
        if (self._ticks_birth_in_progress(events_dont_care, health)
                and health.in_best_health):
            # Set to PENDING if a healthy but not finished tick.
            health = VerediHealth.PENDING

        self.set_tick_health(health, False)
        return health

    def _subscribe(self) -> VerediHealth:
        '''
        Subscribe to the Engine's events.
        '''
        # Request to transition the engine into TICKS_DEATH for (eventual) stop.
        if not self.meeting.event.is_subscribed(EngineStopRequest,
                                                self._event_request_stop):
            self.meeting.event.subscribe(EngineStopRequest,
                                         self._event_request_stop)

        return VerediHealth.HEALTHY

    def _update_mitosis(self) -> None:
        '''
        EventManager will now start processing events. Systems should start
        registering for things, talking to each other, loading data, etc.

        Sets (and returns) engine's tick health every tick. Make sure to check
        it.

        Returns
          - tick health
        '''
        self._update_init()
        health = tick_health_init(SystemTick.MITOSIS,
                                  invalid_ok=True)

        # ---
        # Subscribe systems.
        # ---
        health = health.update(
            self._subscribe(),
            self.meeting.component.subscribe(self.meeting.event),
            self.meeting.entity.subscribe(self.meeting.event),
            self.meeting.system.subscribe(self.meeting.event),
            self.meeting.data.subscribe(self.meeting.event),
            self.meeting.identity.subscribe(self.meeting.event))

        # ---
        # Tick systems.
        # ---
        # Let all our running systems have an MITOSIS tick.
        health = health.update(
            self.meeting.system.update(SystemTick.MITOSIS),
            self.meeting.identity.update(SystemTick.MITOSIS),
            self.meeting.data.update(SystemTick.MITOSIS))
        events_published = self.meeting.event.update(
            SystemTick.MITOSIS,
            self.meeting.time)

        self._dbg_tick("Tick: {}, Tick health: {}, # Events: {}",
                       self.tick,
                       health,
                       events_published)

        if (self._ticks_birth_in_progress(events_published, health)
                and health.in_best_health):
            # Set to PENDING if a healthy but not finished tick.
            health = VerediHealth.PENDING

        self.set_tick_health(health, False)
        return health

    # -------------------------------------------------------------------------
    # Life-Cycle: TICKS_LIFE: In-Game Loops
    # -------------------------------------------------------------------------
    def _update_game_loop(self) -> VerediHealth:
        '''
        Run one single game-loop tick function per call.

        Returns that tick's health.
        '''
        self._update_init()

        try:
            if self.tick == SystemTick.TIME:
                return self._update_time()

            elif self.tick == SystemTick.CREATION:
                return self._update_creation()

            elif self.tick == SystemTick.PRE:
                return self._update_pre()

            elif self.tick == SystemTick.STANDARD:
                return self._update_standard()

            elif self.tick == SystemTick.POST:
                return self._update_post()

            elif self.tick == SystemTick.DESTRUCTION:
                return self._update_destruction()

            else:
                # Else, um... How and why are we here? This is a bad place.
                # TODO [2020-09-27]: Do we need to funeral ourselves here or
                # anything?
                self.log_tick(self.tick,
                              log.Level.ERROR,
                              "FATAL: In {}._update_game_loop() but not in "
                              "any game-loop ticks? Tick: {}. Valid: {}",
                              self.klass,
                              self.tick,
                              _GAME_LOOP_SEQUENCE)
                self.set_all_health(VerediHealth.FATAL, True)
                return self.tick_health

        # Various exceptions we can handle at this level...
        # Or we can't but want to log.
        except VerediError as error:
            # TODO: health thingy
            # Plow on ahead anyways or raise due to debug flags.
            self.log_tick_error(
                self.tick,
                error,
                "Engine's tick() received an error of type '{}' "
                "at: {}",
                type(error), self.meeting.time.error_game_time)
            self.set_all_health(VerediHealth.FATAL, True)
            return self.tick_health

        except Exception as error:
            # TODO: health thingy
            # Plow on ahead anyways or raise due to debug flags.
            self.log_tick_error(
                self.tick,
                error,
                "Engine's tick() received an unknown exception "
                "at: {}",
                self.meeting.time.error_game_time)
            self.set_all_health(VerediHealth.FATAL, True)
            return self.tick_health

        # ---
        # pycodestyle E722 - bare 'except'
        # ---
        # I do want this catch-all here; it's the highest level of the game's
        # run-time. We want our engine to know all the errors that everything
        # it's running produces.
        #
        # In any case, always re-raise. It is probably something important that
        # we shouldn't (?) catch like SystemExit, KeyboardInterrupt,
        # GeneratorExit...
        # ---
        except:  # noqa E722
            # TODO: health thingy

            # Always log in catch-all?
            # For now anyways.
            self._metered_log.exception(
                self.tick,
                VerediError,
                "Engine's tick() received a _very_ "
                "unknown exception at: {}",
                self.meeting.time.error_game_time)

            # Always re-raise in catch-all.
            raise

        self.set_all_health(VerediHealth.FATAL, True)
        msg = ("Engine's _update_game_loop called for a tick it doesn't "
               f"handle. Tick: {self.tick} at "
               f"{self.meeting.time.error_game_time}.")
        error = TickError(msg, None)
        self.log_tick_error(self.tick, error, msg,
                            always_raise=True)
        return self.tick_health

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # Life-Cycle: TICKS_LIFE: Specific Ticks
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def _update_time(self) -> VerediHealth:
        '''
        Time updates as very first part of this tick step.

        Creation, events, system rescheduling.
        '''
        # Time is first. Because it is time, and this is the time to update
        # the time.
        self.meeting.time.delta()

        # Data next?
        health = self.meeting.data.update(SystemTick.TIME)

        # Create systems now.
        health = health.update(
            self.meeting.system.creation(self.meeting.time))

        # Time events, system creation events...
        # System rescheduling, whatever.
        health = health.update(
            self._do_tick(SystemTick.TIME))

        self.set_tick_health(health, False)
        return health

    def _update_creation(self) -> VerediHealth:
        '''
        Main game loop's final update function - birth/creation of
        components & entities.
        '''
        health = tick_health_init(SystemTick.CREATION)

        health = health.update(
            self.meeting.system.creation(self.meeting.time))
        health = health.update(
            self.meeting.component.creation(self.meeting.time))
        health = health.update(
            self.meeting.entity.creation(self.meeting.time))

        health = health.update(
            self._do_tick(SystemTick.CREATION))

        self.set_tick_health(health, False)
        return health

    def _update_pre(self) -> VerediHealth:
        '''
        Main game loop's set-up update function - anything that has to happen
        before SystemTick.STANDARD.
        '''
        health = tick_health_init(SystemTick.PRE)

        health = health.update(
            self._do_tick(SystemTick.PRE))

        self.set_tick_health(health, False)
        return health

    def _update_standard(self) -> VerediHealth:
        '''
        Main game loop's main update tick function.
        '''
        health = tick_health_init(SystemTick.STANDARD)

        health = health.update(
            self._do_tick(SystemTick.STANDARD))

        self.set_tick_health(health, False)
        return health

    def _update_post(self) -> VerediHealth:
        '''
        Main game loop's clean-up update function - anything that has to happen
        after SystemTick.STANDARD.
        '''
        health = tick_health_init(SystemTick.POST)

        health = health.update(
            self._do_tick(SystemTick.POST))
        self.set_tick_health(health, False)
        return health

    def _update_destruction(self) -> VerediHealth:
        '''
        Main game loop's final update function - death/deletion of
        components & entities.
        '''
        health = tick_health_init(SystemTick.DESTRUCTION)
        health = health.update(
            self.meeting.component.destruction(self.meeting.time))
        health = health.update(
            self.meeting.entity.destruction(self.meeting.time))
        health = health.update(
            self.meeting.system.destruction(self.meeting.time))

        health = health.update(
            self._do_tick(SystemTick.DESTRUCTION))

        self.set_tick_health(health, False)
        return health

    # -------------------------------------------------------------------------
    # Life-Cycle: TICKS_DEATH: End-of-Life Ticks
    # -------------------------------------------------------------------------

    def _update_autophagy(self) -> VerediHealth:
        '''
        Graceful game shutdown. Will be called more than once.

        Order of things must not matter in this tick (well, time first, maybe).
        This is just for systems to prep for shut-down as orderly as possible,
        using any/all other systems to e.g. save their data.

        Importantly, AUTOPHAGY does not mean "die". A system must be able to
        process all incoming events/function calls for as long as the engine
        says it's AUTOPHAGY time.
        '''
        self._update_init()
        health = tick_health_init(SystemTick.AUTOPHAGY)

        health = health.update(
            self._do_tick(SystemTick.AUTOPHAGY))

        self.set_tick_health(health, False)
        return health

    def _update_apoptosis(self) -> VerediHealth:
        '''
        Apoptosis! Systems can die now and stop doing their job. They should
        allow the apoptosis tick to call them as much as it wants. They should
        probably not throw exceptions for events or calls that still happen if
        possible - perhaps Null, None, or logs is enough?
        '''
        self._update_init()
        health = tick_health_init(SystemTick.APOPTOSIS)

        health = health.update(
            self._do_tick(SystemTick.APOPTOSIS))

        self.set_tick_health(health, False)
        return health

    def _update_necrosis(self) -> VerediHealth:
        '''
        It's the end of the game as we know it (and I feel fine).

        ECS Managers are finally allowed to die at the end of this tick.

        This should only be called /ONCE/.
        '''
        self._update_init()
        health = tick_health_init(SystemTick.NECROSIS)

        health = health.update(
            self._do_tick(SystemTick.NECROSIS))

        self.set_tick_health(health, False)
        return health

    def _update_funeral(self) -> VerediHealth:
        '''
        Hold a funeral for ourself.

        This should only be called /ONCE/.
        '''
        self._update_init()
        health = tick_health_init(SystemTick.FUNERAL)

        # The funeral (currently) is only for the engine.
        # health = health.update(
        #     self._do_tick(SystemTick.FUNERAL))

        # We're done and shouldn't get another tick. Park tick and life-cycle
        # now so we can test them.
        self._tick.next = SystemTick.FUNERAL | SystemTick.NECROSIS
        self._life_cycle.next = SystemTick.FUNERAL | SystemTick.NECROSIS

        # Are we HEALTHY? Whatever. Use NECROSIS for 'healthy dead'.
        if health.in_best_health:
            health = health.update(VerediHealth.NECROSIS)

        self.set_tick_health(health, False)
        return health

    # TODO: Check return values of system ticks and kill off any that are
    # unhealthy too much?

    # -------------------------------------------------------------------------
    # Unit Testing Helpers
    # -------------------------------------------------------------------------

    def _ut_set_up(self) -> None:
        '''
        Any unit-testing set-up to do?
        '''
        # None currently [2021-01-31].
        # Managers do their own.
        pass

    def _ut_tear_down(self) -> None:
        '''
        Any unit-testing tear-down to do?
        '''
        # None currently [2021-01-31].
        # Managers do their own.
        pass
