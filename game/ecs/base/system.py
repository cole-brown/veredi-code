# coding: utf-8

'''
Base class for game update loop systems.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Type, Any, Iterable, Set)
from veredi.base.null import NullNoneOr
if TYPE_CHECKING:
    from ..meeting                  import Meeting
    from veredi.base.context        import VerediContext
    from veredi.data.config.context import ConfigContext


from abc import ABC, abstractmethod
import enum
import decimal

from veredi.logger     import log
from veredi.base.const import VerediHealth

from ..const           import SystemTick, SystemPriority, DebugFlag
from .exceptions       import SystemErrorV
from ..exceptions      import TickError
from .identity         import SystemId
from .component        import Component

from ..manager         import EcsManager
from ..time            import TimeManager
from ..event           import EventManager, Event
from ..component       import ComponentManager
from ..entity          import EntityManager


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# ---
# System's Life Cycle State
# ---

@enum.unique
class SystemLifeCycle(enum.Enum):
    INVALID    = 0
    CREATING   = enum.auto()
    ALIVE      = enum.auto()
    DESTROYING = enum.auto()
    DEAD       = enum.auto()

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
    def __init__(self,
                 context:  Optional['VerediContext'],
                 sid:      SystemId,
                 managers: 'Meeting') -> None:

        self._life_cycle: SystemLifeCycle = SystemLifeCycle.INVALID
        self._system_id:          SystemId                       = sid

        self._components_req:     Optional[Set[Type[Component]]] = None
        self._components_req_all: bool                           = True
        self._ticks:              Optional[SystemTick]           = None

        self._manager:            'Meeting'                      = managers

        # ---
        # Self-Health Set Up
        # ---
        # If we get in a not-healthy state, we'll start just dropping inputs.
        self._health_state: VerediHealth = VerediHealth.HEALTHY
        self._required_managers: Optional[Set[Type[EcsManager]]] = None

        # Most systems have these, so we'll just define 'em in the base.
        self._health_meter_event:   Optional[Decimal] = None
        self._health_meter_update:  Optional[Decimal] = None

        # Systems can set up more logging meters like those for use with
        # self._health_log(). E.g.:
        # Then call self._health_log() like, say...
        #     # Doctor checkup.
        #     if not self._healthy():
        #         self._health_meter_jeff = self._health_log(
        #             self._health_meter_jeff,
        #             log.Level.WARNING,
        #             "HEALTH({}): Skipping jeff - our system health "
        #             "isn't good enough to process.",
        #             self._state, event,
        #             context=event.context)
        #         return

        # ---
        # Final init set up/configuration from context/config and
        # system-specific stuff.
        # ---
        self._configure(context)

    @property
    def id(self) -> SystemId:
        return SystemId.INVALID if self._system_id is None else self._system_id

    @property
    @abstractmethod
    def name(self) -> str:
        '''
        The 'dotted string' name this system has. Probably what they used to
        register.
        E.g.
          @register('veredi', 'input', 'system')
        would be:
          'veredi.input.system'
        '''
        raise NotImplementedError

    @property
    def enabled(self) -> bool:
        return self._life_cycle == SystemLifeCycle.ALIVE

    @property
    def life_cycle(self) -> SystemLifeCycle:
        return self._life_cycle

    def _life_cycled(self, new_state: SystemLifeCycle) -> None:
        '''
        SystemManager calls this to update life cycle. Will be called on:
          - INVALID  -> CREATING   : During SystemManager.create().
          - CREATING -> ALIVE      : During SystemManager.creation()
          - ALIVE    -> DESTROYING : During SystemManager.destroy().
          - DESTROYING -> DEAD     : During SystemManager.destruction()
        '''
        self._life_cycle = new_state

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
    # System Death / Health
    # -------------------------------------------------------------------------

    def apoptosis(self, time: 'TimeManager') -> VerediHealth:
        '''
        Game is ending gracefully. Do graceful end-of-the-world stuff...
        '''
        self._health_state = VerediHealth.APOPTOSIS
        return VerediHealth.APOPTOSIS

    @property
    def health(self) -> VerediHealth:
        return self._health_state

    def _healthy(self) -> bool:
        '''
        Are we in a runnable state?
        '''
        return self._health_state.good

    def _health_check(self,
                      current_health=VerediHealth.HEALTHY) -> VerediHealth:
        '''
        Tracks our system health. Returns either `current_health` or something
        worse from what all we track.
        '''
        manager_health = self._manager.healthy(self._required_managers)
        if not manager_health.good:
            self._health_state = VerediHealth.set(manager_health,
                                                  self._health_state)
            # We rely on those managers to function, so we're bad if
            # they don't exist.
            return self.health

        # Set our state to whatever's worse and return that.
        # TODO [2020-06-04]: Eventually maybe a gradient of health so one
        # bad thing doesn't knock us offline?
        self._health_state = VerediHealth.worse(current_health,
                                                self._health_state)
        return self.health

    def _health_log(self,
                    log_meter: decimal.Decimal,
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
            log.at_level(log_level,
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
        if not self._healthy():
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
        if not self._healthy():
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
                        context:  NullNoneOr['VerediContext']) -> bool:
        '''Check health, log if needed, and return True if able to proceed.'''
        if not self._healthy():
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

    def subscribe(self, event_manager: EventManager) -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        # Sanity checks...
        if (event_manager
                and self._manager and self._manager.event
                and self._manager.event is not event_manager):
            raise log.exception(None,
                                SystemErrorV,
                                "subscribe() received an EventManager which "
                                "is different from its saved EventManager "
                                "from initialization. ours: {}, supplied: {}",
                                self._manager.event, event_manager)

        if (self._required_managers and EventManager in self._required_managers
                and not self._manager.event):
            raise log.exception(None,
                                SystemErrorV,
                                "System has no event manager to subscribe to "
                                "but requires one.",
                                self._manager.event, event_manager)

        return VerediHealth.HEALTHY

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
                          tick: SystemTick,
                          time_mgr: 'TimeManager') -> bool:
        '''
        Returns a boolean for whether this system wants to run during this tick
        update function.
        '''
        return self._ticks is not None and self._ticks.has(tick)

    def required(self) -> Optional[Iterable[Component]]:
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
            return self._update_intra_system(time_mgr,
                                             component_mgr,
                                             entity_mgr)

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
        return VerediHealth.FATAL

    def _update_intra_sys(self,
                          time_mgr:      TimeManager,
                          component_mgr: ComponentManager,
                          entity_mgr:    EntityManager) -> VerediHealth:
        '''
        Part of the set-up ticks. Systems should use this for any
        system-to-system setup. For examples:
          - System.subscribe() gets called here.
          - Command registration happens here.
        '''
        return VerediHealth.FATAL

    def _update_time(self,
                     time_mgr:      TimeManager,
                     component_mgr: ComponentManager,
                     entity_mgr:    EntityManager) -> VerediHealth:
        '''
        First in Game update loop. Systems should use this rarely as the game
        time clock itself updates in this part of the loop.
        '''
        return VerediHealth.FATAL

    def _update_creation(self,
                         time_mgr:      TimeManager,
                         component_mgr: ComponentManager,
                         entity_mgr:    EntityManager) -> VerediHealth:
        '''
        Before Standard upate. Creation part of life cycles managed here.
        '''
        return VerediHealth.FATAL

    def _update_pre(self,
                    time_mgr:      TimeManager,
                    component_mgr: ComponentManager,
                    entity_mgr:    EntityManager) -> VerediHealth:
        '''
        Pre-update. For any systems that need to squeeze in something just
        before actual tick.
        '''
        return VerediHealth.FATAL

    def _update(self,
                time_mgr:      TimeManager,
                component_mgr: ComponentManager,
                entity_mgr:    EntityManager) -> VerediHealth:
        '''
        Normal/Standard upate. Basically everything should happen here.
        '''
        return VerediHealth.FATAL

    def _update_post(self,
                     time_mgr:      TimeManager,
                     component_mgr: ComponentManager,
                     entity_mgr:    EntityManager) -> VerediHealth:
        '''
        Post-update. For any systems that need to squeeze in something just
        after actual tick.
        '''
        return VerediHealth.FATAL

    def _update_destruction(self,
                            time_mgr:      TimeManager,
                            component_mgr: ComponentManager,
                            entity_mgr:    EntityManager) -> VerediHealth:
        '''
        Final upate. Death/deletion part of life cycles managed here.
        '''
        return VerediHealth.FATAL

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
