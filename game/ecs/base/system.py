# coding: utf-8

'''
Base class for game update loop systems.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Type, Any, Iterable, Set, Dict)
from veredi.base.null import NullNoneOr, Nullable, Null
if TYPE_CHECKING:
    from ..meeting                  import Meeting
    from veredi.base.context        import VerediContext
    from veredi.data.config.context import ConfigContext

    from .component                 import Component
    from .entity                    import Entity


from abc import ABC, abstractmethod
import enum


from veredi.data.config       import registry
from veredi                   import log
from veredi.logger.mixin      import LogMixin
from veredi.base.const        import VerediHealth
from veredi.debug.const       import DebugFlag
from veredi.base.assortments  import DeltaNext

from .identity                import EntityId, SystemId
from .exceptions              import EcsSystemError

from ..const                  import SystemTick, SystemPriority, tick_healthy
from ..exceptions             import TickError

from ..manager                import EcsManager
from ..event                  import EventManager, Event


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# ---
# System's Life Cycle State
# ---

@enum.unique
class SystemLifeCycle(enum.Enum):
    '''
    General state in the life-cycle of a system.
    The usual flow is:
      INVALID    -> CREATING
      CREATING   -> ALIVE
      ALIVE      -> DESTROYING
      DESTROYING -> DEAD

    Sidetracks include:
      1) Structured death:
         ALIVE     -> AUTOPHAGY
         AUTOPHAGY -> DESTROYING
    '''

    INVALID    = 0
    '''
    A bad Life-Cycle to be in. Systems are briefly here before set to CREATING.
    '''

    CREATING   = enum.auto()
    '''
    System is awaiting creation.
    '''

    ALIVE      = enum.auto()
    '''
    System is created and ready to run or already running.
    The majority of a system's life will be here.
    '''

    AUTOPHAGY  = enum.auto()
    '''
    Game has asked for a structured shutdown of systems. This is for systems
    to do clean up and saving and such while remaining responsive.
    '''

    APOPTOSIS = enum.auto()
    '''
    Game has started the shutdown of systems. This is for systems
    to do final clean up. They can now become unresponsive to events, etc.
    '''

    NECROSIS = enum.auto()
    '''
    A very transitive state. Lasts for part of a single tick. Systems will then
    be transitioned to DESTROYING and then finally DEAD.
    '''

    DESTROYING = enum.auto()
    '''
    Systems are no longer considered ALIVE, but are awaiting destruction.
    '''

    DEAD       = enum.auto()
    '''
    Systems have been destroyed.
    '''

    def __str__(self):
        return (
            f"{self.__class__.__name__}.{self._name_}"
        )

    def __repr__(self):
        return (
            f"SLC.{self._name_}"
        )


# ---
# Helper class to hold onto stuff we use and pass into created Systems.
# ---

# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class System(LogMixin, ABC):

    # -------------------------------------------------------------------------
    # Class Methods
    # -------------------------------------------------------------------------

    @classmethod
    def dependencies(klass: 'System') -> Optional[Dict[Type['System'], str]]:
        '''
        System's dependencies in a System class/type to dotted string
        dictionary.

        Required dependencies will be checked for by type.
          - If a system of that type already exists, good.
          - If not, the dotted string will be used to try to create one.
        '''
        return None

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self):
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        self._life_cycle: SystemLifeCycle = SystemLifeCycle.INVALID
        '''
        Our current life cycle.
        '''

        self._system_id: SystemId = None
        '''
        Our ID. Set by SystemManager. Do not touch!
        '''

        self._components_req: Optional[Set[Type['Component']]] = None
        '''
        The components we /absolutely require/ to function.
        '''

        self._components_req_all: bool = True
        '''
        True: self._components_req is a Union of all components required.

        False: Any one of the components in self._components_req is enough for
        us to do something with the entity for our tick.
        '''

        self._ticks: Optional[SystemTick] = None
        '''
        The ticks we desire to run in.

        Systems will always get the TICKS_BIRTH and TICKS_DEATH ticks. The
        default _cycle_<tick> and _update_<tick> for those ticks should be
        acceptable if the system doesn't care.
        '''

        self._manager: 'Meeting' = None
        '''
        A link to the engine's Meeting of ECS Managers.
        '''

        self._component_type: Type['Component'] = None
        '''
        This system's component type. Used in get().
        For systems that aren't tied to a specifc component, leave as 'None'.
        '''

        # ---
        # Logging
        # ---
        # We're a LogMixin. Use self._log_<level>(), self._log_group(), etc.

        # ---
        # Subscriptions
        # ---
        self._subscribed: bool = False
        '''
        Set to true once you've sent off any subscription stuff to EventManager
        during SystemTick.MITOSIS.
        '''

        # ---
        # Self-Health Set Up
        # ---
        # If we get in a not-healthy state, we'll start just dropping inputs.
        self._health: VerediHealth = VerediHealth.HEALTHY
        '''
        Overall health of the system.
        '''

        self._required_managers: Optional[Set[Type[EcsManager]]] = None
        '''
        All ECS Managers that we /require/ in order to function.
        '''

        # Most systems have these, so we'll just define 'em in the base.
        self._health_meter_event:   Optional[int] = None
        '''
        Store timing information for our timed/metered 'system isn't healthy'
        messages that fire off during event things.
        '''

        self._health_meter_update:  Optional[int] = None
        '''
        Stores timing information for our timed/metered 'system isn't healthy'
        messages that fire off during system tick things.
        '''

        self._reduced_tick_rate: Optional[Dict[SystemTick, DeltaNext]] = {}
        '''
        If systems want to only do some tick (or part of a tick), they can put
        the tick and how often they want to do it here.

        e.g. if we want every 10th SystemTick.CREATION for checking that some
        data is in sync, set:
          TimeManager.set_reduced_tick_rate(SystemTick.CREATION, 10)
        '''

    def __init__(self,
                 context:  Optional['VerediContext'],
                 sid:      SystemId,
                 managers: 'Meeting') -> None:
        self._define_vars()

        # ---
        # Set our variables.
        # ---
        self._system_id = sid
        self._manager = managers

        # ---
        # Logger!
        # ---
        # Set up before _configure() so we have self._log_*() working ASAP.
        self._log_config(self.dotted())

        # ---
        # Final set up/configuration from context/config and
        # system-specific stuff.
        # ---
        self._configure(context)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def id(self) -> SystemId:
        return SystemId.INVALID if self._system_id is None else self._system_id

    @classmethod
    @abstractmethod
    def dotted(klass: 'System') -> str:
        """
        The dotted name this system has. If the system uses '@register', you
        still have to implement dotted, but you get klass._DOTTED for free
        (the @register decorator sets it).

        E.g.
          @register('veredi', 'jeff', 'system')
        would be:
          klass._DOTTED = 'veredi.jeff.system'

        So just implement like this:

            @classmethod
            def dotted(klass: 'JeffSystem') -> str:
                '''
                Returns our dotted name.
                '''
                # klass._DOTTED magically provided by @register
                return klass._DOTTED
        """
        raise NotImplementedError(f"{klass.__name__}.dotted() "
                                  "is not implemented in base class. "
                                  "Subclasses should get it defined via "
                                  "@register, or else define it themselves.")

    @property
    def enabled(self) -> bool:
        return self._life_cycle == SystemLifeCycle.ALIVE

    # -------------------------------------------------------------------------
    # Life Cycle
    # -------------------------------------------------------------------------

    @property
    def life_cycle(self) -> SystemLifeCycle:
        return self._life_cycle

    def _life_cycled(self, new_state: SystemLifeCycle) -> VerediHealth:
        '''
        SystemManager calls this to update life cycle. Will be called on:
          - INVALID    -> CREATING   : During SystemManager.create()
          - CREATING   -> ALIVE      : During SystemManager.creation()
          - ALIVE?     -> AUTOPHAGY  : During SystemManager.autophagy()
          - AOPTOSIS   -> APOPTOSIS  : During SystemManager.apoptosis()
          - APOPTOSIS  -> NECROSIS   : During SystemManager.necrosis()
          - NECROSIS   -> DESTROYING : During SystemManager._update_necrosis()
          - DESTROYING -> DEAD       : During SystemManager.destruction()
        '''
        # Sanity.
        if new_state == self._life_cycle:
            self._log_warning("Already in {}.", new_state)
            return self.health

        # ------------------------------
        # Do transition.
        # ------------------------------
        # Bad transition?
        if new_state == SystemLifeCycle.INVALID:
            msg = (f"{str(self)}: {self._life_cycle}->{new_state} "
                   "is an invalid life-cycle to transition to.")
            error = ValueError(msg,
                               self._life_cycle,
                               new_state)
            raise self._log_exception(error, msg)

        # Valid life-cycles; call specific cycle function.
        elif new_state == SystemLifeCycle.CREATING:
            self._health = self._health.update(
                self._cycle_creating())

        elif new_state == SystemLifeCycle.ALIVE:
            self._health = self._health.update(
                self._cycle_alive())

        elif new_state == SystemLifeCycle.AUTOPHAGY:
            self._health = self._health.update(
                self._cycle_autophagy())

        elif new_state == SystemLifeCycle.APOPTOSIS:
            self._health = self._health.update(
                self._cycle_apoptosis())

        elif new_state == SystemLifeCycle.NECROSIS:
            self._health = self._health.update(
                self._cycle_necrosis())

        elif new_state == SystemLifeCycle.DESTROYING:
            self._health = self._health.update(
                self._cycle_destroying())

        elif new_state == SystemLifeCycle.DEAD:
            self._health = self._health.update(
                self._cycle_dead())

        # Unknown transition? Should add it to valids or bad, probably.
        else:
            msg = (f"{str(self)}: {self._life_cycle}->{new_state} "
                   "is an unknown life-cycle to transition to.")
            error = ValueError(msg,
                               self._life_cycle,
                               new_state)
            raise self._log_exception(error, msg)

        return self._health

    def _cycle_creating(self) -> VerediHealth:
        '''
        System is being cycled into creating state from current state.
        Current state is still set in self._life_cycle.
        '''
        self._life_cycle = SystemLifeCycle.CREATING
        self._health = self._health.update(VerediHealth.HEALTHY)
        return self.health

    def _cycle_alive(self) -> VerediHealth:
        '''
        System is being cycled into alive state from current state.
        Current state is still set in self._life_cycle.
        '''
        self._life_cycle = SystemLifeCycle.ALIVE
        self._health = self._health.update(VerediHealth.HEALTHY)
        return self.health

    def _cycle_autophagy(self) -> VerediHealth:
        '''
        System is being cycled into autophagy state from current state.
        Current state is still set in self._life_cycle.
        '''
        self._life_cycle = SystemLifeCycle.AUTOPHAGY
        # Default to just being done with autophagy?
        self._health = self._health.update(VerediHealth.AUTOPHAGY_SUCCESSFUL)

        return self.health

    def _cycle_apoptosis(self) -> VerediHealth:
        '''
        System is being cycled into apoptosis state from current state.
        Current state is still set in self._life_cycle.
        '''
        self._life_cycle = SystemLifeCycle.APOPTOSIS
        # Default to just being done with apoptosis?
        self._health = self._health.update(VerediHealth.APOPTOSIS_DONE)

        return self.health

    def _cycle_necrosis(self) -> VerediHealth:
        '''
        System is being cycled into necrosis state from current state.
        Current state is still set in self._life_cycle.
        '''
        self._life_cycle = SystemLifeCycle.NECROSIS
        # Set our health to NECROSIS so destroying/dead know we're ending the
        # expected way.
        self._health = self._health.update(VerediHealth.NECROSIS)
        return self.health

    def _cycle_destroying(self) -> VerediHealth:
        '''
        System is being cycled into destroying state from current state.
        Current state is still set in self._life_cycle.
        '''
        self._life_cycle = SystemLifeCycle.DESTROYING
        # If our health is NECROSIS, ok. We expect to be destroying/dead then.
        # Otherwise set ourselves to the bad dying.
        if self._health != VerediHealth.NECROSIS:
            self._health = self._health.update(VerediHealth.DYING)
        return self.health

    def _cycle_dead(self) -> VerediHealth:
        '''
        System is being cycled into dead state from current state.
        Current state is still set in self._life_cycle.
        '''
        self._life_cycle = SystemLifeCycle.DEAD
        # If our health is NECROSIS, ok. We expect to be destroying/dead then.
        # Otherwise set ourselves to the bad dying.
        if self._health != VerediHealth.NECROSIS:
            self._health = self._health.update(VerediHealth.FATAL)

        return self.health

    # -------------------------------------------------------------------------
    # System Set Up
    # -------------------------------------------------------------------------

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''
        Allows systems to grab, from the context/config, anything that
        they need to set up themselves.
        '''
        ...

    def priority(self) -> Union[SystemPriority, int]:
        '''
        Returns a SystemPriority (or int) for when, relative to other systems,
        this should run. Highest priority goes firstest.
        '''
        # TODO: flow control - systems have priorities and can depend on each
        # other, so that a topological order for their execution can be
        # established.

        # So allow either static priority level, or some sort of...
        # SystemFlow.Before('class name')
        # SystemFlow.After('class name')
        return SystemPriority.LOW

    @staticmethod
    def sort_key(system: 'System') -> Union[SystemPriority, int]:
        return system.priority()

    # -------------------------------------------------------------------------
    # Getter for Entity's/System's Component
    # -------------------------------------------------------------------------

    def get(self, entity_id: EntityId) -> Nullable['Component']:
        '''
        Try to get entity. Try to get system's only/most important component
        type off entity.

        Return component or Null().
        '''
        if not self._component_type:
            return Null()

        entity = self._manager.entity.get(entity_id)
        component = entity.get(self._component_type)
        return component

    # -------------------------------------------------------------------------
    # System Death
    # -------------------------------------------------------------------------

    # TODO [2020-10-08]: Use this timeout_desired() in TICKS_BIRTH,
    # TICKS_DEATH to see if there's a smaller max timeout engine/sysmgr can use.
    def timeout_desired(self, cycle: SystemTick) -> Optional[float]:
        '''
        If a system wants some minimum time, they can override this function.
        This is only a request, though. The SystemManager or Engine may not
        grant it.
        '''
        return None

    # -------------------------------------------------------------------------
    # System Health
    # -------------------------------------------------------------------------

    @property
    def health(self) -> VerediHealth:
        return self._health

    @health.setter
    def health(self, update_value: VerediHealth) -> None:
        '''
        Sets self._health to the worst of current value and `update_value`.
        '''
        self._health = self._health.update(update_value)

    def _healthy(self, tick: SystemTick) -> bool:
        '''
        Are we in a healthy/runnable state?

        For ticks at end of game (TICKS_DEATH), this is just any 'runnable'
        health.

        For the rest of the ticks (namely TICKS_LIFE), this is only the 'best'
        of health.
        '''
        return tick_healthy(tick, self._health)

    def _health_check(self,
                      tick: SystemTick,
                      current_health: VerediHealth = VerediHealth.HEALTHY
                      ) -> VerediHealth:
        '''
        Tracks our system health. Returns either `current_health` or something
        worse from what all we track.

        Checks for all required managers via Meeting.healthy().

        Checks for existance of all systems we depend on (according to
        self.dependencies()). If something doesn't exist, degrade health to
        UNHEALTHY. Only checks for existance of the dependency - not health.
        '''
        # ---
        # Health Summary: Managers
        # ---
        manager_health = self._manager.healthy(self._required_managers)
        if not manager_health.in_best_health:
            self._health = self._health.update(manager_health)
            # We rely on those managers to function, so we're bad if
            # they don't exist.
            return self.health

        # ---
        # Health Summary: Systems
        # ---
        dependency_health = VerediHealth.HEALTHY
        dependencies = self.dependencies() or {}
        for sys_type in dependencies:
            system = self._manager.system.get(sys_type)
            if not system:
                # Log and degrade our system dependency health.
                self._log_warning("{} cannot find its requried system: {}",
                                  self.__class__.__name__,
                                  sys_type)
                dependency_health = dependency_health.update(
                    VerediHealth.UNHEALTHY)

        # ---
        # Health Summary: Summary
        # ---
        # Set our state to whatever's worse and return that.
        # TODO [2020-06-04]: Eventually maybe a gradient of health so one
        # bad thing doesn't knock us offline?
        self._health = self._health.update(current_health,
                                           manager_health,
                                           dependency_health)
        return self.health

    def _health_log(self,
                    log_meter: int,
                    log_level: log.Level,
                    msg:       str,
                    *args:     Any,
                    **kwargs:  Any):
        '''
        Do a metered health log if meter allows. Will log out at `log_level`.

        WARNING is a good default. Not using an optional param so args/kwargs
        are more explicitly separated.
        '''
        output_log, maybe_updated_meter = self._manager.time.metered(log_meter)
        if output_log:
            kwargs = self._log_stack(**kwargs)
            self._log_at_level(
                log_level,
                f"HEALTH({str(self.health)}): " + msg,
                args, kwargs)
        return maybe_updated_meter

    def _health_ok_msg(self,
                       message:  str,
                       *args:    Any,
                       context:  NullNoneOr['VerediContext'],
                       **kwargs: Any) -> bool:
        '''Check health, log if needed, and return True if able to proceed.'''
        tick = self._manager.time.engine_tick_current
        if not self._healthy(tick):
            kwargs = self._log_stack(**kwargs)
            self._health_meter_event = self._health_log(
                self._health_meter_event,
                log.Level.WARNING,
                message,
                *args,
                context=context,
                **kwargs)
            return False
        return True

    def _health_ok_event(self,
                         event: 'Event') -> bool:
        '''Check health, log if needed, and return True if able to proceed.'''
        tick = self._manager.time.engine_tick_current
        if not self._healthy(tick):
            msg = ("Dropping event {} - our system health "
                   "isn't good enough to process.")
            kwargs = self._log_stack()
            self._health_meter_event = self._health_log(
                self._health_meter_event,
                log.Level.WARNING,
                msg,
                event,
                context=event.context,
                **kwargs)
            return False
        return True

    def _health_ok_tick(self,
                        tick: 'SystemTick',
                        context:  NullNoneOr['VerediContext'] = None) -> bool:
        '''Check health, log if needed, and return True if able to proceed.'''
        if not self._healthy(tick):
            msg = ("Skipping tick {} - our system health "
                   "isn't good enough to process.")
            kwargs = self._log_stack()
            self._health_meter_update = self._health_log(
                self._health_meter_update,
                log.Level.WARNING,
                msg,
                tick,
                context=context,
                **kwargs)
            return False
        return True

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def _subscribe(self) -> VerediHealth:
        '''
        Implement this to subscribe to events/etc. Will only be called
        (successfully) once in MITOSIS tick from self.subscribe().

        Return HEALTHY if everything went well.
        Return PENDING if you want to be called again.
        Return something else if you want to die.
        '''
        return VerediHealth.HEALTHY

    def subscribe(self, event_manager: EventManager) -> VerediHealth:
        '''
        Idempotently subscribe to any life-long event subscriptions here. Can
        hold on to event_manager if need to sub/unsub more dynamically.
        '''
        # ---
        # MUST BE IDEMPOTENT!
        # ---
        # That is... This must be callable multiple times with it doing the
        # correct thing once and only once.

        # Prevent reregistration.
        if self._subscribed:
            return VerediHealth.HEALTHY

        # Sanity checks...
        if (event_manager
                and self._manager and self._manager.event
                and self._manager.event is not event_manager):
            msg = ("subscribe() received an EventManager which "
                   "is different from its saved EventManager "
                   "from initialization. ours: {}, supplied: {}")
            msg = msg.format(self._manager.event, event_manager)
            error = EcsSystemError(msg,
                                   None,
                                   context=None)
            raise self._log_exception(error, msg)

        if (self._required_managers and EventManager in self._required_managers
                and not self._manager.event):
            msg = ("System has no event manager to subscribe to "
                   "but requires one.")
            error = EcsSystemError(msg,
                                   None,
                                   context=None)
            raise self._log_exception(error, msg)

        # Have our sub-class do whatever it wants this one time.
        # Or, you know, more than once... depending on the health returned.
        subscribe_health = self._subscribe()
        if subscribe_health == VerediHealth.HEALTHY:
            self._subscribed = True

        self.health = subscribe_health
        return subscribe_health

    def _event_create(self,
                      event_class:                Type[Event],
                      owner_id:                   int,
                      type:                       Union[int, enum.Enum],
                      context:                    Optional['VerediContext'],
                      requires_immediate_publish: bool = False) -> None:
        '''
        Calls our EventManager.create(), if we have an EventManager.
        '''
        if not self._manager.event:
            return
        self._manager.event.create(event_class,
                                   owner_id,
                                   type,
                                   context,
                                   requires_immediate_publish)

    def _event_notify(self,
                      event:                      'Event',
                      requires_immediate_publish: bool = False) -> None:
        '''
        Calls our EventManager.notify(), if we have an EventManager.
        '''
        if not self._manager.event:
            return
        self._manager.event.notify(event,
                                   requires_immediate_publish)

    # -------------------------------------------------------------------------
    # Game Update Loop/Tick Functions
    # -------------------------------------------------------------------------

    def wants_update_tick(self,
                          tick: SystemTick) -> bool:
        '''
        Returns a boolean for whether this system wants to run during this tick
        update function.

        Default is:
          Always want: AUTOPHAGY, APOPTOSIS, NECROSIS
            - These update functions work by default so no change needed if you
              don't actually need them.
          Optional: The rest of the ticks.
            - Checks if self._ticks has `tick`.
        '''
        if (tick == SystemTick.AUTOPHAGY
                or tick == SystemTick.APOPTOSIS
                or tick == SystemTick.NECROSIS):
            return True

        return self._ticks is not None and self._ticks.has(tick)

    def required(self) -> Optional[Iterable['Component']]:
        '''
        Returns the Component types this system /requires/ in order to function
        on an entity.

        e.g. Perhaps a Combat system /requires/ Health and Defense components,
        and uses others like Position, Attack... This function should only
        return Health and Defense.
        '''
        return self._components_req

    def require_all(self) -> bool:
        '''
        Returns True if `required()` is an 'AND'
          (i.e. "require all these components").

        Returns False if `required()` is an 'OR'
          (i.e. "require any one of these components").
        '''
        return self._components_req_all

    def _wanted_entities(self, tick: SystemTick) -> VerediHealth:
        '''
        Loop over entities that have self.required().
        '''
        req_fn = (self._manager.entity.each_with_all
                  if self.require_all() else
                  self._manager.entity.each_with_any)
        for entity in req_fn(self.required()):
            yield entity

    def update_tick(self,
                    tick: SystemTick) -> VerediHealth:
        '''
        Calls the correct update function for the tick state.

        Returns VerediHealth value.
        '''
        if tick is SystemTick.SYNTHESIS:
            return self._update_synthesis()

        elif tick is SystemTick.MITOSIS:
            return self._update_mitosis()

        elif tick is SystemTick.TIME:
            return self._update_time()

        elif tick is SystemTick.CREATION:
            return self._update_creation()

        elif tick is SystemTick.PRE:
            return self._update_pre()

        elif tick is SystemTick.STANDARD:
            return self._update()

        elif tick is SystemTick.POST:
            return self._update_post()

        elif tick is SystemTick.DESTRUCTION:
            return self._update_destruction()

        elif tick is SystemTick.AUTOPHAGY:
            return self._update_autophagy()

        elif tick is SystemTick.APOPTOSIS:
            return self._update_apoptosis()

        elif tick is SystemTick.NECROSIS:
            return self._update_necrosis()

        else:
            # This, too, should be treated as a VerediHealth.FATAL...
            raise TickError(
                "{} does not have an update_tick handler for {}.",
                self.__class__.__name__, tick)

    def _update_synthesis(self) -> VerediHealth:
        '''
        First in set-up loop. Systems should use this to load and initialize
        stuff that takes multiple cycles or is otherwise unwieldy
        during __init__.
        '''
        default_return = VerediHealth.FATAL
        self.health = default_return
        return self.health

    def _update_intra_sys(self) -> VerediHealth:
        '''
        Part of the set-up ticks. Systems should use this for any
        system-to-system setup. For examples:
          - System.subscribe() gets called here.
          - Command registration happens here.
        '''
        default_return = VerediHealth.FATAL
        self.health = default_return
        return self.health

    def _update_time(self) -> VerediHealth:
        '''
        First in Game update loop. Systems should use this rarely as the game
        time clock itself updates in this part of the loop.
        '''
        default_return = VerediHealth.FATAL
        self.health = default_return
        return self.health

    def _update_creation(self) -> VerediHealth:
        '''
        Before Standard upate. Creation part of life cycles managed here.
        '''
        default_return = VerediHealth.FATAL
        self.health = default_return
        return self.health

    def _update_pre(self) -> VerediHealth:
        '''
        Pre-update. For any systems that need to squeeze in something just
        before actual tick.
        '''
        default_return = VerediHealth.FATAL
        self.health = default_return
        return self.health

    def _update(self) -> VerediHealth:
        '''
        Normal/Standard upate. Basically everything should happen here.
        '''
        default_return = VerediHealth.FATAL
        self.health = default_return
        return self.health

    def _update_post(self) -> VerediHealth:
        '''
        Post-update. For any systems that need to squeeze in something just
        after actual tick.
        '''
        default_return = VerediHealth.FATAL
        self.health = default_return
        return self.health

    def _update_destruction(self) -> VerediHealth:
        '''
        Final game-loop update. Death/deletion part of life cycles
        managed here.
        '''
        default_return = VerediHealth.FATAL
        self.health = default_return
        return self.health

    def _update_autophagy(self) -> VerediHealth:
        '''
        Structured death phase. System should be responsive until it the next
        phase, but should be doing stuff for shutting down, like saving off
        data, etc.

        Default is "do nothing and return done."
        '''
        default_return = VerediHealth.AUTOPHAGY_SUCCESSFUL
        self.health = default_return
        return self.health

    def _update_apoptosis(self) -> VerediHealth:
        '''
        "Die now" death phase. System may now go unresponsive to events,
        function calls, etc. Systems cannot expect to have done a successful
        autophagy.

        Default is "do nothing and return done."
        '''
        default_return = VerediHealth.APOPTOSIS_DONE
        self.health = default_return
        return self.health

    def _update_necrosis(self) -> VerediHealth:
        '''
        Final game update. This is only called once. Systems should most likely
        have nothing to do here.

        Default is "do nothing and return that we're dead now."
        '''
        default_return = VerediHealth.NECROSIS
        self.health = default_return
        return self.health

    # -------------------------------------------------------------------------
    # Logging and String
    # -------------------------------------------------------------------------

    def _should_debug(self):
        '''
        Returns true if log.Level.DEBUG is outputting and if our DebugFlags
        want us to output too.
        '''
        return (log.will_output(log.Level.DEBUG)
                and self._manager.flagged(DebugFlag.SYSTEM_DEBUG))

    def __str__(self):
        return (
            f"{self.__class__.__name__}"
            f"[{self.id}, "
            f"{str(self.life_cycle)}], "
            f"{str(self.health)}]"
        )

    def __repr__(self):
        return (
            '<v.sys:'
            f"{self.__class__.__name__}"
            f"[{self.id}, "
            f"{repr(self.life_cycle)}], "
            f"{repr(self.health)}]>"
        )


# -----------------------------------------------------------------------------
# Tell registry to leave my children alone for @property dotted() puropses.
# -----------------------------------------------------------------------------
registry.ignore(System)
