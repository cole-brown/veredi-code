# coding: utf-8

'''
Base class for game update loop systems.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Set, Type, Dict, List)
from veredi.base.null import Null, Nullable, NullNoneOr
if TYPE_CHECKING:
    from veredi.base.identity import MonotonicIdGenerator


from veredi.logger             import log
from veredi.base.const         import VerediHealth
from veredi.base.context       import VerediContext
from veredi.data               import background
from veredi.data.config.config import Configuration
from veredi.debug.const        import DebugFlag

from .base.identity            import SystemId
from .base.system              import (System,
                                       SystemLifeCycle)

from veredi.base.exceptions    import VerediError
from .base.exceptions          import SystemErrorV

from .const                    import SystemTick
from .time                     import TimeManager
from .event                    import EcsManagerWithEvents, EventManager, Event
from .component                import ComponentManager
from .entity                   import EntityManager


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class SystemEvent(Event):
    ...


class SystemLifeEvent(Event):
    pass


class SystemManager(EcsManagerWithEvents):
    '''
    Manages the life cycles of entities/components.
    '''

    # -------------------------------------------------------------------------
    # Init / Set Up
    # -------------------------------------------------------------------------

    def __init__(self,
                 config:            NullNoneOr[Configuration],
                 time_manager:      NullNoneOr[TimeManager],
                 event_manager:     NullNoneOr[EventManager],
                 component_manager: NullNoneOr[ComponentManager],
                 entity_manager:    NullNoneOr[EntityManager],
                 debug_flags:       NullNoneOr[DebugFlag]) -> None:
        '''Initializes this thing.'''
        self._debug: Nullable[DebugFlag] = debug_flags or Null()

        # TODO [2020-06-01]: get rid of this class's link to config?
        self._config: NullNoneOr[Configuration] = config or Null()

        # Need to keep EventManager in self._event_manager to conform
        # to EcsManagerWithEvents interface.
        self._event_manager: NullNoneOr[EventManager] = event_manager or Null()

        self._system_id:      'MonotonicIdGenerator' = SystemId.generator()
        self._system_create:  Set[SystemId]          = set()
        self._system_destroy: Set[SystemId]          = set()

        # TODO: Pool instead of allowing stuff to be allocated/deallocated?
        self._system:         Dict[SystemId, System]   = {}
        self._schedule:       List[System]             = []
        self._reschedule:     bool                     = False
        # self._health = {} # TODO: impl this? or put in game class?

    # -------------------------------------------------------------------------
    # Debugging
    # -------------------------------------------------------------------------

    def debug_flagged(self, desired) -> bool:
        '''
        Returns true if SystemManager's debug flags are set to something and
        that something has the desired flag. Returns false otherwise.
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

    def _error_maybe_raise(self,
                           error:      Exception,
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
            # Can't provide an wrapping error type here or my error's stack
            # context gets lost I guess?
            raise log.exception(
                error,
                None,
                msg,
                *args,
                context=context,
                **kwargs
            ) from error
        else:
            log.exception(
                error,
                None,
                msg,
                *args,
                context=context,
                **kwargs)

    # -------------------------------------------------------------------------
    # EcsManagerWithEvents Interface
    # -------------------------------------------------------------------------

    def subscribe(self, event_manager: 'EventManager') -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        for sid in self._system:
            system = self._system[sid]
            if system:
                system.subscribe(event_manager)

        return VerediHealth.HEALTHY

    def apoptosis(self, time: 'TimeManager') -> VerediHealth:
        '''
        Game is ending gracefully. Do graceful end-of-the-world stuff...
        '''
        # Mark every ent for destruction, then run destruction.
        for sid in self._system:
            system = self._system[sid]
            if system:
                system.apoptosis(time)
            self.destroy(sid)
        self.destruction(time)

        return super().apoptosis(time)

    # -------------------------------------------------------------------------
    # API: System Collection Iteration
    # -------------------------------------------------------------------------

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
               entity: 'EntityManager') -> VerediHealth:
        '''
        Engine calls us for each update tick, and we'll call all our
        game systems.
        '''
        # Update schedule at start of the tick, if it needs it.
        if (SystemTick.RESCHEDULE_SYSTEMS.has(tick)
                or not self._schedule):
            self._update_schedule()
            self._log_tick("Updated schedule. tick: {}", tick)

        worst_health = VerediHealth.HEALTHY

        # TODO: self._schedule[tick] is a priority/topographical tree or
        # something that doesn't pop off members each loop?
        for system in self._schedule:
            if not system.wants_update_tick(tick, time):
                continue

            self._log_tick(
                "SystemManager.update({tick}, {time:05.6f}): {system}",
                tick=tick,
                time=time.seconds,
                system=system)

            # Try/catch each system, so they don't kill each other with a
            # single repeating exception.
            try:
                # Update worst_health var with this system's tick return value.
                worst_health = VerediHealth.set(
                    worst_health,
                    system.update_tick(tick, time, component, entity))
                # Only do this if we /really/ want logs.
                if self.debug_flagged(DebugFlag.SYSTEM_DEBUG):
                    self._log_tick("SystemManager.update: {} {} {}",
                                   tick, system, worst_health)

            except VerediError as error:
                # TODO: health thingy
                # Plow on ahead anyways or raise due to debug flags.
                self._error_maybe_raise(
                    error,
                    "SystemManager's {} system caught error type '{}' "
                    "during {} tick (time={}).",
                    str(system), type(error),
                    tick, time.seconds)

            except Exception as error:
                # TODO: health thingy
                # Plow on ahead anyways or raise due to debug flags.
                self._error_maybe_raise(
                    error,
                    "SystemManager's {} system had an unknown exception "
                    "during {} tick (time={}).",
                    str(system), tick, time.seconds)

        return worst_health

    # -------------------------------------------------------------------------
    # API: Component/System Management
    # -------------------------------------------------------------------------

    def get(self,
            desired: Union[SystemId, Type[System]]) -> Nullable[System]:
        '''
        Get an existing/alive system from the system pool and return it.

        Does not care about current life cycle state of system.
        '''
        by_id = self._system.get(desired, None)
        if by_id:
            return by_id

        # Else, type?
        for id in self._system:
            by_type = self._system.get(id, None)
            if isinstance(by_type, desired):
                return by_type

        return Null()

    def create(self,
               sys_class: Type[System],
               context:   Optional[VerediContext]) -> SystemId:
        '''
        Creates a system with the supplied args. This is the start of
        the life cycle of the system.

        Returns the system id.

        System will be cycled to ALIVE during the CREATION tick.
        '''
        for system in self._system.values():
            if isinstance(system, sys_class):
                raise log.exception(
                    None,
                    SystemErrorV,
                    "Cannot create another system of type: {}. "
                    "There is already one running: {}",
                    str(sys_class), str(system))

        sid = self._system_id.next()

        # Stuff event, component managers into kwargs in case system wants them
        # on init.

        system = sys_class(context,
                           sid,
                           background.system.meeting)
        self._system[sid] = system
        self._system_create.add(sid)
        system._life_cycled(SystemLifeCycle.CREATING)
        background.system.life_cycle(system, SystemLifeCycle.CREATING)

        self._event_create(SystemLifeEvent,
                           sid,
                           SystemLifeCycle.CREATING,
                           None, False)

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
        background.system.life_cycle(system, SystemLifeCycle.DESTROYING)

        self._event_create(SystemLifeEvent,
                           system_id,
                           SystemLifeCycle.DESTROYING,
                           None, False)

    # -------------------------------------------------------------------------
    # Game Loop: Component/System Life Cycle Updates
    # -------------------------------------------------------------------------

    def creation(self,
                 time: 'TimeManager') -> VerediHealth:
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
                background.system.life_cycle(system, SystemLifeCycle.ALIVE)

            except SystemErrorV as error:
                log.exception(
                    error,
                    "SystemErrorV in creation() for system_id {}.",
                    system_id)
                # TODO: put this system in... jail or something? Delete?

            self._event_create(SystemLifeEvent,
                               system_id,
                               SystemLifeCycle.ALIVE,
                               None, False)

        self._reschedule = True
        return VerediHealth.HEALTHY

    def destruction(self,
                    time: 'TimeManager') -> VerediHealth:
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
                background.system.life_cycle(system, SystemLifeCycle.DEAD)
                # ...and forget about it.
                self._system.pop(system_id, None)

            except SystemErrorV as error:
                log.exception(
                    error,
                    "SystemErrorV in creation() for system_id {}.",
                    system_id)
                # TODO: put this system in... jail or something? Delete?

            self._event_create(SystemLifeEvent,
                               system_id,
                               SystemLifeCycle.DEAD,
                               None, False)

        # Done with iteration - clear the removes.
        self._system_destroy.clear()

        self._reschedule = True
        return VerediHealth.HEALTHY
