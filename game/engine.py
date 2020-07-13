# coding: utf-8

'''
A game of something or other.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Type, Any)
if TYPE_CHECKING:
    from veredi.base.context import VerediContext

import enum

# from typing import Optional
from veredi.base.null import Nullable, NullNoneOr, Null

# Error Handling
from veredi.logger             import log
from veredi.base.exceptions    import VerediError

# Other More Basic Stuff
from veredi.data               import background
from veredi.base.const         import VerediHealth
from veredi.data.config.config import Configuration

# ECS Managers & Systems
from .ecs.const                import SystemTick, DebugFlag
from .ecs.time                 import TimeManager
from .ecs.event                import EventManager
from .ecs.component            import ComponentManager
from .ecs.entity               import EntityManager
from .ecs.system               import SystemManager
from .ecs.meeting              import Meeting

# ECS Minions
from .ecs.base.entity          import Entity


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# ------------------------------
# Engine's Life Cycle State
# ------------------------------

@enum.unique
class EngineLifeCycle(enum.Enum):
    INVALID    = 0
    CREATING   = enum.auto()
    ALIVE      = enum.auto()
    DESTROYING = enum.auto()
    DEAD       = enum.auto()

    # ---
    # To String
    # ---

    def __str__(self):
        return (
            f"{self.__class__.__name__}.{self._name_}"
        )

    def __repr__(self):
        return (
            f"SLC.{self._name_}"
        )


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

class Engine:
    '''
    Implements an ECS-powered game engine with just
    one time-step loop (currently).
    '''

    def __init__(self,
                 owner:             Entity,
                 campaign_id:       int,
                 configuration:     Configuration,
                 event_manager:     NullNoneOr[EventManager]     = None,
                 time_manager:      NullNoneOr[TimeManager]      = None,
                 component_manager: NullNoneOr[ComponentManager] = None,
                 entity_manager:    NullNoneOr[EntityManager]    = None,
                 system_manager:    NullNoneOr[SystemManager]    = None,
                 debug:             NullNoneOr[DebugFlag]        = None
                 ) -> None:
        # # TODO: Make session a System, put these in there?
        # self.repo = repo_manager
        # self.owner = owner
        # self.campaign = repo_manager.campaign.load_by_id(campaign_id)

        # TODO: load/make session based on... campaign and.... parameter?
        #   - or is that a second init step?

        # ---
        # Engine Status
        # ---
        self._engine_health = VerediHealth.INVALID
        self._life_cycle    = EngineLifeCycle.INVALID
        self._tick_state    = SystemTick.INVALID
        self._tick_health   = VerediHealth.INVALID

        # ---
        # Debugging
        # ---
        self._debug = debug

        # ---
        # Required/Special Systems
        # ---
        self.config    = configuration     or Configuration()

        # ---
        # Make the Managers go to their Meeting.
        # ---
        event     = event_manager     or EventManager()
        time      = time_manager      or TimeManager()
        component = component_manager or ComponentManager(self.config,
                                                          event)
        entity    = entity_manager    or EntityManager(self.config,
                                                       event,
                                                       component)
        system    = system_manager    or SystemManager(self.config,
                                                       time,
                                                       event,
                                                       component,
                                                       entity,
                                                       self._debug)
        self.meeting = Meeting(
            time,
            event,
            component,
            entity,
            system,
            self._debug)
        background.system.set_meeting(self.meeting)

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

    def _log_tick(self,
                  msg: str,
                  *args: Any,
                  **kwargs: Any) -> None:
        '''
        Debug Log output if DebugFlag has the LOG_TICK flag set.
        '''
        if not self.debug_flagged(DebugFlag.LOG_TICK):
            return

        # Bump up stack by one so it points to our caller.
        log.incr_stack_level(kwargs)
        log.debug(msg, *args, **kwargs)

    # -------------------------------------------------------------------------
    # Engine Overall Health
    # -------------------------------------------------------------------------

    @property
    def engine_health(self) -> VerediHealth:
        '''
        Overall health of the engine itself.
        '''
        return self._engine_health

    def set_engine_health(self, value: VerediHealth, forced: bool) -> None:
        '''
        Set the current health of the engine overall.
        If `forced`, just straight up set it.
        Else, use VerediHealth.set() to pick the worst of current and value.
        '''
        if forced:
            self._engine_health = value
        self._engine_health = VerediHealth.set(self._engine_health,
                                               value)

    def _engine_healthy(self) -> bool:
        '''
        Are we in a runnable state?
        '''
        return self._engine_health.good

    @property
    def tick_health(self) -> VerediHealth:
        '''
        Health of current tick.
        '''
        return self._tick_health

    def set_tick_health(self, value: VerediHealth, forced: bool) -> None:
        '''
        Set the health of current tick.
        If `forced`, just straight up set it.
        Else, use VerediHealth.set() to pick the worst of current and value.
        '''
        if forced:
            self._tick_health = value
        self._tick_health = VerediHealth.set(self._tick_health,
                                             value)

    @property
    def life_cycle(self) -> EngineLifeCycle:
        return self._life_cycle

    def _error_maybe_raise(self,
                           error:      Exception,
                           v_err_type: Optional[Type[VerediError]],
                           msg:        Optional[str],
                           *args:      Any,
                           context:    Optional['VerediContext'] = None,
                           **kwargs:   Any):
        '''
        Log an error, and raise it if `self.debug_flagged` to do so.
        '''
        kwargs = kwargs or {}
        log.incr_stack_level(kwargs)
        if self.debug_flagged(DebugFlag.RAISE_ERRORS):
            raise log.exception(
                error,
                v_err_type,
                msg,
                *args,
                context=context,
                **kwargs
            ) from error
        else:
            log.exception(
                error,
                v_err_type,
                msg,
                *args,
                context=context,
                **kwargs)

    # -------------------------------------------------------------------------
    # Game Start/Stop
    # -------------------------------------------------------------------------

    def _should_stop(self):
        return self.engine_health.should_die

    def stop(self):
        '''
        Call if you want engine to stop after the end of this tick, then run
        it's apoptosis() function, then exit gracefully.
        '''
        self.set_engine_health(VerediHealth.APOPTOSIS, True)

    def run(self, cycle: EngineLifeCycle) -> VerediHealth:
        '''
        Run through a life cycle of the Engine: CREATING, ALIVE, DESTROYING

        Engine.life_cycle must start in correct state to transition.
        Post-CREATING:   INVALID
          CREATING:      INVALID    -> CREATING
          ALIVE:         CREATING   -> ALIVE
          DESTROYING:    ALIVE      -> DESTROYING
        Post-DESTROYING: DESTROYING -> DEAD
        '''
        if not self._should_stop():
            self.set_engine_health(
                self._run_create(),
                False)

        if not self._should_stop():
            self.set_engine_health(
                self._run_alive(),
                False)

        if not self._should_stop():
            self.set_engine_health(
                self._run_destroy(),
                False)

        return self.engine_health

    def _run_create(self) -> VerediHealth:
        from_state = EngineLifeCycle.INVALID
        to_state = EngineLifeCycle.CREATING
        self._log_tick("Start of _run_create.")
        if self._life_cycle != from_state:
            msg = (f"Cannot transition to '{to_state}' from "
                   f"'{self._life_cycle}'; only from '{from_state}'")
            error = ValueError(msg)
            self._error_maybe_raise(error, None, msg)
            return VerediHealth.UNHEALTHY

        self._life_cycle = to_state

        self._update_genesis()
        self._update_intra_sys()

        return VerediHealth.HEALTHY

    def _run_alive(self) -> VerediHealth:
        from_state = EngineLifeCycle.CREATING
        to_state = EngineLifeCycle.ALIVE
        self._log_tick("Start of _run_alive.")
        if self._life_cycle != from_state:
            msg = (f"Cannot transition to '{to_state}' from "
                   f"'{self._life_cycle}'; only from '{from_state}'")
            error = ValueError(msg)
            self._error_maybe_raise(error, None, msg)
            return VerediHealth.UNHEALTHY

        self._life_cycle = to_state

        while not self._should_stop():
            self.tick()

        return VerediHealth.HEALTHY

    def _run_destroy(self) -> VerediHealth:
        from_state = EngineLifeCycle.ALIVE
        to_state = EngineLifeCycle.DESTROYING
        self._log_tick("Start of _run_destroy.")
        if self._life_cycle != from_state:
            msg = (f"Cannot transition to '{to_state}' from "
                   f"'{self._life_cycle}'; only from '{from_state}'")
            error = ValueError(msg)
            self._error_maybe_raise(error, None, msg)
            return VerediHealth.UNHEALTHY

        self._life_cycle = to_state

        self.apoptosis()

        self._life_cycle = EngineLifeCycle.DEAD
        return VerediHealth.HEALTHY

    def apoptosis(self) -> VerediHealth:
        '''
        Graceful game shutdown.
        '''
        self.set_engine_health(VerediHealth.APOPTOSIS, True)
        self.set_tick_health(VerediHealth.APOPTOSIS, True)

        # Should I fire off an event, or should I call directly? Both? Have
        # Engine only call Managers directly and EventManager can do a big
        # event if it wants.

        # Ordering matters. We want the systems that depend on things to go
        # after those things.
        # E.g. EntityManager depends on ComponentManager, so it goes after.
        # E.g. They all might want updated time.
        health = self.meeting.time.apoptosis()
        if health != VerediHealth.APOPTOSIS:
            log.critical("TimeManager.apoptosis() returned an unexpected "
                         "VerediHealth: {} (time: {})",
                         health, self.meeting.time.seconds)

        health = self.meeting.event.apoptosis(self.meeting.time)
        if health != VerediHealth.APOPTOSIS:
            log.critical("EventManager.apoptosis() returned an unexpected "
                         "VerediHealth: {} (time: {})",
                         health, self.meeting.time.seconds)

        health = self.meeting.component.apoptosis(self.meeting.time)
        if health != VerediHealth.APOPTOSIS:
            log.critical("ComponentManager.apoptosis() returned an unexpected "
                         "VerediHealth: {} (time: {})",
                         health, self.meeting.time.seconds)

        health = self.meeting.entity.apoptosis(self.meeting.time)
        if health != VerediHealth.APOPTOSIS:
            log.critical("EntityManager.apoptosis() returned an unexpected "
                         "VerediHealth: {} (time: {})",
                         health, self.meeting.time.seconds)

        health = self.meeting.system.apoptosis(self.meeting.time)
        if health != VerediHealth.APOPTOSIS:
            log.critical("SystemManager.apoptosis() returned an unexpected "
                         "VerediHealth: {} (time: {})",
                         health, self.meeting.time.seconds)

        return self.engine_health

    # -------------------------------------------------------------------------
    # Pre-Game Loading Loop
    # -------------------------------------------------------------------------

    def _setting_up(self,
                    health: VerediHealth,
                    events_published: Union[int, bool]) -> bool:
        '''
        `health` should be tick health.

        `events_published` should either be number of events actually publish,
        or a bool: False for 'not yet', True for 'who cares'.

        Fail out of set-up if:
          - `health` indicates we should die.
          - engine has been told we should stop.
          - TimeManager is timing and has reach time out value.

        Still setting up if:
          - `events_published` is not zero and also not True
          - `health` is in "limbo"
            - That is, health is neither 'good' nor 'bad'.
              - E.g. VerediHealth.PENDING

        Succeed out of set-up if:
          - None of the above.
        '''
        # Done if we've gotten a bad enough health to die: just fail set up.
        if health.should_die:
            self._log_tick("Should die. health: {}", health)
            return False

        # We've been told to stop by external sources: just fail set up.
        if self._should_stop():
            self._log_tick("Should stop.")
            return False

        # We timed out: fail set up.
        if (self.meeting.time.timing
                and self.meeting.time.is_timed_out(
                    self.meeting.time._SHORT_TIMEOUT_SEC)):
            self._log_tick("Timed out. Setting health to FATAL.")
            self.set_engine_health(VerediHealth.FATAL, True)
            self.set_tick_health(VerediHealth.FATAL, True)
            return False

        # Events haven't started or haven't died down: keep going.
        if (events_published != 0
                and events_published is not True):
            self._log_tick("Events in progress. Published: {}",
                           events_published)
            return True

        # Systems that run in set up ticks aren't stabalized to a good or bad
        # health yet: keep going.
        if health.limbo:
            self._log_tick("Health in limbo: {}", health)
            return True

        # Else... Done I guess?
        self._log_tick("Successfully fell through to success case. health: {}",
                       health)
        return False

    def _update_genesis(self) -> None:
        '''
        Note: No EventManager in here as systems and such should be creating.
        EventManager will start processing events in next (INTRA_SYSTEM) tick.
        '''
        # Call Systems'/Managers' loading functions until everyone
        # is done loading.
        self._tick_state  = SystemTick.GENESIS
        self.set_tick_health(VerediHealth.INVALID, True)

        self.meeting.time.start_timeout()
        while self._setting_up(self.tick_health, True):
            # Force first health set to get this loop's health started fresh.
            # Do not force from there in order to get 'worst' of the loop.

            # Create systems now.
            self.set_tick_health(
                self.meeting.system.creation(self.meeting.time),
                True)

            # Update any that want this tick.
            self.set_tick_health(
                self.meeting.system.update(SystemTick.GENESIS,
                                           self.meeting.time,
                                           self.meeting.component,
                                           self.meeting.entity),
                False)

            self._log_tick("Tick state: {}, Tick health: {}",
                           self._tick_state, self.tick_health)

    def _update_intra_sys(self) -> None:
        # Call Systems'/Managers' intra_sys functions until everyone
        # is done talking.
        self._tick_state = SystemTick.INTRA_SYSTEM
        self.set_tick_health(VerediHealth.INVALID, True)

        # First up, tell folks to subscribe?
        # TODO: or should this be elsewhere?
        self.meeting.time.subscribe(self.meeting.event)
        self.meeting.component.subscribe(self.meeting.event)
        self.meeting.entity.subscribe(self.meeting.event)
        self.meeting.system.subscribe(self.meeting.event)

        self.meeting.time.start_timeout()
        events_published = False  # False for "we haven't started yet".
        while self._setting_up(self._tick_health, events_published):
            # Force first health set to get this loop's health started fresh.
            # Do not force from there in order to get 'worst' of the loop.

            # Update any that want this tick.
            self.set_tick_health(
                self.meeting.system.update(SystemTick.INTRA_SYSTEM,
                                           self.meeting.time,
                                           self.meeting.component,
                                           self.meeting.entity),
                True)

            events_published = self.meeting.event.update(
                SystemTick.INTRA_SYSTEM,
                self.meeting.time)
            self._log_tick("Tick state: {}, Tick health: {}, # Events: {}",
                           self._tick_state,
                           self.tick_health,
                           events_published)

    # -------------------------------------------------------------------------
    # In-Game Loops
    # -------------------------------------------------------------------------

    def tick(self) -> None:
        '''
        One full swing through the update loop functions.
        '''
        now_secs = -1  # In case _update_time errors out.
        try:
            now_secs = self._update_time()

            self._update_creation()
            self._update_pre()

            self._update()

            self._update_post()
            self._update_destruction()

        # Various exceptions we can handle at this level...
        # Or we can't but want to log.
        except VerediError as error:
            # TODO: health thingy
            # Plow on ahead anyways or raise due to debug flags.
            self._error_maybe_raise(
                error,
                None,
                "Engine's tick() received an error of type '{}' "
                "at time {}.",
                type(error), now_secs)

        except Exception as error:
            # TODO: health thingy
            # Plow on ahead anyways or raise due to debug flags.
            self._error_maybe_raise(
                error,
                None,
                "Engine's tick() received an unknown exception "
                "at time {}.",
                now_secs)

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
            log.error(
                None,
                VerediError,
                "Engine's tick() received a _very_ "
                "unknown exception at time {}.",
                now_secs)

            # Always re-raise in catch-all.
            raise

    def _update_time(self) -> None:
        self._tick_state = SystemTick.TIME
        # Time is first. Because it is time.
        self.meeting.time.step()
        # Create systems now.
        self.meeting.system.creation(self.meeting.time)

        # Time events, system creation events...
        self.meeting.event.update(SystemTick.TIME, self.meeting.time)
        # System rescheduling, whatever.
        self.meeting.system.update(SystemTick.TIME, self.meeting.time,
                                   self.meeting.component, self.meeting.entity)

    def _update_creation(self) -> None:
        '''
        Main game loop's final update function - birth/creation of
        components & entities.
        '''
        self._tick_state = SystemTick.CREATION
        self.meeting.component.creation(self.meeting.time)
        self.meeting.entity.creation(self.meeting.time)

        self.meeting.event.update(SystemTick.CREATION, self.meeting.time)
        self.meeting.system.update(SystemTick.CREATION, self.meeting.time,
                                   self.meeting.component, self.meeting.entity)

    def _update_pre(self) -> None:
        '''
        Main game loop's set-up update function - anything that has to happen
        before SystemTick.STANDARD.
        '''
        self._tick_state = SystemTick.PRE
        self.meeting.event.update(SystemTick.PRE, self.meeting.time)
        self.meeting.system.update(SystemTick.PRE, self.meeting.time,
                                   self.meeting.component, self.meeting.entity)

    def _update(self) -> None:
        '''
        Main game loop's main update tick function.
        '''
        self._tick_state = SystemTick.STANDARD
        self.meeting.event.update(SystemTick.STANDARD, self.meeting.time)
        self.meeting.system.update(SystemTick.STANDARD, self.meeting.time,
                                   self.meeting.component, self.meeting.entity)

    def _update_post(self) -> None:
        '''
        Main game loop's clean-up update function - anything that has to happen
        after SystemTick.STANDARD.
        '''
        self._tick_state = SystemTick.POST
        self.meeting.event.update(SystemTick.POST, self.meeting.time)
        self.meeting.system.update(SystemTick.POST, self.meeting.time,
                                   self.meeting.component, self.meeting.entity)

    def _update_destruction(self) -> None:
        '''
        Main game loop's final update function - death/deletion of
        components & entities.
        '''
        self._tick_state = SystemTick.DESTRUCTION
        self.meeting.component.destruction(self.meeting.time)
        self.meeting.entity.destruction(self.meeting.time)
        self.meeting.system.destruction(self.meeting.time)

        self.meeting.event.update(SystemTick.DESTRUCTION, self.meeting.time)
        self.meeting.system.update(SystemTick.DESTRUCTION, self.meeting.time,
                                   self.meeting.component, self.meeting.entity)

    # TODO: Check return values of system ticks and kill off any that are
    # unhealthy too much?
