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

from veredi.base.null                   import NullNoneOr, null_or_none


# Error Handling
from veredi.logger                      import log
from veredi.logger.metered              import MeteredLog
from veredi.logger.mixin                import LogMixin
from veredi.base.exceptions             import VerediError, HealthError
from .ecs.exceptions                    import TickError

# Other More Basic Stuff
from veredi.data                        import background
from veredi.base.const                  import VerediHealth
from veredi.base.assortments            import CurrentNext
from veredi.data.config.config          import Configuration
from veredi.debug.const                 import DebugFlag
from veredi.time.timer                  import MonotonicTimer

# ECS Managers & Systems
from .ecs.const                         import (SystemTick,
                                                game_loop_start,
                                                game_loop_end,
                                                game_loop_next,
                                                _GAME_LOOP_SEQUENCE)
from .ecs.time                          import TimeManager
from .ecs.event                         import EventManager
from .ecs.component                     import ComponentManager
from .ecs.entity                        import EntityManager
from .ecs.system                        import SystemManager
from .ecs.meeting                       import Meeting

# Identity Manager
from .data.identity.manager             import IdentityManager

# ECS Minions
from .ecs.base.entity                   import Entity

# ---
# Required Systems
# ---
from veredi.game.data.system            import DataSystem


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

class Engine(LogMixin):
    '''
    Implements an ECS-powered game engine with just
    one time-step loop (currently).
    '''

    SYSTEMS_REQUIRED = frozenset((DataSystem, ))

    DOTTED = 'veredi.game.engine'

    _METER_LOG_AMT = 10  # seconds
    '''
    Amount of time (in seconds) that we want our MeteredLog to squelch/ignore
    the same/similar logging messages.
    '''

    def _define_vars(self) -> None:
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
          SystemTick.TICKS_START
          SystemTick.TICKS_RUN
          SystemTick.TICKS_END
        '''

        self._tick: CurrentNext[SystemTick] = CurrentNext(
            SystemTick.INVALID,
            SystemTick.INVALID)
        '''Current individual tick (e.g. SystemTick.STANDARD).'''

        self._timer_life: MonotonicTimer = None
        '''
        Timer for Engine's Life-Cycles.

        TICKS_START:
          - Resets on each tick transition and times each start-up tick.

        TICKS_RUN:
          - Times from entrance into this life-cycle until exit.

        TICKS_END:
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
                 owner:             Entity,
                 campaign_id:       int,
                 configuration:     Configuration,
                 event_manager:     NullNoneOr[EventManager]     = None,
                 time_manager:      NullNoneOr[TimeManager]      = None,
                 component_manager: NullNoneOr[ComponentManager] = None,
                 entity_manager:    NullNoneOr[EntityManager]    = None,
                 system_manager:    NullNoneOr[SystemManager]    = None,
                 identity_manager:  NullNoneOr[IdentityManager]  = None,
                 debug:             NullNoneOr[DebugFlag]        = None
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
        self._log_config(self.dotted())

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
        # Debugging
        # ---
        self._debug = debug

        # ---
        # Make the Managers go to their Meeting.
        # ---
        event     = event_manager     or EventManager(configuration,
                                                      self._debug)
        time      = time_manager      or TimeManager()
        component = component_manager or ComponentManager(configuration,
                                                          event)
        entity    = entity_manager    or EntityManager(configuration,
                                                       event,
                                                       component)
        system    = system_manager    or SystemManager(configuration,
                                                       time,
                                                       event,
                                                       component,
                                                       entity,
                                                       self._debug)
        identity  = identity_manager  or IdentityManager(configuration,
                                                         time,
                                                         event,
                                                         entity,
                                                         self._debug)

        self.meeting = Meeting(
            time,
            event,
            component,
            entity,
            system,
            identity,
            self._debug)
        mtg_bg_data, mtg_bg_owner = self.meeting.get_background()
        background.manager.set(self.meeting.dotted(),
                               self.meeting,
                               mtg_bg_data,
                               mtg_bg_owner)

        # ---
        # Time & Timer Set-Up
        # ---
        # Init Timer starts timing here and then just runs, so this is all we
        # really need to do with it.
        timer_run_name = self.dotted() + '.time.run'
        self._timer_run = time.make_timer(timer_run_name)

        # Life Timer times specific life-cycles (or specific parts of them).
        # We'll reset it in transition places.
        timer_life_name = self.dotted() + '.time.life_cycle'
        self._timer_life = time.make_timer(timer_life_name)

        # Init TimeManager with our tick objects and our timers.
        time.engine_init(self._tick, self._life_cycle,
                         timers={
                             timer_run_name: self._timer_run,
                             timer_life_name: self._timer_life,
                         },
                         default_name=timer_life_name)

        # ---
        # Metered Logging
        # ---
        self._metered_log = MeteredLog(self.dotted(),
                                       log.Level.NOTSET,
                                       time.machine,
                                       fingerprint=True)
        # Tick Life-Cycles
        self._metered_log.meter(SystemTick.TICKS_START,  self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.TICKS_RUN,    self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.TICKS_END,    self._METER_LOG_AMT)

        # Ticks
        self._metered_log.meter(SystemTick.GENESIS,      self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.INTRA_SYSTEM, self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.TIME,         self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.CREATION,     self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.PRE,          self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.STANDARD,     self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.POST,         self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.DESTRUCTION,  self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.APOPTOSIS,    self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.APOCALYPSE,   self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.THE_END,      self._METER_LOG_AMT)
        self._metered_log.meter(SystemTick.FUNERAL,      self._METER_LOG_AMT)

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

    @classmethod
    def dotted(klass: 'Engine') -> str:
        return klass.DOTTED

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

    def _dbg_health(self,
                    tick:        SystemTick,
                    curr_health: VerediHealth,
                    prev_health: VerediHealth,
                    info:        str,
                    *args:       Any,
                    **kwargs:    Any) -> None:
        '''
        Raises an error if health is less than the minimum for runnable engine.

        Adds:
          "Engine's health became unrunnable: {prev} -> {curr}."
          to info/args/kwargs for log message.
        '''
        if (not self.debug_flagged(DebugFlag.RAISE_HEALTH)
                or curr_health.in_runnable_health):
            return

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
        self.dotted() func).

        WARNING: Log may be squelched if its too similar to other recent log
        messages in the `tick`.

        Returns True if logged, False if squelched.
        '''
        kwargs = kwargs or {}
        kwargs = self._log_stack(**kwargs)
        return self._metered_log.log(tick,
                                     level,
                                     msg,
                                     *args,
                                     **kwargs)

    def log_tick_maybe_raise(self,
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

    def _runnable(self, health: VerediHealth) -> bool:
        '''
        Returns true if `health` is not null/none, and is a health over the min
        for running.
        '''
        # ---
        # Bad Value? -> not runnable (False)
        # ---
        # If the health is None/Null, straight up fail.
        if null_or_none(health):
            return False

        # ---
        # Good Health? -> runnable (True)
        # ---
        return health.in_runnable_health

    def running(self, *args: VerediHealth) -> bool:
        '''
        Returns true if our engine health, our tick health, and all `args`
        health are good enough to run a tick.
        '''
        valid_healths = (self._runnable(self.engine_health)
                         or self._runnable(self.tick_health))
        for each in args:
            valid_healths = valid_healths or self._runnable(each)
        return valid_healths

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
        self._dbg_health(self.tick,
                         value,
                         VerediHealth.set(prev_tick, prev_engine),
                         (f"set_all_health "
                          f"{'forcing' if forced else 'setting'} "
                          f"to poor value: {value}."))

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
            self._dbg_health(self.tick,
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
            self._dbg_health(self.tick,
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
        if not self._runnable(self.engine_health):
            self.log_tick(self.life_cycle,
                          log.Level.CRITICAL,
                          "Engine overall health is bad - "
                          "cannot run next tick: {} {}",
                          self.tick, str(self.engine_health))
            healthy = False

        if not self._runnable(self.tick_health):
            self.log_tick(self.life_cycle,
                          log.Level.CRITICAL,
                          "Engine tick health is bad - "
                          "cannot run next tick: {} {}",
                          self.tick, str(self.engine_health))
            healthy = False

        return healthy

    def run(self) -> None:
        '''
        Infinite loop of 'self.run_tick()' until stopped.
        '''
        # TODO [2020-09-28]: Implement this.
        raise NotImplementedError(f"{self.__class__.__name__}.run() is "
                                  "not implemented.")

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

        if self._should_stop():
            self.log_tick(self.life_cycle,
                          log.Level.CRITICAL,
                          "Engine.run() ignored due to engine being in "
                          "incorrect state for running. _should_stop() "
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
            # Run the cycle asked for!
            # ---
            health = self._run_cycle(cycle)
            # This has updated the engine health based on cycle health results.

        finally:
            self.meeting.time.step

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
                                         SystemTick.TICKS_START)
        self._tick.set_if_invalids(SystemTick.INVALID,
                                   SystemTick.GENESIS)

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
        # serial/non-looping life cycle (e.g. TICKS_START: GENESIS ->
        # INTRA_SYSTEM), this will call any transition functions.
        #
        # It can be called during non-transitions - it will figure out if a
        # transition is happening that it cares about.
        self._run_trans_to(cycle_from, cycle_to,
                           self._tick.current, self._tick.next)

        # ------------------------------
        # Pull next into current for the upcomming run.
        # ------------------------------
        cycle = self._life_cycle.cycle()
        self._tick.cycle()

        # Done; return the new current life cycle.
        return cycle

    def _run_trans_to(self,
                      cycle_from: SystemTick,
                      cycle_to:   SystemTick,
                      tick_from:  SystemTick,
                      tick_to:    SystemTick) -> VerediHealth:
        '''
        Calls any once-only, enter/exit engine life-cycle functions. For
        TICKS_START and TICKS_END life-cycles, this calls specific tick cycle
        transitions too.

        Should only be called if not an /invalid/ transition. Can be called for
        non-transitions.

        Keeps a running health check of any tick transition functions called.
        Updates tick health with this, and returns our health (not overall tick
        health).
        '''
        health = VerediHealth.HEALTHY

        # ------------------------------
        # Life-Cycle: TICKS_START
        # ------------------------------
        # TICKS_START isn't what most things care about - they want
        # the specific start ticks...
        if cycle_to == SystemTick.TICKS_START:
            # ---
            # Not a Tick-Cycle: No-op.
            # ---
            if tick_from == tick_to:
                pass

            # ---
            # Tick-Cycles: GENESIS, INTRA_SYSTEM.
            # ---
            elif (tick_to == SystemTick.GENESIS
                  or tick_to == SystemTick.INTRA_SYSTEM):
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
        # Life-Cycle: TICKS_RUN
        # ------------------------------
        elif cycle_to == SystemTick.TICKS_RUN and cycle_from != cycle_to:
            health = health.update(self.meeting.life_cycle(cycle_from,
                                                           cycle_to,
                                                           tick_from,
                                                           tick_to))

        # ------------------------------
        # Life-Cycle: TICKS_END
        # ------------------------------
        elif cycle_to == SystemTick.TICKS_END:
            # ---
            # Not a Tick-Cycle: No-op.
            # ---
            if tick_from == tick_to:
                pass

            # ---
            # Tick-Cycles: APOPTOSIS, APOCALYPSE, THE_END, FUNERAL
            # ---
            elif (tick_to == SystemTick.APOPTOSIS
                  or tick_to == SystemTick.APOCALYPSE
                  or tick_to == SystemTick.THE_END
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
        # ----> TICKS_START
        # ---
        if cycle_to == SystemTick.TICKS_START:
            # Only Valid Transition: INVALID -> TICKS_START
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
        # ----> TICKS_RUN
        # ---
        elif cycle_to == SystemTick.TICKS_RUN:
            # Only Valid Transition: TICKS_START -> TICKS_RUN
            if cycle_from != SystemTick.TICKS_START:
                # Error on bad transition.
                return self._run_trans_error(cycle_from, cycle_to,
                                             SystemTick.TICKS_START)
            else:
                # Log/start timer on good transition.
                # We have the upcoming current cycle as `cycle_to`.
                # Get the upcoming current tick from `self._tick.next`.
                self._run_trans_log(cycle_to,
                                    self._tick.next)
                return cycle_to

        # ---
        # ----> TICKS_END
        # ---
        elif cycle_to == SystemTick.TICKS_END:
            # Valid Transitions: TICKS_START -> TICKS_END
            #                    TICKS_RUN   -> TICKS_END
            if (cycle_from != SystemTick.TICKS_START
                    and cycle_from != SystemTick.TICKS_RUN):
                # Error on bad transition.
                return self._run_trans_error(cycle_from, cycle_to,
                                             (SystemTick.TICKS_RUN,
                                              SystemTick.TICKS_START))
            else:
                # Log/start timer on good transition.
                # We have the upcoming current cycle as `cycle_to`.
                # Get the upcoming current tick from `self._tick.next`.
                self._run_trans_log(cycle_to,
                                    self._tick.next)
                return cycle_to

        # ---
        # ----> THE_END | FUNERAL
        # ---
        elif cycle_to == SystemTick.FUNERAL | SystemTick.THE_END:
            # Valid Transitions: TICKS_END -> THE_END | FUNERAL
            if (cycle_from != SystemTick.TICKS_END):
                # Error on bad transition.
                return self._run_trans_error(cycle_from, cycle_to,
                                             SystemTick.TICKS_END)
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
        self.log_tick_maybe_raise(cycle_from, error, msg, **kwargs)
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
        if cycle == SystemTick.TICKS_START:
            run_health = self._run_cycle_start()

        elif cycle == SystemTick.TICKS_RUN:
            run_health = self._run_cycle_run()

        elif cycle == SystemTick.TICKS_END:
            run_health = self._run_cycle_end()

        else:
            self.log_tick_maybe_raise(
                cycle,
                VerediError,
                "{}._run_cycle({}) received an un-runnable SystemTick: {}. "
                "Valid options are: ",
                self.__class__.__name__,
                cycle, cycle,
                (SystemTick.TICKS_START,
                 SystemTick.TICKS_RUN,
                 SystemTick.TICKS_END))

        self.set_engine_health(run_health, False)
        return run_health

    # -------------------------------------------------------------------------
    # Game Start
    # -------------------------------------------------------------------------

    def _run_cycle_start(self) -> VerediHealth:
        '''
        Will run a tick of start-up per call. Start Ticks loop independently
        until complete, then move on to the next (..., GENESIS, GENESIS, INTRA,
        INTRA, ...). This function will transitions from each start tick to the
        next automatically.

        We will time out if any one tick takes too long to finish and move on
        to the next.

        We will transition out of TICKS_START automatically when we finish
        successfully.

        Returns:
          - VerediHealth.PENDING if TICKS_START life-cycle is still in progress
          - VerediHealth.HEALTHY if we are done.
          - Some other health if we or our systems are going wrong.
        '''

        # ------------------------------
        # First tick: GENESIS
        # ------------------------------
        if self.tick == SystemTick.GENESIS:

            health = self._update_genesis()
            # Health in general will be checked later...
            # Just check for other things and return it.

            # Allow a healthy tick that technically overran the timeout to
            # pass. It's close enough, right?
            if (health != VerediHealth.HEALTHY
                    and self.meeting.time.is_timed_out(self._timer_life,
                                                       'genesis')):
                self.log_tick(self.tick,
                              log.Level.ERROR,
                              "FATAL: {}'s {} took too long "
                              "and timed out! (took {})",
                              self.__class__.__name__,
                              self.tick,
                              self._timer_life.elapsed_str)
                self.set_all_health(VerediHealth.FATAL, True)
                return self.tick_health

            # HEALTHY means done. Set up for our transition.
            if health == VerediHealth.HEALTHY:
                self._tick.next = SystemTick.INTRA_SYSTEM
                # Leave life-cycle as-is.

            # Did a tick of genesis; done for this time.
            return health

        # ------------------------------
        # Second tick: INTRA_SYSTEM
        # ------------------------------
        elif self.tick == SystemTick.INTRA_SYSTEM:

            health = self._update_intrasystem()
            # Health in general will be checked later...
            # Just check for other things and return it.

            # Allow a healthy tick that technically overran the timeout to
            # pass. It's close enough, right?
            if (health != VerediHealth.HEALTHY
                    and self.meeting.time.is_timed_out(self._timer_life,
                                                       'intrasystem')):
                self.log_tick(self.tick,
                              log.Level.ERROR,
                              "FATAL: {}'s {} took too long "
                              "and timed out! (took {})",
                              self.__class__.__name__,
                              self.tick,
                              self._timer_life.elapsed_str)
                self.set_all_health(VerediHealth.FATAL, True)
                return self.tick_health

            # HEALTHY means done. Set up for our transition.
            if health == VerediHealth.HEALTHY:
                # Set up for entering the standard game life-cycle and ticks.
                self._tick.next = SystemTick.TIME
                self._life_cycle.next = SystemTick.TICKS_RUN

            # Did a tick of intra-system; done for this time.
            return health

        # Else, um... How and why are we here? This is a bad place.
        self.log_tick(self.tick,
                      log.Level.ERROR,
                      "FATAL: {} is in {} but not in any "
                      "creation/start-up ticks? {}",
                      self.__class__.__name__,
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

        There is also no automatic normal transition out of the TICKS_RUN
        life-cycle. A system or something will need to trigger the engine's
        apoptosis.

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
            self.log_tick_maybe_raise(self.tick, error, msg)
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
            self._dbg_health(self.tick,
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
            self.log_tick_maybe_raise(self.tick, error, msg)
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
        until complete, then move on to the next (..., APOPTOSIS, APOPTOSIS,
        APOCALYPSE, ..., etc.) . This function will transitions from each start
        tick to the next automatically.

        We will time out if any one tick takes too long to finish and move on
        to the next.

        We will transition life-cycle and tick to FUNERAL after a successful
        finish.

        Returns:
          - VerediHealth.PENDING if TICKS_END life-cycle is still in progress
          - VerediHealth.HEALTHY if we are done.
          - Some other health if we or our systems are going wrong.
        '''
        # ------------------------------
        # First tick: APOPTOSIS
        # ------------------------------
        if self.tick == SystemTick.APOPTOSIS:
            # THE END IS NIGH!

            health = self._update_apoptosis()
            # Health in general will be checked later...
            # Just check for other things and return it.

            # Allow a healthy tick that technically overran the timeout to
            # pass. It's close enough, right?
            if ((health != VerediHealth.APOPTOSIS_SUCCESSFUL
                 or health != VerediHealth.APOPTOSIS_FAILURE)
                and self.meeting.time.is_timed_out(self._timer_life,
                                                   'apoptosis')):
                self.log_tick(self.tick,
                              log.Level.ERROR,
                              "FATAL: {}'s {} took too long "
                              "and timed out! (took {})",
                              self.__class__.__name__,
                              self.tick,
                              self._timer_life.elapsed_str)
                self.set_all_health(VerediHealth.FATAL, True)
                return self.tick_health

            # Are we done? Set up for our transition.
            if (health == VerediHealth.APOPTOSIS_SUCCESSFUL
                    or health == VerediHealth.APOPTOSIS_FAILURE):
                # THE END TIMES ARE UPON US!
                self._tick.next = SystemTick.APOCALYPSE
                # Leave life-cycle as-is.

            # Did a tick of apoptosis; done for this time.
            return health

        # ------------------------------
        # Second tick: APOCALYPSE
        # ------------------------------
        elif self.tick == SystemTick.APOCALYPSE:

            health = self._update_apocalypse()
            # Health in general will be checked later...
            # Just check for other things and return it.

            # Allow a healthy tick that technically overran the timeout to
            # pass. It's close enough, right?
            if (health != VerediHealth.APOCALYPSE_DONE
                    and self.meeting.time.is_timed_out(self._timer_life,
                                                       'apocalypse')):
                self.log_tick(self.tick,
                              log.Level.ERROR,
                              "FATAL: {}'s {} took too long "
                              "and timed out! (took {})",
                              self.__class__.__name__,
                              self.tick,
                              self._timer_life.elapsed_str)
                self.set_all_health(VerediHealth.FATAL, True)
                return self.tick_health

            # HEALTHY means done. Set up for our transition.
            if health == VerediHealth.APOCALYPSE_DONE:
                # THE END IS HERE!
                self._tick.next = SystemTick.THE_END
                # Leave life-cycle as-is.

            # Did a tick of apocalypse; done for this time.
            return health

        # ------------------------------
        # Final tick: THE_END
        # ------------------------------
        elif self.tick == SystemTick.THE_END:
            # There is only one pass through this tick.

            health = self._update_the_end()
            # Health in general will be checked later...
            # Just check for other things and return it.

            # Do the health check for consistency with all the other ticks, but
            # really this is the end and whatever. The health is the health at
            # this point.
            if health != VerediHealth.THE_END:
                self.log_tick(self.tick,
                              log.Level.WARNING,
                              "{}'s {} completed with poor "
                              "or incorrect health. (time: {})",
                              self.__class__.__name__,
                              self.tick,
                              self._timer_life.elapsed_str)
                self.set_all_health(VerediHealth.FATAL, True)
                return self.tick_health

            # Stay in TICKS_END life-cycle.

            # Don't care about anything. We're done. Good day.
            self._tick.next = SystemTick.FUNERAL

            # Farewell.
            return health

        # ------------------------------
        # No, really. THE_END was the final tick.
        # This is just our FUNERAL tick...
        # ------------------------------
        elif self.tick == SystemTick.FUNERAL:
            # There is only one pass through this tick.

            health = self._update_funeral()
            # Health in general will be checked later...
            # Just check for other things and return it.

            # We're done. Park tick and life-cycle.
            self._tick.next = SystemTick.FUNERAL | SystemTick.THE_END
            self._life_cycle.next = SystemTick.FUNERAL | SystemTick.THE_END

            # Do the health check for consistency with all the other ticks, but
            # really this is the end and whatever. The health is the health at
            # this point.
            if health != VerediHealth.THE_END:
                self.log_tick(self.tick,
                              log.Level.WARNING,
                              "{}'s {} completed with poor "
                              "or incorrect health: {} (expected: {}). "
                              "(time: {})",
                              self.__class__.__name__,
                              str(self.tick),
                              str(health),
                              str(VerediHealth.THE_END),
                              self._timer_life.elapsed_str)
                self.set_all_health(VerediHealth.FATAL, True)

            return health

        # Else, um... How and why are we here? This is a bad place.
        # TODO [2020-09-27]: Do we need to funeral ourselves here or anything?
        self.log_tick(self.tick,
                      log.Level.ERROR,
                      "FATAL: {} is in {} but not in any "
                      "tear-down/end ticks? {}",
                      self.__class__.__name__,
                      self.tick,
                      self._timer_life.elapsed_str)
        self.set_all_health(VerediHealth.FATAL, True)
        return self.tick_health

    # -------------------------------------------------------------------------
    # Game Stopping
    # -------------------------------------------------------------------------

    def _should_stop(self):
        return self.engine_health.should_die

    def stop(self):
        '''
        Call if you want engine to stop after the end of this tick the graceful
        way - going into the TICKS_END life-cycle and running all the
        end-of-life ticks.
        '''
        # ---
        # Can't Stop - Log and Leave.
        # ---
        if (self.life_cycle != SystemTick.INVALID
                and self.life_cycle != SystemTick.TICKS_START
                and self.life_cycle != SystemTick.TICKS_RUN):
            if self.life_cycle == SystemTick.TICKS_END:
                self.log_tick(self.life_cycle,
                              log.Level.ERROR,
                              "Cannot stop engine - it is stopping already. "
                              "Current life-cycle: {}, tick: {}",
                              str(self.life_cycle), str(self.tick))
            elif self.life_cycle == SystemTick.AFTER_THE_END:
                self.log_tick(self.life_cycle,
                              log.Level.ERROR,
                              "Cannot stop engine - it is stopped already. "
                              "Current life-cycle: {}, tick: {}",
                              str(self.life_cycle), str(self.tick))
            else:
                self.log_tick(self.life_cycle,
                              log.Level.ERROR,
                              "Cannot stop engine - it is in an unknown "
                              "state. Current life-cycle: {}, tick: {}",
                              str(self.life_cycle), str(self.tick))
            return

        # ---
        # Stop it!
        # ---
        self.set_all_health(VerediHealth.APOPTOSIS, True)
        self._tick.next = SystemTick.APOPTOSIS
        self._life_cycle.next = SystemTick.TICKS_END

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
        '''
        self.meeting.event.update(tick, self.meeting.time)
        health = self.meeting.system.update(tick)
        return health

    # -------------------------------------------------------------------------
    # Life-Cycle: TICKS_START: Pre-Game Loading
    # -------------------------------------------------------------------------

    def _ticks_start_in_progress(self,
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

    def _update_genesis(self) -> VerediHealth:
        '''
        Note: No EventManager in here as systems and such should be creating.
        EventManager will start processing events in next (INTRA_SYSTEM) tick.

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
        # Let any systems that exist now have a GENESIS tick.
        health = self.meeting.system.update(SystemTick.GENESIS)

        self._dbg_tick("Tick: {}, Tick health: {}",
                       self.tick, health)

        events_dont_care = True
        if (self._ticks_start_in_progress(events_dont_care, health)
                and health.in_best_health):
            # Set to PENDING if a healthy but not finished tick.
            health = VerediHealth.PENDING

        self.set_tick_health(health, False)
        return health

    def _update_intrasystem(self) -> None:
        '''
        EventManager will now start processing events. Systems should start
        registering for things, talking to each other, loading data, etc.

        Sets (and returns) engine's tick health every tick. Make sure to check
        it.

        Returns
          - tick health
        '''
        self._update_init()
        health = VerediHealth.INVALID

        # ---
        # Subscribe systems.
        # ---
        health = health.update(
            self.meeting.time.subscribe(self.meeting.event))
        health = health.update(
            self.meeting.component.subscribe(self.meeting.event))
        health = health.update(
            self.meeting.entity.subscribe(self.meeting.event))
        health = health.update(
            self.meeting.system.subscribe(self.meeting.event))

        # ---
        # Tick systems.
        # ---
        # Let all our running systems have an INTRA_SYSTEM tick.
        health = self.meeting.system.update(SystemTick.INTRA_SYSTEM)
        events_published = self.meeting.event.update(
            SystemTick.INTRA_SYSTEM,
            self.meeting.time)

        self._dbg_tick("Tick: {}, Tick health: {}, # Events: {}",
                       self.tick,
                       health,
                       events_published)

        if (self._ticks_start_in_progress(events_published, health)
                and health.in_best_health):
            # Set to PENDING if a healthy but not finished tick.
            health = VerediHealth.PENDING

        self.set_tick_health(health, False)
        return health

    # -------------------------------------------------------------------------
    # Life-Cycle: TICKS_RUN: In-Game Loops
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
                              self.__class__.__name__,
                              self.tick,
                              _GAME_LOOP_SEQUENCE)
                self.set_all_health(VerediHealth.FATAL, True)
                return self.tick_health

        # Various exceptions we can handle at this level...
        # Or we can't but want to log.
        except VerediError as error:
            # TODO: health thingy
            # Plow on ahead anyways or raise due to debug flags.
            self.log_tick_maybe_raise(
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
            self.log_tick_maybe_raise(
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
        self.log_tick_maybe_raise(self.tick, error, msg,
                                  always_raise=True)
        return self.tick_health

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # Life-Cycle: TICKS_RUN: Specific Ticks
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def _update_time(self) -> VerediHealth:
        '''
        Time updates as very first part of this tick step.

        Creation, events, system rescheduling.
        '''
        # Time is first. Because it is time, and this is the time to update
        # the time.
        self.meeting.time.step()

        health = VerediHealth.INVALID

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
        health = VerediHealth.INVALID

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
        health = VerediHealth.INVALID

        health = health.update(
            self._do_tick(SystemTick.PRE))

        self.set_tick_health(health, False)
        return health

    def _update_standard(self) -> VerediHealth:
        '''
        Main game loop's main update tick function.
        '''
        health = VerediHealth.INVALID

        health = health.update(
            self._do_tick(SystemTick.STANDARD))

        self.set_tick_health(health, False)
        return health

    def _update_post(self) -> VerediHealth:
        '''
        Main game loop's clean-up update function - anything that has to happen
        after SystemTick.STANDARD.
        '''
        health = VerediHealth.INVALID

        health = health.update(
            self._do_tick(SystemTick.POST))
        self.set_tick_health(health, False)
        return health

    def _update_destruction(self) -> VerediHealth:
        '''
        Main game loop's final update function - death/deletion of
        components & entities.
        '''
        health = VerediHealth.INVALID
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
    # Life-Cycle: TICKS_END: End-of-Life Ticks
    # -------------------------------------------------------------------------

    def _update_apoptosis(self) -> VerediHealth:
        '''
        Graceful game shutdown. Will be called more than once.

        Order of things must not matter in this tick (well, time first, maybe).
        This is just for systems to prep for shut-down as orderly as possible,
        using any/all other systems to e.g. save their data.

        Importantly, APOPTOSIS does not mean "die". A system must be able to
        process all incoming events/function calls for as long as the engine
        says it's APOPTOSIS time.
        '''
        self._update_init()
        health = VerediHealth.INVALID

        health = health.update(
            self._do_tick(SystemTick.APOPTOSIS))

        self.set_tick_health(health, False)
        return health

    def _update_apocalypse(self) -> VerediHealth:
        '''
        Apocalypse! Systems can die now and stop doing their job. They should
        allow the apocalypse tick to call them as much as it wants. They should
        probably not throw exceptions for events or calls that still happen if
        possible - perhaps Null, None, or logs is enough?
        '''
        self._update_init()
        health = VerediHealth.INVALID

        health = health.update(
            self._do_tick(SystemTick.APOCALYPSE))

        self.set_tick_health(health, False)
        return health

    def _update_the_end(self) -> VerediHealth:
        '''
        It's the end of the game as we know it (and I feel fine).

        ECS Managers are finally allowed to die at the end of this tick.

        This should only be called /ONCE/.
        '''
        self._update_init()
        health = VerediHealth.INVALID

        health = health.update(
            self._do_tick(SystemTick.THE_END))

        self.set_tick_health(health, False)
        return health

    def _update_funeral(self) -> VerediHealth:
        '''
        Hold a funeral for ourself.

        This should only be called /ONCE/.
        '''
        self._update_init()
        health = VerediHealth.INVALID

        health = health.update(
            self._do_tick(SystemTick.FUNERAL))

        # We're done and shouldn't get another tick. Park tick and life-cycle
        # now so we can test them.
        self._tick.next = SystemTick.FUNERAL | SystemTick.THE_END
        self._life_cycle.next = SystemTick.FUNERAL | SystemTick.THE_END

        # Are we HEALTHY? Whatever. Use THE_END for 'healthy dead'.
        if health.in_best_health:
            health = health.update(VerediHealth.THE_END)

        self.set_tick_health(health, False)
        return health

    # TODO: Check return values of system ticks and kill off any that are
    # unhealthy too much?
