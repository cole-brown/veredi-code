# coding: utf-8

'''
Base class for game update loop systems.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Iterable, Set, Union
import enum
import decimal

from veredi.entity.component import (EntityId,
                                     INVALID_ENTITY_ID,
                                     Component,
                                     ComponentMetaData,
                                     ComponentError)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

@enum.unique
class SystemTick(enum.Flag):
    TIME     = enum.auto()
    LIFE     = enum.auto()
    PRE      = enum.auto()
    STANDARD = enum.auto()
    POST     = enum.auto()
    DEATH    = enum.auto()

    def has(self, tick):
        if (self & tick) == tick:
            return True
        return False


class SystemPriority(enum.IntEnum):
    '''
    Low priority systems go last, so that a standard (non-reversed) sort will
    sort them in high-to-low priority.
    '''
    LOW    = 10000
    MEDIUM = 1000
    HIGH   = 100


@enum.unique
class SystemHealth(enum.Enum):
    FATAL     = enum.auto()
    UNHEALTHY = enum.auto()
    HEALTHY   = enum.auto()


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class System:
    def __init__(self) -> None:
        self._components = None
        self._health = {} # TODO: impl this? or put in game class?
        self._ticks = None

    # --------------------------------------------------------------------------
    # System Registration / Definition
    # --------------------------------------------------------------------------

    def priority(self) -> Union[SystemPriority, int]:
        '''
        Returns a SystemPriority (or int) for when, relative to other systems,
        this should run. Highest priority goes firstest.
        '''
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
        return None

    # --------------------------------------------------------------------------
    # Game Update Loop/Tick Functions
    # --------------------------------------------------------------------------

    def wants_update_tick(self,
                          tick: SystemTick,
                          time: decimal.Decimal) -> bool:
        '''
        Returns a boolean for whether this system wants to run during this tick
        update function.
        '''
        return self._ticks is not None and self._ticks.has(tick)

    def update_tick(self,
                    tick: SystemTick,
                    time: decimal.Decimal,
                    sys_entities: 'System',
                    sys_time: 'System') -> SystemHealth:
        '''
        Calls the correct update function for the tick state.

        Returns SystemHealth value.
        '''
        if tick is SystemTick.TIME:
            return self.update_time(time, sys_entities, sys_time)

        elif tick is SystemTick.LIFE:
            return self.update_life(time, sys_entities, sys_time)

        elif tick is SystemTick.PRE:
            return self.update_pre(time, sys_entities, sys_time)

        elif tick is SystemTick.STANDARD:
            return self.update(time, sys_entities, sys_time)

        elif tick is SystemTick.POST:
            return self.update_post(time, sys_entities, sys_time)

        elif tick is SystemTick.DEATH:
            return self.update_death(time, sys_entities, sys_time)

        else:
            # This, too, should be treated as a SystemHealth.FATAL...
            raise exceptions.TickError(
                "{} does not have an update_tick handler for {}.",
                self.__class__.__name__, tick)

    def update_time(self,
                    time: decimal.Decimal,
                    sys_entities: 'System',
                    sys_time: 'System') -> SystemHealth:
        '''
        First in Game update loop. Systems should use this rarely as the game
        time clock itself updates in this part of the loop.
        '''
        return SystemHealth.FATAL

    def update_life(self,
                    time: decimal.Decimal,
                    sys_entities: 'System',
                    sys_time: 'System') -> SystemHealth:
        '''
        Before Standard upate. Creation part of life cycles managed here.
        '''
        return SystemHealth.FATAL

    def update_pre(self,
                   time: decimal.Decimal,
                   sys_entities: 'System',
                   sys_time: 'System') -> SystemHealth:
        '''
        Pre-update. For any systems that need to squeeze in something just
        before actual tick.
        '''
        return SystemHealth.FATAL

    def update(self,
               time: decimal.Decimal,
               sys_entities: 'System',
               sys_time: 'System') -> SystemHealth:
        '''
        Normal/Standard upate. Basically everything should happen here.
        '''
        return SystemHealth.FATAL

    def update_post(self,
                    time: decimal.Decimal,
                    sys_entities: 'System',
                    sys_time: 'System') -> SystemHealth:
        '''
        Post-update. For any systems that need to squeeze in something just
        after actual tick.
        '''
        return SystemHealth.FATAL

    def update_death(self,
                    time: decimal.Decimal,
                    sys_entities: 'System',
                    sys_time: 'System') -> SystemHealth:
        '''
        Final upate. Death/deletion part of life cycles managed here.
        '''
        return SystemHealth.FATAL

