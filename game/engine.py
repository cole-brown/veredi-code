# coding: utf-8

'''
A game of something or other.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
from typing import Callable, Optional, Iterable, Set
import enum
import decimal

# Error Handling
from veredi.logger import log

from veredi.bases.exceptions import VerediError
from veredi.entity.exceptions import ComponentError, EntityError
from .ecs.exceptions import SystemError, TickError

# ECS Managers & Systems
from .ecs.entity import EntityManager
from .ecs.component import ComponentManager
from .ecs.system import SystemTick, SystemPriority, SystemHealth, System
from .ecs.time import TimeManager
from .ecs.event import EventManager

# ECS Minions
from veredi.entity.component import (ComponentId,
                                     INVALID_COMPONENT_ID,
                                     Component)
from veredi.entity.entity import (EntityId,
                                  INVALID_ENTITY_ID,
                                  Entity)

# Game Data
from veredi.data.repository import manager


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# Game is:
#   manager of whole shebang
#
# game should get:
#   campaign info (name, owner?, system?, ...)
#   repo... types?
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


# Campaign: setting of game. saved state of game. ids of entities/systems tied to game

# Setting: d20 or whatever?
#   - "rule-set"?

# Session: one sit-down's worth of a game.
#   collection of scenes?
#   ids of entities/systems used in that session?

# Entity: just an id?

# Component: a thing an entity has

# System: a thing that triggers off of component(s) to update an entity

#



# NOTE: Owner is DM. But someone else could be DM too...
#     : Maybe a session DM list or something to keep track?
#     : Can a player be a DM too (e.g. to help newbie DM)?
#       - At the same time as they're playing?

#
# NOTE: DM is god. They must be able to change everything, ideally on a
# temporary OR permanent basis.

@enum.unique
class EngineDebug(enum.Flag):
    LOG_TICK     = enum.auto()
    '''Output a log message each tick at debug level.'''

    RAISE_ERRORS = enum.auto()
    '''Re-raises any errors/exceptions caught in Engine object itself.'''

    UNIT_TESTS = LOG_TICK | RAISE_ERRORS

    def has(self, flag):
        return ((self & flag) == flag)


class Engine:
    '''
    Implements an ECS-powered game engine with just
    one time-step loop (currently).
    '''

    def __init__(self,
                 owner:             Entity,
                 campaign_id:       int,
                 repo_manager:      manager.Manager,
                 event_manager:     Optional[EventManager]     = None,
                 entity_manager:    Optional[EntityManager]    = None,
                 component_manager: Optional[ComponentManager] = None,
                 # system_manager:  Optional[SystemManager]    = None,
                 time_manager:      Optional[TimeManager]      = None,
                 debug:             Optional[EngineDebug]      = None
                 ) -> None:
        # # TODO: Make session a System, put these in there?
        # self.repo = repo_manager
        # self.owner = owner
        # self.campaign = repo_manager.campaign.load_by_id(campaign_id)

        # TODO: load/make session based on... campaign and.... parameter?
        #   - or is that a second init step?

        # ---
        # Debugging
        # ---
        self.debug = debug

        # ---
        # Required/Special Systems
        # ---
        self.event     = event_manager     or EventManager()
        self.component = component_manager or ComponentManager()
        self.entity    = entity_manager    or EntityManager(self.component)
        # TODO THIS SYSTEM MANAGER
        #self.system    = system_manager    or SystemManager()
        self.time      = time_manager      or TimeManager()
        # TODO: give these folks a back-link to me? Or the Event system for regstration step???

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
    def debug(self) -> EngineDebug:
        '''Returns current debug flags.'''
        return self._debug

    @debug.setter
    def debug(self, value: EngineDebug) -> None:
        '''
        Set current debug flags. No error/sanity checks.
        Universe could explode; use wisely.
        '''
        self._debug = value


    # --------------------------------------------------------------------------
    # Engine Set Up
    # --------------------------------------------------------------------------

    def register(self, *systems: System) -> None:
        '''
        Systems wanting to run in the game loop should register themselves
        before the set_up() call comes.
        '''
        for sys in systems:
            self._sys_registration.add(sys)

    def set_up(self) -> None:
        '''
        Systems wanting to run in the game loop should register themselves
        before the set_up() call comes.
        '''
        # Start with what we have, if anything.
        schedule = set(self._sys_schedule)
        self._sys_schedule.clear()

        # Update with registered systems.
        schedule.update(self._sys_registration)
        self._sys_registration.clear()

        # Priority sort (highest priority firstest)
        self._sys_schedule.extend(schedule)
        self._sys_schedule.sort(key=System.sort_key)


    # -------------------------------------------------------------------------
    # Game Loops
    # -------------------------------------------------------------------------
    def tick(self) -> None:
        '''
        One full swing through the update loop functions.
        '''
        now_secs = -1  # In case _update_time errors out.
        try:
            now_secs = self._update_time()

            self._update_life(now_secs)
            self._update_pre(now_secs)

            self._update(now_secs)

            self._update_post(now_secs)
            self._update_death(now_secs)

        # Various exceptions we can handle at this level...
        # Or we can't but want to log.
        except TickError as error:
            log.exception(
                error,
                "Engine's tick() received a TickError at time {}.",
                now_secs)
            # TODO: health thingy
            if self.debug_flagged(EngineDebug.RAISE_ERRORS):
                raise
        except SystemError as error:
            log.exception(
                error,
                "Engine's tick() received a SystemError at time {}.",
                now_secs)
            # TODO: health thingy
            if self.debug_flagged(EngineDebug.RAISE_ERRORS):
                raise
        except ComponentError as error:
            log.exception(
                error,
                "Engine's tick() received a ComponentError at time {}.",
                now_secs)
            # TODO: health thingy
            if self.debug_flagged(EngineDebug.RAISE_ERRORS):
                raise
        except EntityError as error:
            log.exception(
                error,
                "Engine's tick() received a EntityError at time {}.",
                now_secs)
            # TODO: health thingy
            if self.debug_flagged(EngineDebug.RAISE_ERRORS):
                raise
        except VerediError as error:
            log.exception(
                error,
                "Engine's tick() received a generic VerediError at time {}.",
                now_secs)
            # TODO: health thingy
            if self.debug_flagged(EngineDebug.RAISE_ERRORS):
                raise
        except Exception as error:
            print(self.debug)
            print(error)
            log.exception(
                error,
                "Engine's tick() received an unknown exception at time {}.",
                now_secs)
            # TODO: health thingy
            # Plow on ahead anyways.
            # raise
            if self.debug_flagged(EngineDebug.RAISE_ERRORS):
                raise
        except:
            log.error(
                "Engine's tick() received a _very_ unknown exception at time {}.",
                now_secs)
            # TODO: health thingy
            # Plow on ahead anyways.
            # raise
            if self.debug_flagged(EngineDebug.RAISE_ERRORS):
                raise

    def _update_systems(self, time: decimal.Decimal, tick: SystemTick) -> None:
        # TODO: self._sys_schedule[tick] is a priority queue or something that
        # doesn't pop off members each loop?
        for each in self._sys_schedule:
            if not each.wants_update_tick(tick, time):
                continue

            if self.debug_flagged(EngineDebug.LOG_TICK):
                log.debug("Tick.{tick} [{time:05.6f}]: {system}",
                          tick=tick,
                          time=time,
                          system=each)

            # Try/catch each system, so they don't kill each other with a single
            # repeating exception.
            try:
                each.update_tick(tick, time, self.entity, self.time)

            # Various exceptions we can handle at this level...
            # Or we can't but want to log.
            except TickError as error:
                log.exception(
                    error,
                    "Engine's {} System had a TickError during {} tick (time={}).",
                    str(each), tick, time)
                if self.debug_flagged(EngineDebug.RAISE_ERRORS):
                    raise
                # TODO: health thingy
            except SystemError as error:
                log.exception(
                    error,
                    "Engine's {} System had a SystemError during {} tick (time={}).",
                    str(each), tick, time)
                if self.debug_flagged(EngineDebug.RAISE_ERRORS):
                    raise
                # TODO: health thingy
            except ComponentError as error:
                log.exception(
                    error,
                    "Engine's {} System had a ComponentError during {} tick (time={}).",
                    str(each), tick, time)
                if self.debug_flagged(EngineDebug.RAISE_ERRORS):
                    raise
                # TODO: health thingy
            except EntityError as error:
                log.exception(
                    error,
                    "Engine's {} System had a EntityError during {} tick (time={}).",
                    str(each), tick, time)
                if self.debug_flagged(EngineDebug.RAISE_ERRORS):
                    raise
                # TODO: health thingy
            except VerediError as error:
                log.exception(
                    error,
                    "Engine's {} System had a generic VerediError during {} tick (time={}).",
                    str(each), tick, time)
                if self.debug_flagged(EngineDebug.RAISE_ERRORS):
                    raise
                # TODO: health thingy
            except Exception as error:
                log.exception(
                    error,
                    "Engine's {} System had an unknown exception during {} tick (time={}).",
                    str(each), tick, time)
                if self.debug_flagged(EngineDebug.RAISE_ERRORS):
                    raise
                # TODO: health thingy
                raise

    def _update_time(self) -> decimal.Decimal:
        now = self.time.step()

        self._update_systems(now, SystemTick.TIME)

        return now

    def _update_life(self, now: decimal.Decimal) -> None:
        '''
        Main game loop's final update function - birth/creation of
        components & entities.
        '''
        # TODO: have life make a list of new entities?
        self.entity.creation(self.time)

        self._update_systems(now, SystemTick.LIFE)

    def _update_pre(self, now: decimal.Decimal) -> None:
        '''
        Main game loop's set-up update function - anything that has to happen
        before SystemTick.STANDARD.
        '''
        self._update_systems(now, SystemTick.PRE)

    def _update_post(self, now: decimal.Decimal) -> None:
        '''
        Main game loop's clean-up update function - anything that has to happen
        after SystemTick.STANDARD.
        '''
        self._update_systems(now, SystemTick.POST)

    def _update_death(self, now: decimal.Decimal) -> None:
        '''
        Main game loop's final update function - death/deletion of
        components & entities.
        '''
        # TODO: have life make a list of dead entities? sub-components?
        self.entity.destruction(self.time)

        self._update_systems(now, SystemTick.DEATH)

    def _update(self, now: decimal.Decimal) -> None:
        '''
        Main game loop's main update tick function.
        '''
        self._update_systems(now, SystemTick.STANDARD)

    # TODO: Check return values of system ticks and kill off any that are
    # unhealthy too much?

    # ---  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    # -
    # ---
    # -------
    # -----------
    #        TODO: Turn Entity/Player into an ECS instead.
    # -----------
    # -------
    # ---
    # -
    # ---  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

        # ---
        # Tick Order:
        #   (change at your own peril!)
        #                                                             (dooooom!)
        # ---

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

    # --------------------------------------------------------------------------
    # Engine Management
    # --------------------------------------------------------------------------

    # add player to session
    #   invite?
    # add player to game/campaign
    #   invite?
    # add monster(s)
    # add other stuff... items, currency...
    # remove *
    #   cancel invite?


    # --------------------------------------------------------------------------
    # Combat
    # --------------------------------------------------------------------------

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


    # --------------------------------------------------------------------------
    # Most of these are probably campaign/dm/session/player things...
    # --------------------------------------------------------------------------

    # ---
    # Session.Location?
    # ---

    # party location in: universe, region, local group, galaxy, region, system, region, planet, region, subregion, continent, etc etc...
    #  - they can split the party, so...

    # encounter locations?

    # points of interest...
    #   stuff there: NPCs, treasure, dungeons, encounters, shops, whatever
    #   DM notes

    # ---
    # Session.Time
    # ---
    # time related things for Session
    #  - in game: curr datetime, datetime for each session, duration of each session, etc...
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
