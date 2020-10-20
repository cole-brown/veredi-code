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
    from decimal                    import Decimal
    from ..meeting                  import Meeting
    from veredi.base.context        import VerediContext
    from veredi.data.config.context import ConfigContext

    from .component                 import Component
    from .entity                    import Entity


from abc import ABC, abstractmethod
import enum


from veredi.data.config       import registry
from veredi.logger            import log
from veredi.logger.lumberjack import Lumberjack
from veredi.base.const        import VerediHealth
from veredi.debug.const       import DebugFlag
from veredi.base.assortments  import DeltaNext

from .identity                import EntityId, SystemId
from .exceptions              import SystemErrorV

from ..const                  import SystemTick, SystemPriority
from ..exceptions             import TickError

from ..manager                import EcsManager
from ..time                   import TimeManager, MonotonicTimer
from ..event                  import EventManager, Event
from ..component              import ComponentManager
from ..entity                 import EntityManager


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
         ALIVE     -> APOPTOSIS
         APOPTOSIS -> DESTROYING
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

    APOPTOSIS  = enum.auto()
    '''
    Game has asked for a structured shutdown of systems. This is for systems
    to do clean up and saving and such while remaining responsive.
    '''

    APOCALYPSE = enum.auto()
    '''
    Game has started the shutdown of systems. This is for systems
    to do final clean up. They can now become unresponsive to events, etc.
    '''

    THE_END = enum.auto()
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

class System(ABC):

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

        Systems will always get the TICKS_START and TICKS_END ticks. The
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
        self._log: Lumberjack = None
        '''
        A logger specifically for this system. Logger name is `self.dotted`.
        '''

        # ---
        # Subscriptions
        # ---
        self._subscribed: bool = False
        '''
        Set to true once you've sent off any subscription stuff to EventManager
        during SystemTick.INTRA_SYSTEM.
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
        self._health_meter_event:   Optional['Decimal'] = None
        '''
        Store timing information for our timed/metered 'system isn't healthy'
        messages that fire off during event things.
        '''

        self._health_meter_update:  Optional['Decimal'] = None
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
          self._set_reduced_tick_rate(SystemTick.CREATION, 10)
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
        # Final set up/configuration from context/config and
        # system-specific stuff.
        # ---
        self._configure(context)

        # ---
        # Logger!
        # ---
        # TODO: go through all systems and make sure they use this instead of
        # log.py directly.
        self._log = Lumberjack(self.dotted)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def id(self) -> SystemId:
        return SystemId.INVALID if self._system_id is None else self._system_id

    # TODO: rename this dotted!
    @property
    @abstractmethod
    def dotted(self) -> str:
        '''
        The dotted name this system has. If the system uses '@register', you
        still have to implement dotted, but you get self._DOTTED for free
        (the @register decorator sets it).

        E.g.
          @register('veredi', 'jeff', 'system')
        would be:
          self._DOTTED = 'veredi.jeff.system'

        So just implement like this:

            @property
            def dotted(self) -> str:
                # self._DOTTED magically provided by @register
                return self._DOTTED
        '''
        raise NotImplementedError

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
          - ALIVE?     -> APOPTOSIS  : During SystemManager.apoptosis()
          - AOPTOSIS   -> APOCALYPSE : During SystemManager.apocalypse()
          - APOCALYPSE -> THE_END    : During SystemManager.the_end()
          - THE_END    -> DESTROYING : During SystemManager._update_the_end()
          - DESTROYING -> DEAD       : During SystemManager.destruction()
        '''
        # Sanity.
        if new_state == self._life_cycle:
            self._log.warning("Already in {}.", new_state)
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
            raise self._log.exception(error, msg)

        # Valid life-cycles; call specific cycle function.
        elif new_state == SystemLifeCycle.CREATING:
            self._health = self._health.update(
                self._cycle_creating())

        elif new_state == SystemLifeCycle.ALIVE:
            self._health = self._health.update(
                self._cycle_alive())

        elif new_state == SystemLifeCycle.APOPTOSIS:
            self._health = self._health.update(
                self._cycle_apoptosis())

        elif new_state == SystemLifeCycle.APOCALYPSE:
            self._health = self._health.update(
                self._cycle_apocalypse())

        elif new_state == SystemLifeCycle.THE_END:
            self._health = self._health.update(
                self._cycle_the_end())

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
            raise self._log.exception(error, msg)

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

    def _cycle_apoptosis(self) -> VerediHealth:
        '''
        System is being cycled into apoptosis state from current state.
        Current state is still set in self._life_cycle.
        '''
        self._life_cycle = SystemLifeCycle.APOPTOSIS
        # Default to just being done with apoptosis?
        self._health = self._health.update(VerediHealth.APOPTOSIS_SUCCESSFUL)

        return self.health

    def _cycle_apocalypse(self) -> VerediHealth:
        '''
        System is being cycled into apocalypse state from current state.
        Current state is still set in self._life_cycle.
        '''
        self._life_cycle = SystemLifeCycle.APOCALYPSE
        # Default to just being done with apocalypse?
        self._health = self._health.update(VerediHealth.APOCALYPSE_DONE)

        return self.health

    def _cycle_the_end(self) -> VerediHealth:
        '''
        System is being cycled into the_end state from current state.
        Current state is still set in self._life_cycle.
        '''
        self._life_cycle = SystemLifeCycle.THE_END
        # Set our health to THE_END so destroying/dead know we're ending the
        # expected way.
        self._health = self._health.update(VerediHealth.THE_END)
        return self.health

    def _cycle_destroying(self) -> VerediHealth:
        '''
        System is being cycled into destroying state from current state.
        Current state is still set in self._life_cycle.
        '''
        self._life_cycle = SystemLifeCycle.DESTROYING
        # If our health is THE_END, ok. We expect to be destroying/dead then.
        # Otherwise set ourselves to the bad dying.
        if self._health != VerediHealth.THE_END:
            self._health = self._health.update(VerediHealth.DYING)
        return self.health

    def _cycle_dead(self) -> VerediHealth:
        '''
        System is being cycled into dead state from current state.
        Current state is still set in self._life_cycle.
        '''
        self._life_cycle = SystemLifeCycle.DEAD
        # If our health is THE_END, ok. We expect to be destroying/dead then.
        # Otherwise set ourselves to the bad dying.
        if self._health != VerediHealth.THE_END:
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

    def _log_get_entity(self,
                        entity_id: 'EntityId',
                        event:     NullNoneOr['Event']         = None,
                        context:   NullNoneOr['VerediContext'] = None,
                        preface:   Optional[str]               = None
                        ) -> Nullable['Entity']:
        '''
        Checks to see if entity exists.

        Returns the entity if so.
        Logs at INFO level and returns Null if not.
        '''
        entity = self._manager.entity.get(entity_id)
        if not entity:
            # Entity disappeared, and that's ok.
            preface = preface or ''
            if event:
                preface = preface or f"Dropping event {event} - "
                if not context:
                    context = event.context
            # Entity disappeared, and that's ok.
            self._log.info("{}No entity for its id: {}",
                           preface, entity_id,
                           context=context)
            # TODO [2020-06-04]: a health thing? e.g.
            # self._health_update(EntityDNE)
            return Null()

        return entity

    def _log_get_component(self,
                           entity_id: 'EntityId',
                           comp_type: Type['Component'],
                           event:     NullNoneOr['Event']         = None,
                           context:   NullNoneOr['VerediContext'] = None,
                           preface:   Optional[str]               = None
                           ) -> Nullable['Component']:
        '''
        Checks to see if entity exists and has a component of the correct type.

        Automatically creates preface for events: 'Dropping event {event} - '
        But if `preface` is not None, it will use that. So for commands, e.g.:
          'Dropping command {command_name} - ' could be a good preface.

        Returns the entity's component if so.
        Logs at INFO level and returns Null if not.
        '''
        # entity or Null(), so...
        entity = self._log_get_entity(entity_id)

        component = entity.get(comp_type)
        if not component:
            preface = preface or ''
            if event:
                preface = preface or f"Dropping event {event} - "
                if not context:
                    context = event.context
            # Component disappeared, and that's ok.
            self._log.info("{}No '{}' on entity: {}",
                           preface,
                           component.__class__.__name__,
                           entity,
                           context=context)
            # TODO [2020-06-04]: a health thing? e.g.
            # self._health_update(ComponentDNE)
            return Null()

        return component

    def _log_get_both(self,
                      entity_id: 'EntityId',
                      comp_type: Type['Component'],
                      event:     NullNoneOr['Event']         = None,
                      context:   NullNoneOr['VerediContext'] = None,
                      preface:   Optional[str]               = None) -> bool:
        '''
        Checks to see if entity exists and has a component of the correct type.

        Returns a tuple of (entity, component) if so.
        Logs at INFO level and returns Null() for non-existant pieces, so:
            (Null(), Null())
          or
            (entity, Null())
        '''
        # Just `get` entity... `_log_get_component` will `_log_get_entity`, and
        # that will give us both logs if needed.
        entity = self._manager.entity.get(entity_id)
        component = self._log_get_component(entity_id,
                                            comp_type,
                                            event=event,
                                            preface=preface)
        # entity or Null(), and
        # component or Null(), so...
        return (entity, component)

    # -------------------------------------------------------------------------
    # System Death
    # -------------------------------------------------------------------------

    # TODO [2020-10-08]: Use this timeout_desired() in TICKS_START,
    # TICKS_END to see if there's a smaller max timeout engine/sysmgr can use.
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

        For ticks at end of game (TICKS_END), this is just any 'runnable'
        health.

        For the rest of the ticks (namely TICKS_RUN), this is only the 'best'
        of health.
        '''
        if SystemTick.TICKS_END.has(tick):
            return self._health.in_runnable_health
        return self._health.in_best_health

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
                self._log.warning("{} cannot find its requried system: {}",
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
                    log_meter: 'Decimal',
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
            log.incr_stack_level(kwargs)
            self._log.at_level(
                log_level,
                "HEALTH({}): Skipping ticks - our system health "
                "isn't good enough to process. args: {}, kwargs: {}",
                self.health, args, kwargs)
        return maybe_updated_meter

    def _health_ok_msg(self,
                       message:  str,
                       *args:    Any,
                       context:  NullNoneOr['VerediContext'],
                       **kwargs: Any) -> bool:
        '''Check health, log if needed, and return True if able to proceed.'''
        tick = self._manager.time.engine_tick_current
        if not self._healthy(tick):
            kwargs = log.incr_stack_level(None)
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
            kwargs = log.incr_stack_level(None)
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
            kwargs = log.incr_stack_level(None)
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
        (successfully) once in INTRA_SYSTEM tick from self.subscribe().

        Return HEALTHY if everything went well.
        Return PENDING if you want to be called again.
        Return something else if you want to die.
        '''
        return VerediHealth.HEALTHY

    def subscribe(self, event_manager: EventManager) -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
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
            error = SystemErrorV(msg,
                                 None,
                                 context=None,
                                 associated=None)
            raise self._log.exception(error, msg)

        if (self._required_managers and EventManager in self._required_managers
                and not self._manager.event):
            msg = ("System has no event manager to subscribe to "
                   "but requires one.")
            error = SystemErrorV(msg,
                                 None,
                                 context=None,
                                 associated=None)
            raise self._log.exception(error, msg)

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

    def _set_reduced_tick_rate(self, tick: SystemTick, rate: int) -> None:
        '''
        Set an entry into our reduced tick rate dict. This does nothing on its
        own. System must use self._is_reduced_tick() to check for if/when they
        want to do their reduced processing.
        '''
        self._reduced_tick_rate[tick] = DeltaNext(rate,
                                                  self._manager.time.tick_num)

    def _is_reduced_tick(self, tick: SystemTick) -> bool:
        '''
        Checks to see if this tick is the reduced-tick-rate tick.
        '''
        red_tick = self._reduced_tick_rate.get(tick, None)
        if not red_tick:
            return False

        if self._manager.time.tick_num >= red_tick.next:
            # Update our DeltaNext to the next reduced tick number.
            red_tick.cycle(self._manager.time.tick_num)
            return True

        return False

    def wants_update_tick(self,
                          tick: SystemTick,
                          time_mgr: 'TimeManager') -> bool:
        '''
        Returns a boolean for whether this system wants to run during this tick
        update function.

        Default is:
          Always want: APOPTOSIS, APOCALYPSE, THE_END
            - These update functions work by default so no change needed if you
              don't actually need them.
          Optional: The rest of the ticks.
            - Checks if self._ticks has `tick`.
        '''
        if (tick == SystemTick.APOPTOSIS
                or tick == SystemTick.APOCALYPSE
                or tick == SystemTick.THE_END):
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

    def _wanted_entities(self,
                         tick:          SystemTick,
                         time_mgr:      'TimeManager',
                         component_mgr: 'ComponentManager',
                         entity_mgr:    'EntityManager') -> VerediHealth:
        '''
        Loop over entities that have self.required().
        '''
        req_fn = (entity_mgr.each_with_all
                  if self.require_all() else
                  entity_mgr.each_with_any)
        for entity in req_fn(self.required()):
            yield entity

    def update_tick(self,
                    tick:          SystemTick,
                    time_mgr:      'TimeManager',
                    component_mgr: 'ComponentManager',
                    entity_mgr:    'EntityManager') -> VerediHealth:
        '''
        Calls the correct update function for the tick state.

        Returns VerediHealth value.
        '''
        if tick is SystemTick.GENESIS:
            return self._update_genesis(time_mgr, component_mgr, entity_mgr)

        elif tick is SystemTick.INTRA_SYSTEM:
            return self._update_intra_system(time_mgr.timer)

        elif tick is SystemTick.TIME:
            return self._update_time(time_mgr, component_mgr, entity_mgr)

        elif tick is SystemTick.CREATION:
            return self._update_creation(time_mgr, component_mgr, entity_mgr)

        elif tick is SystemTick.PRE:
            return self._update_pre(time_mgr, component_mgr, entity_mgr)

        elif tick is SystemTick.STANDARD:
            return self._update(time_mgr, component_mgr, entity_mgr)

        elif tick is SystemTick.POST:
            return self._update_post(time_mgr, component_mgr, entity_mgr)

        elif tick is SystemTick.DESTRUCTION:
            return self._update_destruction(time_mgr,
                                            component_mgr,
                                            entity_mgr)

        elif tick is SystemTick.APOPTOSIS:
            return self._update_apoptosis(time_mgr,
                                          component_mgr,
                                          entity_mgr)

        elif tick is SystemTick.APOCALYPSE:
            return self._update_apocalypse(time_mgr,
                                           component_mgr,
                                           entity_mgr)

        elif tick is SystemTick.THE_END:
            return self._update_the_end(time_mgr,
                                        component_mgr,
                                        entity_mgr)

        else:
            # This, too, should be treated as a VerediHealth.FATAL...
            raise TickError(
                "{} does not have an update_tick handler for {}.",
                self.__class__.__name__, tick)

    def _update_genesis(self,
                        time_mgr:      TimeManager,
                        component_mgr: ComponentManager,
                        entity_mgr:    EntityManager) -> VerediHealth:
        '''
        First in set-up loop. Systems should use this to load and initialize
        stuff that takes multiple cycles or is otherwise unwieldy
        during __init__.
        '''
        default_return = VerediHealth.FATAL
        self.health = default_return
        return self.health

    def _update_intra_sys(self,
                          timer: MonotonicTimer) -> VerediHealth:
        '''
        Part of the set-up ticks. Systems should use this for any
        system-to-system setup. For examples:
          - System.subscribe() gets called here.
          - Command registration happens here.
        '''
        default_return = VerediHealth.FATAL
        self.health = default_return
        return self.health

    def _update_time(self,
                     time_mgr:      TimeManager,
                     component_mgr: ComponentManager,
                     entity_mgr:    EntityManager) -> VerediHealth:
        '''
        First in Game update loop. Systems should use this rarely as the game
        time clock itself updates in this part of the loop.
        '''
        default_return = VerediHealth.FATAL
        self.health = default_return
        return self.health

    def _update_creation(self,
                         time_mgr:      TimeManager,
                         component_mgr: ComponentManager,
                         entity_mgr:    EntityManager) -> VerediHealth:
        '''
        Before Standard upate. Creation part of life cycles managed here.
        '''
        default_return = VerediHealth.FATAL
        self.health = default_return
        return self.health

    def _update_pre(self,
                    time_mgr:      TimeManager,
                    component_mgr: ComponentManager,
                    entity_mgr:    EntityManager) -> VerediHealth:
        '''
        Pre-update. For any systems that need to squeeze in something just
        before actual tick.
        '''
        default_return = VerediHealth.FATAL
        self.health = default_return
        return self.health

    def _update(self,
                time_mgr:      TimeManager,
                component_mgr: ComponentManager,
                entity_mgr:    EntityManager) -> VerediHealth:
        '''
        Normal/Standard upate. Basically everything should happen here.
        '''
        default_return = VerediHealth.FATAL
        self.health = default_return
        return self.health

    def _update_post(self,
                     time_mgr:      TimeManager,
                     component_mgr: ComponentManager,
                     entity_mgr:    EntityManager) -> VerediHealth:
        '''
        Post-update. For any systems that need to squeeze in something just
        after actual tick.
        '''
        default_return = VerediHealth.FATAL
        self.health = default_return
        return self.health

    def _update_destruction(self,
                            time_mgr:      TimeManager,
                            component_mgr: ComponentManager,
                            entity_mgr:    EntityManager) -> VerediHealth:
        '''
        Final game-loop update. Death/deletion part of life cycles
        managed here.
        '''
        default_return = VerediHealth.FATAL
        self.health = default_return
        return self.health

    def _update_apoptosis(self,
                          time_mgr:      TimeManager,
                          component_mgr: ComponentManager,
                          entity_mgr:    EntityManager) -> VerediHealth:
        '''
        Structured death phase. System should be responsive until it the next
        phase, but should be doing stuff for shutting down, like saving off
        data, etc.

        Default is "do nothing and return done."
        '''
        default_return = VerediHealth.APOPTOSIS_SUCCESSFUL
        self.health = default_return
        return self.health

    def _update_apocalypse(self,
                           time_mgr:      TimeManager,
                           component_mgr: ComponentManager,
                           entity_mgr:    EntityManager) -> VerediHealth:
        '''
        "Die now" death phase. System may now go unresponsive to events,
        function calls, etc. Systems cannot expect to have done a successful
        apoptosis.

        Default is "do nothing and return done."
        '''
        default_return = VerediHealth.APOCALYPSE_DONE
        self.health = default_return
        return self.health

    def _update_the_end(self,
                        time_mgr:      TimeManager,
                        component_mgr: ComponentManager,
                        entity_mgr:    EntityManager) -> VerediHealth:
        '''
        Final game update. This is only called once. Systems should most likely
        have nothing to do here.

        Default is "do nothing and return that we're dead now."
        '''
        default_return = VerediHealth.THE_END
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
            f"{str(self.life_cycle)}]"
        )

    def __repr__(self):
        return (
            '<v.sys:'
            f"{self.__class__.__name__}"
            f"[{self.id}, "
            f"{repr(self.life_cycle)}]>"
        )


# -----------------------------------------------------------------------------
# Tell registry to leave my children alone for @property dotted() puropses.
# -----------------------------------------------------------------------------
registry.ignore(System)
