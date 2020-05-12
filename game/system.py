# coding: utf-8

'''
Base class for game update loop systems.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Iterable, Set, Union
import enum

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
    Low priority go last, so they get a bigger value.
    '''
    LOW    = 10000
    MEDIUM = 1000
    HIGH   = 100

    @staticmethod
    def compare(left:  Union['SystemPriority', int],
                right: Union['SystemPriority', int]):
        '''
        Compares two priority/int values against each other
        for priority sorting.
        '''

        if left < right:
            return -1
        elif left > right:
            return 1
        return 0


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
        self._health = {} # TODO: impl this? or put in game?

    # --------------------------------------------------------------------------
    # System Registration / Definition
    # --------------------------------------------------------------------------

    @classmethod
    def register(cls: 'System') -> Optional[SystemTick]:
        '''
        Returns a SystemTick value of flagged ticks this system desires to run
        during.
        '''
        return None

    def priority(self) -> Union[SystemPriority, int]:
        '''
        Returns a SystemPriority (or int) for when, relative to other systems,
        this should run. Highest priority goes firstest.
        '''
        return SystemPriority.LOW

    @staticmethod
    def compare(left: 'System', right: 'System'):
        '''
        Compares two systems against each other for priority sorting.
        '''
        return SystemPriority.compare(left.priority(), right.priority())

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

    def update_tick(self,
                    tick: SystemTick,
                    time: float,
                    sys_entities: 'System',
                    sys_time: 'System') -> SystemHealth:
        '''
        Calls the correct update function for the tick state.

        Returns SystemHealth value.
        '''
        if tick is SystemTick.TIME:
            return self.update_time(tick, time, sys_entities, sys_time)

        elif tick is SystemTick.LIFE:
            return self.update_life(tick, time, sys_entities, sys_time)

        elif tick is SystemTick.PRE:
            return self.update_pre(tick, time, sys_entities, sys_time)

        elif tick is SystemTick.STANDARD:
            return self.update(tick, time, sys_entities, sys_time)

        elif tick is SystemTick.POST:
            return self.update_post(tick, time, sys_entities, sys_time)

        elif tick is SystemTick.DEATH:
            return self.update_death(tick, time, sys_entities, sys_time)

        else:
            # This, too, should be treated as a SystemHealth.FATAL...
            raise exceptions.TickError(
                "{} does not have an update_tick handler for {}.",
                self.__class__.__name__, tick)

    def update_time(self,
                    time: float,
                    sys_entities: 'System',
                    sys_time: 'System') -> SystemHealth:
        '''
        First in Game update loop. Systems should use this rarely as the game
        time clock itself updates in this part of the loop.
        '''
        return SystemHealth.FATAL

    def update_life(self,
                    time: float,
                    sys_entities: 'System',
                    sys_time: 'System') -> SystemHealth:
        '''
        Before Standard upate. Creation part of life cycles managed here.
        '''
        return SystemHealth.FATAL

    def update_pre(self,
                   time: float,
                   sys_entities: 'System',
                   sys_time: 'System') -> SystemHealth:
        '''
        Pre-update. For any systems that need to squeeze in something just
        before actual tick.
        '''
        return SystemHealth.FATAL

    def update(self,
               time: float,
               sys_entities: 'System',
               sys_time: 'System') -> SystemHealth:
        '''
        Normal/Standard upate. Basically everything should happen here.
        '''
        return SystemHealth.FATAL

    def update_post(self,
                    time: float,
                    sys_entities: 'System',
                    sys_time: 'System') -> SystemHealth:
        '''
        Post-update. For any systems that need to squeeze in something just
        after actual tick.
        '''
        return SystemHealth.FATAL

    def update_death(self,
                    time: float,
                    sys_entities: 'System',
                    sys_time: 'System') -> SystemHealth:
        '''
        Final upate. Death/deletion part of life cycles managed here.
        '''
        return SystemHealth.FATAL
