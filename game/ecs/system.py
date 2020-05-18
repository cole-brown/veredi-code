# coding: utf-8

'''
Base class for game update loop systems.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Iterable, Set, Union, Any, Type
import enum
import decimal

from veredi.logger import log

from .base.identity import (MonotonicIdGenerator,
                            ComponentId,
                            EntityId,
                            SystemId)
from .base.component import (Component,
                             ComponentError)
from .base.entity import Entity
from .base.system import (System,
                          SystemLifeCycle)

from veredi.base.exceptions import VerediError
from .base.exceptions import ComponentError, EntityError
from .exceptions import SystemError, TickError

from .const import SystemTick, SystemPriority, SystemHealth, DebugFlag
from .event import EcsManagerWithEvents


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# Code
# ------------------------------------------------------------------------------

class SystemManager(EcsManagerWithEvents):
    '''
    Manages the life cycles of entities/components.
    '''

    def __init__(self, debug_flags: Optional[DebugFlag]) -> None:
        '''Initializes this thing.'''
        self._debug = debug_flags

        # TODO: Pools instead of allowing stuff to be allocated/deallocated?
        self._system_id:      MonotonicIdGenerator     = MonotonicIdGenerator(SystemId)
        self._system_create:  Set[SystemId]            = set()
        self._system_destroy: Set[SystemId]            = set()

        self._system:         Dict[SystemId, System]   = {}
        self._schedule:       List[System]             = []
        self._reschedule:     bool                     = False
        # self._health = {} # TODO: impl this? or put in game class?

        self._event:          'EventManager'           = None


    # --------------------------------------------------------------------------
    # Debugging
    # --------------------------------------------------------------------------

    def debug_flagged(self, desired) -> bool:
        '''
        Returns true if SystemManager's debug flags are set to something and that
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

    # --------------------------------------------------------------------------
    # EcsManagerWithEvents Interface
    # --------------------------------------------------------------------------

    def subscribe(self, event_manager: 'EventManager') -> SystemHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        self._event = event_manager
        return SystemHealth.HEALTY

    def apoptosis(self, time: 'TimeManager') -> SystemHealth:
        '''
        Game is ending gracefully. Do graceful end-of-the-world stuff...
        '''
        # Mark every ent for destruction, then run destruction.
        for sid in self._system:
            self.destroy(sid)
        self.destruction(time)

        return super().apoptosis(time)

    # --------------------------------------------------------------------------
    # API: System Collection Iteration
    # --------------------------------------------------------------------------

    def _update_schedule(self) -> None:
        '''
        Recreate the system schedule from the current systems, if needed.

        Will only happen once per tick.
        '''
        if not self._reschedule:
            return

        # Clear out our current schedule, and remake it.
        self._schedule.clear()
        for sid in self._system:
            system = self._system[sid]
            self._schedule.append(system)

        # Priority sort (highest priority firstest)
        self._schedule.sort(key=System.sort_key)

        self._reschedule = False

    def update(self,
               tick: SystemTick,
               time: 'TimeManager',
               component: 'ComponentManager',
               entity: 'EntityManager') -> None:
        '''
        Engine calls us for each update tick, and we'll call all our
        game systems.
        '''
        # Update schedule at start of the tick, if it needs it.
        if tick == SystemTick.TIME:
            self._update_schedule()

        # TODO: self._schedule[tick] is a priority/topographical tree or
        # something that doesn't pop off members each loop?
        for system in self._schedule:
            if not system.wants_update_tick(tick, time):
                continue

            if self.debug_flagged(DebugFlag.LOG_TICK):
                log.debug("SystemManager.update({tick}, {time:05.6f}): {system}",
                          tick=tick,
                          time=time.get_tick(),
                          system=system)

            # Try/catch each system, so they don't kill each other with a single
            # repeating exception.
            try:
                system.update_tick(tick, time, component, entity)

            # Various exceptions we can handle at this level...
            # Or we can't but want to log.
            except TickError as error:
                log.exception(
                    error,
                    "SystemManager's {} system had a TickError "
                    "during {} tick (time={}).",
                    str(system), tick, time.get_tick())
                if self.debug_flagged(DebugFlag.RAISE_ERRORS):
                    raise
                # TODO: health thingy
            except SystemError as error:
                log.exception(
                    error,
                    "SystemManager's {} system had a SystemError "
                    "during {} tick (time={}).",
                    str(system), tick, time.get_tick())
                if self.debug_flagged(DebugFlag.RAISE_ERRORS):
                    raise
                # TODO: health thingy
            except ComponentError as error:
                log.exception(
                    error,
                    "SystemManager's {} system had a ComponentError "
                    "during {} tick (time={}).",
                    str(system), tick, time.get_tick())
                if self.debug_flagged(DebugFlag.RAISE_ERRORS):
                    raise
                # TODO: health thingy
            except EntityError as error:
                log.exception(
                    error,
                    "SystemManager's {} system had a EntityError "
                    "during {} tick (time={}).",
                    str(system), tick, time.get_tick())
                if self.debug_flagged(DebugFlag.RAISE_ERRORS):
                    raise
                # TODO: health thingy
            except VerediError as error:
                log.exception(
                    error,
                    "SystemManager's {} system had a generic VerediError "
                    "during {} tick (time={}).",
                    str(system), tick, time.get_tick())
                if self.debug_flagged(DebugFlag.RAISE_ERRORS):
                    raise
                # TODO: health thingy
            except Exception as error:
                log.exception(
                    error,
                    "SystemManager's {} system had an unknown exception "
                    "during {} tick (time={}).",
                    str(system), tick, time.get_tick())
                if self.debug_flagged(DebugFlag.RAISE_ERRORS):
                    raise
                # TODO: health thingy
                raise

    # --------------------------------------------------------------------------
    # API: Component/System Management
    # --------------------------------------------------------------------------

    def get(self, system_id: SystemId) -> Optional[System]:
        '''
        Get an existing/alive system from the system pool and return it.

        Does not care about current life cycle state of system.
        '''
        return self._system.get(system_id, None)

    def create(self,
               sys_class: Type[System],
               *args: Any,
               **kwargs: Any) -> SystemId:
        '''
        Creates a system with the supplied args. This is the start of
        the life cycle of the system.

        Returns the system id.

        System will be cycled to ALIVE during the CREATION tick.
        '''
        sid = self._system_id.next()

        system = sys_class(sid, *args, **kwargs)
        self._system[sid] = system
        self._system_create.add(sid)
        system._life_cycled(SystemLifeCycle.CREATING)

        # TODO Event?

        return sid

    def destroy(self, system_id: SystemId) -> None:
        '''
        Cycles system to DESTROYING now... This is the 'end' of the life cycle
        of the system.

        System will be fully removed from our pools on the DESTRUCTION tick.
        '''
        system = self.get(system_id)
        if not system:
            return

        system._life_cycle = SystemLifeCycle.DESTROYING
        self._system_destroy.add(system.id)
        # TODO Event?

    # --------------------------------------------------------------------------
    # Game Loop: Component/System Life Cycle Updates
    # --------------------------------------------------------------------------

    def creation(self,
                 time: 'TimeManager') -> SystemHealth:
        '''
        Runs before the start of the tick/update loop.

        Updates entities in CREATING state to ALIVE state.
        '''

        for system_id in self._system_create:
            # System should exist in our pool, otherwise we don't
            # care about it...
            system = self.get(system_id)
            if (not system
                    or system._life_cycle != SystemLifeCycle.CREATING):
                continue

            try:
                # Bump it to alive now.
                system._life_cycled(SystemLifeCycle.ALIVE)

            except SystemError as error:
                log.exception(
                    error,
                    "SystemError in creation() for system_id {}.",
                    system_id)
                # TODO: put this system in... jail or something? Delete?

            # TODO EVENT HERE!

        self._reschedule = True
        return SystemHealth.HEALTHY

    def destruction(self,
                    time: 'TimeManager') -> SystemHealth:
        '''
        Runs after the end of the tick/update loop.

        Removes entities not in ALIVE state from system pools.
        '''

        # Check all entities in the destroy pool...
        for system_id in self._system_destroy:
            # System should exist in our pool, otherwise we don't
            # care about it...
            system = self.get(system_id)
            if (not system
                    # INVALID, CREATING, DESTROYING will all be
                    # cycled into death. ALIVE can stay.
                    or system._life_cycle == SystemLifeCycle.ALIVE):
                continue

            try:
                # Bump it to dead now.
                system._life_cycled(SystemLifeCycle.DEAD)
                # ...and forget about it.
                self._system.pop(system_id, None)

            except SystemError as error:
                log.exception(
                    error,
                    "SystemError in creation() for system_id {}.",
                    system_id)
                # TODO: put this system in... jail or something? Delete?

            # TODO EVENT HERE!

        # Done with iteration - clear the removes.
        self._system_destroy.clear()

        self._reschedule = True
        return SystemHealth.HEALTHY

