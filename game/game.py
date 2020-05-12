# coding: utf-8

'''
A game of something or other.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Callable, Optional, Iterable, Set

from veredi.bases.exceptions import VerediError
from veredi.entity.exceptions import ComponentError
from .exceptions import SystemError, TickError

from . import time
from .entity import SystemLifeCycle
from . import system
from veredi.entity.component import (EntityId,
                                     INVALID_ENTITY_ID,
                                     Component,
                                     ComponentMetaData)

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


class Game:
    DEBUG_TICK = True

    def __init__(self, owner, campaign_id, repo_manager,
                 time_system=None, life_cycle=None):
        self.repo = repo_manager
        self.owner = owner
        self.campaign = repo_manager.campaign.load_by_id(campaign_id)

        # TODO: load/make session based on... campaign and.... parameter?
        #   - or is that a second init step?

        # ---
        # Required/Special Systems
        # ---
        self._time_setup(time_system)
        self._life_cycle_setup(life_cycle)

        # ---
        # General Systems
        # ---
        self._sys_register = set()
        self._sys_priority = []

    def _time_setup(self, time_system=None):
        self.sys_time = time_system or time.Time()

    def _life_cycle_setup(self, life_cycle):
        self.sys_life_cycle = life_cycle or SystemLifeCycle()

    # -------------------------------------------------------------------------
    # Game Loops
    # -------------------------------------------------------------------------
    def tick(self, time_step):
        '''
        One full swing through the update loop functions.
        '''
        try:
            time = self._update_time(time_step)

            self._update_life(time)
            self._update_pre(time)

            self._update(time)

            self._update_post(time)
            self._update_death(time)

        # Various exceptions we can handle at this level...
        # Or we can't but want to log.
        except TickError as error:
            log.exception(
                error,
                "Game's {} System had a TickError during {} tick (time={}).",
                str(each), tick, time)
            # TODO: health thingy
        except SystemError as error:
            log.exception(
                error,
                "Game's {} System had a SystemError during {} tick (time={}).",
                str(each), tick, time)
            # TODO: health thingy
        except ComponentError as error:
            log.exception(
                error,
                "Game's {} System had a ComponentError during {} tick (time={}).",
                str(each), tick, time)
            # TODO: health thingy
        except VerediError as error:
            log.exception(
                error,
                "Game's {} System had a generic VerediError during {} tick (time={}).",
                str(each), tick, time)
            # TODO: health thingy
        except Exception as error:
            log.exception(
                error,
                "Game's {} System had an unknown exception during {} tick (time={}).",
                str(each), tick, time)
            # TODO: health thingy
            # Plow on ahead anyways.
            # raise
        except:
            log.error(
                "Game's tick had a _very_ unknown exception during {} tick (time={}).",
                tick, time)
            # TODO: health thingy
            # Plow on ahead anyways.
            # raise

    def _update_systems(self, time: float, tick: system.SystemTick) -> None:
        # TODO: self._systems[tick] is a priority queue or something that
        # doesn't pop off members each loop?
        for each in self._systems[tick]:
            if self.DEBUG_TICK:
                log.debug("Tick.{tick} [{time:05.6d}]: {system}",
                          tick=tick,
                          time=time,
                          system=system)

            # Try/catch each system, so they don't kill each other with a single
            # repeating exception.
            try:
                each.update_tick(tick, time, self.sys_life_cycle, self.sys_time)

            # Various exceptions we can handle at this level...
            # Or we can't but want to log.
            except TickError as error:
                log.exception(
                    error,
                    "Game's {} System had a TickError during {} tick (time={}).",
                    str(each), tick, time)
                # TODO: health thingy
            except SystemError as error:
                log.exception(
                    error,
                    "Game's {} System had a SystemError during {} tick (time={}).",
                    str(each), tick, time)
                # TODO: health thingy
            except ComponentError as error:
                log.exception(
                    error,
                    "Game's {} System had a ComponentError during {} tick (time={}).",
                    str(each), tick, time)
                # TODO: health thingy
            except VerediError as error:
                log.exception(
                    error,
                    "Game's {} System had a generic VerediError during {} tick (time={}).",
                    str(each), tick, time)
                # TODO: health thingy
            except Exception as error:
                log.exception(
                    error,
                    "Game's {} System had an unknown exception during {} tick (time={}).",
                    str(each), tick, time)
                # TODO: health thingy
                raise

    def _update_time(self, time_step):
        now = self.sys_time.tick(time_step)

        self._update_systems(now, system.SystemTick.TIME)

    def _update_life(self, time):
        '''
        Main game loop's final update function - birth/creation of
        components & entities.
        '''
        # TODO: have life make a list of new entities?
        self.sys_life_cycle.update_life(time,
                                        self.sys_life_cycle, self.sys_time)

        self._update_systems(now, system.SystemTick.LIFE)

    def _update_pre(self, time):
        '''
        Main game loop's set-up update function - anything that has to happen
        before SystemTick.STANDARD.
        '''
        self._update_systems(now, system.SystemTick.PRE)

    def _update_post(self, time):
        '''
        Main game loop's clean-up update function - anything that has to happen
        after SystemTick.STANDARD.
        '''
        self._update_systems(now, system.SystemTick.POST)

    def _update_death(self, time):
        '''
        Main game loop's final update function - death/deletion of
        components & entities.
        '''
        # TODO: have life make a list of dead entities? sub-components?
        self.sys_life_cycle.update_life(time,
                                        self.sys_life_cycle, self.sys_time)

        self._update_systems(now, system.SystemTick.LIFE)

    def _update(self, time_step):
        '''
        Main game loop's main update tick function.
        '''
        self._update_systems(now, system.SystemTick.STANDARD)

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
    # Game Management
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
