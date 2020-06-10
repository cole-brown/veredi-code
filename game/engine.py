# coding: utf-8

'''
A game of something or other.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional

# Error Handling
from veredi.logger import log

from veredi.base.exceptions import VerediError

# Other More Basic Stuff
from veredi.base.const import VerediHealth
from veredi.data.config.config import Configuration

# ECS Managers & Systems
from .ecs.const import SystemTick, DebugFlag
from .ecs.entity import EntityManager
from .ecs.component import ComponentManager
from .ecs.system import SystemManager
from .ecs.time import TimeManager
from .ecs.event import EventManager

# ECS Minions
from .ecs.base.entity import Entity


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

class Engine:
    '''
    Implements an ECS-powered game engine with just
    one time-step loop (currently).
    '''

    def __init__(self,
                 owner:             Entity,
                 campaign_id:       int,
                 configuration:     Configuration,
                 event_manager:     Optional[EventManager]     = None,
                 time_manager:      Optional[TimeManager]      = None,
                 component_manager: Optional[ComponentManager] = None,
                 entity_manager:    Optional[EntityManager]    = None,
                 system_manager:    Optional[SystemManager]    = None,
                 debug:             Optional[DebugFlag]        = None
                 ) -> None:
        # # TODO: Make session a System, put these in there?
        # self.repo = repo_manager
        # self.owner = owner
        # self.campaign = repo_manager.campaign.load_by_id(campaign_id)

        # TODO: load/make session based on... campaign and.... parameter?
        #   - or is that a second init step?

        self._health = VerediHealth.HEALTHY

        # ---
        # Debugging
        # ---
        self._debug = debug

        # ---
        # Required/Special Systems
        # ---
        self.config    = configuration     or Configuration()
        self.event     = event_manager     or EventManager()
        self.time      = time_manager      or TimeManager()
        self.component = component_manager or ComponentManager(self.config,
                                                               self.event)
        self.entity    = entity_manager    or EntityManager(self.config,
                                                            self.event,
                                                            self.component)
        self.system    = system_manager    or SystemManager(self.config,
                                                            self.time,
                                                            self.event,
                                                            self.component,
                                                            self.entity,
                                                            self._debug)
        # TODO: give these folks a back-link to me? Or the Event system for
        # regstration step???

        # ---
        # General Systems
        # ---
        self._sys_registration = set()
        self._sys_schedule = []

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

    # -------------------------------------------------------------------------
    # Game Start/Stop
    # -------------------------------------------------------------------------

    def _should_stop(self):
        return self._health.should_die

    def stop(self):
        '''
        Call if you want engine to stop after the end of this tick, then run
        it's apoptosis() function, then exit gracefully.
        '''
        self._health = VerediHealth.APOPTOSIS

    def run(self) -> VerediHealth:
        '''
        Infinite loop the game until quitting time.
        '''
        while not self._should_stop():
            self.tick()

        return self.apoptosis()

    def apoptosis(self) -> VerediHealth:
        '''
        Graceful game shutdown.
        '''
        # Should I fire off an event, or should I call directly? Both? Have
        # Engine only call Managers directly and EventManager can do a big
        # event if it wants.

        # Ordering matters. We want the systems that depend on things to go
        # after those things.
        # E.g. EntityManager depends on ComponentManager, so it goes after.
        # E.g. They all might want updated time.
        health = self.time.apoptosis()
        if health != VerediHealth.APOPTOSIS:
            log.critical("TimeManager.apoptosis() returned an unexpected "
                         "VerediHealth: {} (time: {})",
                         health, self.time.seconds)

        health = self.event.apoptosis(self.time)
        if health != VerediHealth.APOPTOSIS:
            log.critical("EventManager.apoptosis() returned an unexpected "
                         "VerediHealth: {} (time: {})",
                         health, self.time.seconds)

        health = self.component.apoptosis(self.time)
        if health != VerediHealth.APOPTOSIS:
            log.critical("ComponentManager.apoptosis() returned an unexpected "
                         "VerediHealth: {} (time: {})",
                         health, self.time.seconds)

        health = self.entity.apoptosis(self.time)
        if health != VerediHealth.APOPTOSIS:
            log.critical("EntityManager.apoptosis() returned an unexpected "
                         "VerediHealth: {} (time: {})",
                         health, self.time.seconds)

        health = self.system.apoptosis(self.time)
        if health != VerediHealth.APOPTOSIS:
            log.critical("SystemManager.apoptosis() returned an unexpected "
                         "VerediHealth: {} (time: {})",
                         health, self.time.seconds)

        return VerediHealth.APOPTOSIS

    # -------------------------------------------------------------------------
    # Pre-Game Loading Loop
    # -------------------------------------------------------------------------
    def setting_up(self):
        return (not self._should_stop()
                and not self.time.is_timed_out(self.time._DEFAULT_TIMEOUT_SEC))

    def set_up(self):
        # Call Systems'/Managers' loading functions until everyone
        # is done loading.
        retval = VerediHealth.HEALTHY
        self.time.start_timeout()
        while self.setting_up(retval):
            self.system.update(SystemTick.SET_UP, self.time,
                               self.component, self.entity)
            self.event.update(SystemTick.SET_UP, self.time)

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
            if self.debug_flagged(DebugFlag.RAISE_ERRORS):
                raise log.exception(
                    error,
                    None,
                    "Engine's tick() received an error of type '{}' "
                    "at time {}.",
                    type(error), now_secs) from error
            else:
                log.exception(
                    error,
                    None,
                    "Engine's tick() received a VerediError at time {}.",
                    now_secs)

        except Exception as error:
            # TODO: health thingy
            # Plow on ahead anyways or raise due to debug flags.
            if self.debug_flagged(DebugFlag.RAISE_ERRORS):
                raise log.exception(
                    error,
                    None,
                    "Engine's tick() received an unknown exception "
                    "at time {}.",
                    now_secs) from error
            else:
                log.exception(
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
        # Time is first. Because it is time.
        self.time.step()
        # Create systems now.
        self.system.creation(self.time)

        # Time events, system creation events...
        self.event.update(SystemTick.TIME, self.time)
        # System rescheduling, whatever.
        self.system.update(SystemTick.TIME, self.time,
                           self.component, self.entity)

    def _update_creation(self) -> None:
        '''
        Main game loop's final update function - birth/creation of
        components & entities.
        '''
        self.component.creation(self.time)
        self.entity.creation(self.time)

        self.event.update(SystemTick.CREATION, self.time)
        self.system.update(SystemTick.CREATION, self.time,
                           self.component, self.entity)

    def _update_pre(self) -> None:
        '''
        Main game loop's set-up update function - anything that has to happen
        before SystemTick.STANDARD.
        '''
        self.event.update(SystemTick.PRE, self.time)
        self.system.update(SystemTick.PRE, self.time,
                           self.component, self.entity)

    def _update(self) -> None:
        '''
        Main game loop's main update tick function.
        '''
        self.event.update(SystemTick.STANDARD, self.time)
        self.system.update(SystemTick.STANDARD, self.time,
                           self.component, self.entity)

    def _update_post(self) -> None:
        '''
        Main game loop's clean-up update function - anything that has to happen
        after SystemTick.STANDARD.
        '''
        self.event.update(SystemTick.POST, self.time)
        self.system.update(SystemTick.POST, self.time,
                           self.component, self.entity)

    def _update_destruction(self) -> None:
        '''
        Main game loop's final update function - death/deletion of
        components & entities.
        '''
        self.component.destruction(self.time)
        self.entity.destruction(self.time)
        self.system.destruction(self.time)

        self.event.update(SystemTick.DESTRUCTION, self.time)
        self.system.update(SystemTick.DESTRUCTION, self.time,
                           self.component, self.entity)

    # TODO: Check return values of system ticks and kill off any that are
    # unhealthy too much?
