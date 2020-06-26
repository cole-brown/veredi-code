# coding: utf-8

'''
Manager interface for ECS managers.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Union, TypeVar, Type, Set)
from veredi.base.null import Nullable, NullNoneOr, NullFalseOr, Null
if TYPE_CHECKING:
    from .manager import EcsManager


from veredi.base.const import VerediHealth

from .time             import TimeManager
from .event            import EventManager
from .component        import ComponentManager
from .entity           import EntityManager
from .system           import SystemManager
from .const            import DebugFlag


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Meeting:
    '''
    ...cuz managers are always in meetings, obviously.

    Helper class to hold onto stuff we use and pass into created Systems.
    '''

    def __init__(self,
                 time_manager:      NullFalseOr[TimeManager],
                 event_manager:     NullFalseOr[EventManager],
                 component_manager: NullFalseOr[ComponentManager],
                 entity_manager:    NullFalseOr[EntityManager],
                 system_manager:    NullFalseOr[SystemManager],
                 debug_flags:       NullFalseOr[DebugFlag]) -> None:
        '''
        Set a manager to False if you know explicitly that it does not exist.
        '''
        # We allow None, Null, or a thing... But we'll ignore None now.
        self._debug:             NullFalseOr[DebugFlag]        = Null()
        self._time_manager:      NullFalseOr[TimeManager]      = Null()
        self._event_manager:     NullFalseOr[EventManager]     = Null()
        self._component_manager: NullFalseOr[ComponentManager] = Null()
        self._entity_manager:    NullFalseOr[EntityManager]    = Null()
        self._system_manager:    NullFalseOr[SystemManager]    = Null()

        self._debug             = debug_flags       or self._debug
        self._time_manager      = time_manager      or self._time_manager
        self._event_manager     = event_manager     or self._event_manager
        self._component_manager = component_manager or self._component_manager
        self._entity_manager    = entity_manager    or self._entity_manager
        self._system_manager    = system_manager    or self._system_manager

    def healthy(self,
                required_set: NullNoneOr[Set[Type['EcsManager']]]
                ) -> VerediHealth:
        '''
        Returns HEALTHY if all required managers are attending the meeting.
        Returns UNHEALTHY if a required manager is explicitly absent
        (that is, we have it set to False).
        Returns PENDING if a required manager is implicitly absent
        (that is, we have it as a Falsy value like Null).
        '''
        # If nothing is required, ok.
        if not required_set:
            return VerediHealth.HEALTHY

        # Fail if any required are not present.
        if TimeManager in required_set and not self._time_manager:
            return (VerediHealth.UNHEALTHY
                    if self._time_manager is False else
                    VerediHealth.PENDING)
        if EventManager in required_set and not self._event_manager:
            return (VerediHealth.UNHEALTHY
                    if self._event_manager is False else
                    VerediHealth.PENDING)
        if ComponentManager in required_set and not self._component_manager:
            return (VerediHealth.UNHEALTHY
                    if self._component_manager is False else
                    VerediHealth.PENDING)
        if EntityManager in required_set and not self._entity_manager:
            return (VerediHealth.UNHEALTHY
                    if self._entity_manager is False else
                    VerediHealth.PENDING)
        if SystemManager in required_set and not self._system_manager:
            return (VerediHealth.UNHEALTHY
                    if self._system_manager is False else
                    VerediHealth.PENDING)

        # Otherwise we're good.
        return VerediHealth.HEALTHY

    @property
    def time(self) -> Union[TimeManager, bool, Null]:
        '''
        Returns TimeManager. If this returns 'False' (as opposed to
        Null/Falsy), that is explicitly stating the explicit absense of a
        TimeManager.
        '''
        # Stupid code-wise, but I want to explicitly state that False is the
        # explicit absense of a TimeManager.
        if self._time_manager is False:
            return False
        return self._time_manager

    @property
    def event(self) -> Union[EventManager, bool, Null]:
        '''
        Returns EventManager. If this returns 'False' (as opposed to
        Null/Falsy), that is explicitly stating the explicit absense of an
        EventManager.
        '''
        # Stupid code-wise, but I want to explicitly state that False is the
        # explicit absense of an EventManager.
        if self._event_manager is False:
            return False
        return self._event_manager

    @property
    def component(self) -> Union[ComponentManager, bool, Null]:
        '''
        Returns ComponentManager. If this returns 'False' (as opposed to
        Null/Falsy), that is explicitly stating the explicit absense of a
        ComponentManager.
        '''
        # Stupid code-wise, but I want to explicitly state that False is the
        # explicit absense of a ComponentManager.
        if self._component_manager is False:
            return False
        return self._component_manager

    @property
    def entity(self) -> Union[EntityManager, bool, Null]:
        '''
        Returns EntityManager. If this returns 'False' (as opposed to
        Null/Falsy), that is explicitly stating the explicit absense of an
        EntityManager.
        '''
        # Stupid code-wise, but I want to explicitly state that False is the
        # explicit absense of an EntityManager.
        if self._entity_manager is False:
            return False
        return self._entity_manager

    @property
    def system(self) -> Union[SystemManager, bool, Null]:
        '''
        Returns SystemManager. If this returns 'False' (as opposed to
        Null/Falsy), that is explicitly stating the explicit absense of an
        SystemManager.
        '''
        # Stupid code-wise, but I want to explicitly state that False is the
        # explicit absense of an SystemManager.
        if self._system_manager is False:
            return False
        return self._system_manager
