# coding: utf-8

'''
Base class for game update loop systems.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import NewType, Optional, Iterable, Set, Union, Any, Type
import enum

from veredi.logger import log
from veredi.base.const import VerediHealth
from veredi.base.context import VerediContext
from veredi.data.config.config import Configuration

from ..const import SystemTick, SystemPriority
from .exceptions import SystemError
from .identity import (ComponentId,
                       EntityId,
                       SystemId)
from .component import (Component,
                        ComponentError)
from .entity import Entity


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

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


# ------------------------------------------------------------------------------
# Code
# ------------------------------------------------------------------------------

class System:
    def __init__(self,
                 sid: SystemId,
                 *args: Any,
                 **kwargs: Any) -> None:

        self._system_id:  SystemId                       = sid
        self._life_cycle: SystemLifeCycle                = SystemLifeCycle.INVALID

        self._components: Optional[Set[Type[Component]]] = None
        self._ticks:      Optional[SystemTick]           = None

    @property
    def id(self) -> SystemId:
        return self._system_id

    @property
    def enabled(self) -> bool:
        return self._life_cycle == ComponentLifeCycle.ALIVE

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

    # --------------------------------------------------------------------------
    # System Registration / Definition
    # --------------------------------------------------------------------------

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

    def required(self) -> Optional[Iterable[Component]]:
        '''
        Returns the Component types this system /requires/ in order to function
        on an entity.

        e.g. Perhaps a Combat system /requires/ Health and Defense components,
        and uses others like Position, Attack... This function should only
        return Health and Defense.
        '''
        return self._components

    # --------------------------------------------------------------------------
    # System Death
    # --------------------------------------------------------------------------

    def apoptosis(self, time: 'TimeManager') -> VerediHealth:
        '''
        Game is ending gracefully. Do graceful end-of-the-world stuff...
        '''
        return VerediHealth.APOPTOSIS

    # --------------------------------------------------------------------------
    # Events
    # --------------------------------------------------------------------------

    def subscribe(self, event_manager: 'EventManager') -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        return VerediHealth.HEALTY

    def event(self,
              event_manager:              'EventManager',
              event_class:                Type['Event'],
              owner_id:                   int,
              type:                       Union[int, enum.Enum],
              context:                    Optional[VerediContext],
              requires_immediate_publish: bool,
              *args:                      Any,
              **kwargs:                   Any) -> None:
        '''
        Calls event_manager.create() if event_manager exists.
        '''
        if not event_manager:
            return
        event_manager.create(
            event_class,
            owner_id,
            type,
            context,
            requires_immediate_publish,
            *args,
            **kwargs)

    # --------------------------------------------------------------------------
    # Game Update Loop/Tick Functions
    # --------------------------------------------------------------------------

    def wants_update_tick(self,
                          tick: SystemTick,
                          time_mgr: 'TimeManager') -> bool:
        '''
        Returns a boolean for whether this system wants to run during this tick
        update function.
        '''
        return self._ticks is not None and self._ticks.has(tick)

    def update_tick(self,
                    tick:          SystemTick,
                    time_mgr:      'TimeManager',
                    component_mgr: 'ComponentManager',
                    entity_mgr:    'EntityManager') -> VerediHealth:
        '''
        Calls the correct update function for the tick state.

        Returns SystemHegalth value.
        '''
        if tick is SystemTick.TIME:
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
            return self._update_destruction(time_mgr, component_mgr, entity_mgr)

        else:
            # This, too, should be treated as a VerediHealth.FATAL...
            raise exceptions.TickError(
                "{} does not have an update_tick handler for {}.",
                self.__class__.__name__, tick)

    def _update_time(self,
                     time_mgr:      'TimeManager',
                     component_mgr: 'ComponentManager',
                     entity_mgr:    'EntityManager') -> VerediHealth:
        '''
        First in Game update loop. Systems should use this rarely as the game
        time clock itself updates in this part of the loop.
        '''
        return VerediHealth.FATAL

    def _update_creation(self,
                         time_mgr:      'TimeManager',
                         component_mgr: 'ComponentManager',
                         entity_mgr:    'EntityManager') -> VerediHealth:
        '''
        Before Standard upate. Creation part of life cycles managed here.
        '''
        return VerediHealth.FATAL

    def _update_pre(self,
                    time_mgr:      'TimeManager',
                    component_mgr: 'ComponentManager',
                    entity_mgr:    'EntityManager') -> VerediHealth:
        '''
        Pre-update. For any systems that need to squeeze in something just
        before actual tick.
        '''
        return VerediHealth.FATAL

    def _update(self,
                time_mgr:      'TimeManager',
                component_mgr: 'ComponentManager',
                entity_mgr:    'EntityManager') -> VerediHealth:
        '''
        Normal/Standard upate. Basically everything should happen here.
        '''
        return VerediHealth.FATAL

    def _update_post(self,
                     time_mgr:      'TimeManager',
                     component_mgr: 'ComponentManager',
                     entity_mgr:    'EntityManager') -> VerediHealth:
        '''
        Post-update. For any systems that need to squeeze in something just
        after actual tick.
        '''
        return VerediHealth.FATAL

    def _update_destruction(self,
                            time_mgr:      'TimeManager',
                            component_mgr: 'ComponentManager',
                            entity_mgr:    'EntityManager') -> VerediHealth:
        '''
        Final upate. Death/deletion part of life cycles managed here.
        '''
        return VerediHealth.FATAL

    def __str__(self):
        return (
            f"{self.__class__.__name__}"
            f"[id:{self.id:03d}, "
            f"{str(self.life_cycle)}]"
        )

    def __repr__(self):
        return (
            '<v.sys:'
            f"{self.__class__.__name__}"
            f"[id:{self.id:03d}, "
            f"{repr(self.life_cycle)}]>"
        )
