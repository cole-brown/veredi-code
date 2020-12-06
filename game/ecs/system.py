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
from veredi.base.dicts         import DoubleIndexDict
from veredi.data               import background
from veredi.data.config.config import Configuration
from veredi.debug.const        import DebugFlag
from veredi.time.timer         import MonotonicTimer

from .base.identity            import SystemId
from .base.system              import (System,
                                       SystemLifeCycle)

from veredi.base.exceptions    import VerediError, HealthError
from .base.exceptions          import SystemErrorV

from .const                    import SystemTick
from .time                     import TimeManager, MonotonicTimer
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

    DOTTED = 'veredi.game.ecs.system'

    # -------------------------------------------------------------------------
    # Init / Set Up
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        super()._define_vars()

        self._debug: Nullable[DebugFlag] = Null()
        '''Debug Flags.'''

        # Need to keep EventManager in self._event_manager to conform
        # to EcsManagerWithEvents interface.
        # TODO [2020-10-03]: Remove EventManager or keep in the interface?
        self._event_manager: NullNoneOr[EventManager] = Null()
        '''ECS Event Manager.'''

        self._system_id:      'MonotonicIdGenerator' = SystemId.generator()
        '''
        SystemId generator for during system creation.

        This is the definitive place for SystemIds and they should only be
        created from this generator.
        '''

        self._system_create:  Set[SystemId]          = set()
        '''Systems that will be created soon.'''

        self._system_destroy: Set[SystemId]          = set()
        '''Systems that will be destroyed soon.'''

        # TODO: Pool instead of allowing stuff to be allocated/deallocated?
        self._system:         DoubleIndexDict        = DoubleIndexDict('id',
                                                                       'type')
        '''Collection of all Systems. Indexed by both ID and TYPE.'''

        self._schedule:       List[System]           = []
        '''
        Our schedule for the next/current game-loop (SystemTick.TICKS_RUN)
        cycle. Not rescheduled every tick - only when something bumps
        self._reschedule to True.
        '''

        self._reschedule:     bool                   = False
        '''
        Flag for redoing our System tick priority schedule (self._schedule).
        '''

        self._timer: Optional['MonotonicTimer'] = MonotonicTimer()
        '''
        We'll use this timer in certain life-cycles/tick-cycles (e.g.
        apoptosis) to let systems time how long it's been since the start of
        that cycle.
        '''

    def __init__(self,
                 config:            NullNoneOr[Configuration],
                 time_manager:      NullNoneOr[TimeManager],
                 event_manager:     NullNoneOr[EventManager],
                 component_manager: NullNoneOr[ComponentManager],
                 entity_manager:    NullNoneOr[EntityManager],
                 debug_flags:       NullNoneOr[DebugFlag]) -> None:

        super().__init__()

        self._debug = debug_flags or Null()
        self._event_manager = event_manager or Null()

    @classmethod
    def dotted(klass: 'SystemManager') -> str:
        return klass.DOTTED

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
        kwargs = self._log_stack(**kwargs)
        self._log_debug(msg, *args, **kwargs)

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
        kwargs = self._log_stack(**kwargs)
        if self.debug_flagged(DebugFlag.RAISE_ERRORS):
            # Can't provide an wrapping error type here or my error's stack
            # context gets lost I guess?
            raise self._log_exception(
                error,
                None,
                msg,
                *args,
                context=context,
                **kwargs
            ) from error
        else:
            self._log_exception(
                error,
                None,
                msg,
                *args,
                context=context,
                **kwargs)

    def _dbg_health(self,
                    system:      System,
                    curr_health: VerediHealth,
                    prev_health: Optional[VerediHealth],
                    info:        str,
                    *args:       Any,
                    tick:        Optional[SystemTick] = None,
                    life:        Optional[SystemLifeCycle] = None,
                    **kwargs:    Any) -> None:
        '''
        Raises an error if health is less than the minimum for runnable engine.

        Adds:
          "{system.dotted()}'s health became unrunnable: {prev} -> {curr}."
          to info/args/kwargs for log message.
        '''
        # Sometimes, it's ok if they're dying...
        if (system.life_cycle == SystemLifeCycle.DESTROYING
                or system.life_cycle == SystemLifeCycle.DEAD):
            return

        # Sometimes, we don't care...
        if (not self.debug_flagged(DebugFlag.RAISE_HEALTH)
                or curr_health.in_runnable_health):
            return

        # But right now we do care. Check the health and raise an error.
        during = '<unknown>'
        if tick and life:
            during = f"tick {str(tick)} and life-cycle {life}"
        elif tick:
            during = str(tick)
        elif life:
            during = str(life)

        health_transition = None
        if prev_health is None:
            health_transition = str(curr_health)
        else:
            health_transition = f"{str(prev_health)} -> {str(curr_health)}"

        msg = (f"{system.dotted()}'s health became unrunnable "
               f"during {during}: {health_transition}. ")
        error = HealthError(curr_health, prev_health, msg, None)
        raise self._log_exception(error,
                                  None,
                                  msg + info,
                                  *args,
                                  **kwargs)

    # -------------------------------------------------------------------------
    # Life-Cycle Transitions
    # -------------------------------------------------------------------------

    def _cycle_genesis(self) -> VerediHealth:
        '''
        Entering TICKS_START life-cycle's first tick: genesis. System creation,
        initializing stuff, etc.
        '''
        self._timer.start()
        return VerediHealth.HEALTHY

    def _cycle_intrasystem(self) -> VerediHealth:
        '''
        Entering TICKS_START life-cycle's next tick - intra-system
        communication, loading, configuration...
        '''
        self._timer.start()
        return VerediHealth.HEALTHY

    def _cycle_game_loop(self) -> VerediHealth:
        '''
        Entering TICKS_RUN life-cycle, aka the main game loop.

        Prepare for the main event.
        '''
        self._timer.start()
        return VerediHealth.HEALTHY

    def _cycle_apoptosis(self) -> VerediHealth:
        '''
        Entering TICKS_END life-cycle's first tick: apoptosis. Initial
        structured shut-down tick cycle. Systems, managers, etc must still be
        in working order for this - saving data, unloading, final
        communications, etc.

        Game is ending gracefully. Call each system once to alert them of this.
        '''
        # Set up timer, set ourself to in apoptosis phase.
        self._timer.start()

        # Set each system to apoptosis phase.
        health = VerediHealth.INVALID
        for sid in self._system.id:
            system = self._system.id[sid]
            if (system
                    and not self._system_in_cycle(system,
                                                  SystemLifeCycle.APOPTOSIS)):
                health = health.update(
                    self._life_cycle_set(system, SystemLifeCycle.APOPTOSIS))

        return health

    def _cycle_apocalypse(self) -> VerediHealth:
        '''
        Entering TICKS_END life-cycle's next tick: apocalypse. Systems can now
        become unresponsive. Managers must stay responsive.

        Game is ending systems gracefully or not. Call each system once to
        alert them of this.
        '''
        # Reset timer, set ourself to in apocalypse phase.
        self._timer.start()

        # Set each system to apocalypse phase.
        health = VerediHealth.INVALID
        for sid in self._system.id:
            system = self._system.id[sid]
            if (system
                    and not self._system_in_cycle(system,
                                                  SystemLifeCycle.APOCALYPSE)):
                health = health.update(
                    self._life_cycle_set(system, SystemLifeCycle.APOCALYPSE))

        return health

    def _cycle_the_end(self) -> VerediHealth:
        '''
        Entering TICKS_END life-cycle's final tick: the_end.

        Managers must finish the tick, so don't kill yourself here... Not quite
        yet.

        Game is ending. This is our 'entering the end' call.
        Systems will also have a chance at 'update the end'.
        Then they will all be destroyed.
        '''
        # Reset timer, set ourself to in the_end phase.
        self._timer.start()

        # Set each system to the_end phase.
        health = VerediHealth.INVALID
        for sid in self._system.id:
            system = self._system.id[sid]
            if (system
                    and not self._system_in_cycle(system,
                                                  SystemLifeCycle.THE_END)):
                health = health.update(
                    self._life_cycle_set(system, SystemLifeCycle.THE_END))

        return health

    def _cycle_thanatos(self) -> VerediHealth:
        '''
        The God Of Death is here.

        We may die now.
        '''
        return VerediHealth.THE_END

    # -------------------------------------------------------------------------
    # EcsManagerWithEvents Interface
    # -------------------------------------------------------------------------

    def subscribe(self, event_manager: 'EventManager') -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        health = VerediHealth.INVALID
        for sid in self._system.id:
            system = self._system.id[sid]
            if system:
                health = health.update(system.subscribe(event_manager))

        return health

    def _system_in_cycle(self,
                         system: System,
                         desired: SystemLifeCycle) -> bool:
        '''
        Checks `system`'s life-cycle.

        Returns true if it matches `desired` cycle.
        '''
        return system.life_cycle == desired

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
        for sid in self._system.id:
            system = self._system.id[sid]
            self._schedule.append(system)

        # Priority sort (highest priority firstest)
        self._schedule.sort(key=System.sort_key)

        self._reschedule = False

    def update(self, tick: SystemTick) -> VerediHealth:
        '''
        Engine calls us for each update tick, and we'll call all our
        game systems.
        '''
        # Update schedule at start of the tick, if it needs it.
        if (SystemTick.RESCHEDULE_SYSTEMS.has(tick)
                or not self._schedule):
            self._update_schedule()
            self._log_tick("Updated schedule. tick: {}", tick)

        time = background.system.meeting.time

        worst_health = VerediHealth.HEALTHY
        # TODO: self._schedule[tick] is a priority/topographical tree or
        # something that doesn't pop off members each loop?
        for system in self._schedule:
            if not system.wants_update_tick(tick):
                continue

            self._log_tick(
                "SystemManager.update({tick}, {time:05.6f}): {system}",
                tick=tick,
                time=time.seconds,
                system=system)

            # Try/catch each system, so they don't kill each other with a
            # single repeating exception.
            try:
                # Call the tick.
                sys_tick_health = system.update_tick(tick)
                self._dbg_health(system,
                                 sys_tick_health,
                                 worst_health,
                                 (f"SystemManager.update for {tick} of "
                                  f"{system.dotted()} resulted in poor "
                                  f"health: {sys_tick_health}."),
                                 tick=tick)

                # Update worst_health var with this system's tick return value.
                worst_health = VerediHealth.set(
                    worst_health,
                    sys_tick_health)

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

        if tick == SystemTick.THE_END:
            # Set all to destroy, then run destruction().
            self._destroy_all(tick, time)

        # Update this for next go.
        self._tick_type_prev = tick

        return worst_health

    # -------------------------------------------------------------------------
    # System Life-Cycle Management
    # -------------------------------------------------------------------------

    def _life_cycle_set(self,
                        system:            System,
                        cycle:             SystemLifeCycle,
                        log_to_background: bool = True) -> None:
        '''
        Set system's life-cycle to cycle (if it isn't already).

        Creats a life-cycle record in background.system if `log_to_background`.
        '''
        health = system._life_cycled(cycle)
        self._dbg_health(system,
                         health,
                         None,
                         (f"SystemManager._life_cycle_set for {cycle} of "
                          f"{system.dotted()} resulted in poor health: "
                          f"{health}."),
                         tick=None,
                         life=cycle)

        if log_to_background:
            background.system.life_cycle(system, cycle, health)
        return health

    # -------------------------------------------------------------------------
    # API: Component/System Management
    # -------------------------------------------------------------------------

    def get(self,
            desired: Union[SystemId, Type[System]]) -> Nullable[System]:
        '''
        Get an existing/alive system from the system pool and return it.

        Does not care about current life cycle state of system.
        '''
        # DoubleIndexDict's get() will look for both SystemId and Type[System].
        system = self._system.get(desired, None)
        if system:
            return system

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
        for system in self._system.id.values():
            if isinstance(system, sys_class):
                raise self._log_exception(
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
        self._system.set(sid, sys_class, system)
        self._system_create.add(sid)
        self._life_cycle_set(system, SystemLifeCycle.CREATING)

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

        self._life_cycle_set(system, SystemLifeCycle.DESTROYING)
        self._system_destroy.add(system.id)

        self._event_create(SystemLifeEvent,
                           system_id,
                           SystemLifeCycle.DESTROYING,
                           None, False)

    def _destroy_all(self, tick: SystemTick, time: 'TimeManager') -> None:
        '''
        Set all systems to DESTROYING. Then destroy them.
        '''
        for system in self._schedule:
            self._log_tick(
                "SystemManager._destory_all({tick})",
                tick=tick)

            # Try/catch each system, so they don't kill each other with a
            # single exception.
            try:
                self.destroy(system.id)

                # Only do this if we /really/ want logs.
                if self.debug_flagged(DebugFlag.SYSTEM_DEBUG):
                    self._log_tick("SystemManager._destroy_all({tick}): "
                                   "{system}",
                                   tick=tick,
                                   system=system)

            except VerediError as error:
                # TODO: health thingy
                # Plow on ahead anyways or raise due to debug flags.
                self._error_maybe_raise(
                    error,
                    "SystemManager._destroy_all({tick}): System '{system}' "
                    "threw VerediError type '{error_type}' "
                    "during destroy().",
                    tick=tick,
                    system=str(system),
                    error_type=type(error))

            except Exception as error:
                # TODO: health thingy
                # Plow on ahead anyways or raise due to debug flags.
                self._error_maybe_raise(
                    error,
                    "SystemManager._destroy_all({tick}): System '{system}' "
                    "threw (general) Exception type '{error_type}' "
                    "during destroy().",
                    tick=tick,
                    system=str(system),
                    error_type=type(error))

        self.destruction(time)

    # -------------------------------------------------------------------------
    # Game Loop: Component/System Life Cycle Updates
    # -------------------------------------------------------------------------

    def creation(self,
                 time: 'TimeManager') -> VerediHealth:
        '''
        Runs before the start of the tick/update loop.

        Updates entities in CREATING state to ALIVE state.
        '''

        finished = set()
        for system_id in self._system_create:
            # System should exist in our pool, otherwise we don't
            # care about it...
            system = self.get(system_id)
            if (not system
                    or system._life_cycle != SystemLifeCycle.CREATING):
                self._log_error("Cannot transition {} to created; needs to be "
                                "in CREATING. Removing from creation pool.",
                                system, system._life_cycle)
                finished.add(system_id)
                continue

            try:
                # Bump it to alive now.
                self._life_cycle_set(system, SystemLifeCycle.ALIVE)

            except SystemErrorV as error:
                finished.add(system_id)
                self._log_exception(
                    error,
                    "SystemErrorV in creation() for system_id {}.",
                    system_id)
                # TODO: put this system in... jail or something? Delete?

            finished.add(system_id)
            self._event_create(SystemLifeEvent,
                               system_id,
                               SystemLifeCycle.ALIVE,
                               None, False)

        for system_id in finished:
            self._system_create.remove(system_id)
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
                self._life_cycle_set(system, SystemLifeCycle.DEAD)
                # ...and forget about it.
                self._system.del_by_keys(system_id, type(system))

            except SystemErrorV as error:
                self._log_exception(
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
