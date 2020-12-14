# coding: utf-8

'''
Manager interface for ECS managers.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Union, Optional, Type, Any, Set, Tuple, Dict)
from veredi.base.null import (NullNoneOr, NullFalseOr, Nullable,
                              Null, null_or_none)
if TYPE_CHECKING:
    from .manager            import EcsManager
    from veredi.base.context import VerediContext
    from .base.component     import Component


from veredi.base.const       import VerediHealth
from veredi.debug.const      import DebugFlag
from veredi.data             import background

from .time                   import TimeManager
from .event                  import EventManager
from .component              import ComponentManager
from .entity                 import EntityManager
from .system                 import SystemManager
from ..data.identity.manager import IdentityManager

from .const                  import SystemTick
from .base.identity          import ComponentId, EntityId


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

    def _define_vars(self):
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        self._debug:             NullFalseOr[DebugFlag]        = Null()
        '''
        Debug flags for managers.
        '''

        self._time_manager:      NullFalseOr[TimeManager]      = Null()
        '''
        "Singleton" for TimeManager.
          - `False` indicates it explicitly does not exist.
          - `Null` indates it should but does not exist.
        '''

        self._event_manager:     NullFalseOr[EventManager]     = Null()
        '''
        "Singleton" for EventManager.
          - `False` indicates it explicitly does not exist.
          - `Null` indates it should but does not exist.
        '''

        self._component_manager: NullFalseOr[ComponentManager] = Null()
        '''
        "Singleton" for ComponentManager.
          - `False` indicates it explicitly does not exist.
          - `Null` indates it should but does not exist.
        '''

        self._entity_manager:    NullFalseOr[EntityManager]    = Null()
        '''
        "Singleton" for EntityManager.
          - `False` indicates it explicitly does not exist.
          - `Null` indates it should but does not exist.
        '''

        self._system_manager:    NullFalseOr[SystemManager]    = Null()
        '''
        "Singleton" for SystemManager.
          - `False` indicates it explicitly does not exist.
          - `Null` indates it should but does not exist.
        '''

        self._identity_manager:  NullFalseOr[IdentityManager]  = Null()
        '''
        "Singleton" for IdentityManager.
          - `False` indicates it explicitly does not exist.
          - `Null` indates it should but does not exist.
        '''

    def __init__(self,
                 time_manager:      NullFalseOr[TimeManager],
                 event_manager:     NullFalseOr[EventManager],
                 component_manager: NullFalseOr[ComponentManager],
                 entity_manager:    NullFalseOr[EntityManager],
                 system_manager:    NullFalseOr[SystemManager],
                 identity_manager:  NullFalseOr[IdentityManager],
                 debug_flags:       NullFalseOr[DebugFlag]) -> None:
        '''
        Set a manager to False if you know explicitly that it does not exist.
        '''
        self._define_vars()
        # We allow None, Null, or a thing... But we'll ignore None now.

        self._debug             = debug_flags       or self._debug
        self._time_manager      = time_manager      or self._time_manager
        self._event_manager     = event_manager     or self._event_manager
        self._component_manager = component_manager or self._component_manager
        self._entity_manager    = entity_manager    or self._entity_manager
        self._system_manager    = system_manager    or self._system_manager
        self._identity_manager  = identity_manager  or self._identity_manager

    # -------------------------------------------------------------------------
    # Meta - Do you have the ___ you need?
    # -------------------------------------------------------------------------

    def flagged(self, flag: DebugFlag) -> bool:
        '''
        Returns true if Meeting's debug flags are Truthy and have the supplied
        `flag` (which can be more than one DebugFlag bit/flag).
        '''
        return self._debug.has(flag)

    # -------------------------------------------------------------------------
    # Meta - Misc Helpers.
    # -------------------------------------------------------------------------

    def dotted(self) -> str:
        '''Veredi dotted label.'''
        return 'veredi.game.ecs.meeting'

    def get_background(self) -> Tuple[Dict[str, str], background.Ownership]:
        '''
        Data for the Veredi Background context.

        Returns: (data, background.Ownership)
        '''
        bg = {
            background.Name.DOTTED.key: self.dotted(),
        }
        return bg, background.Ownership.SHARE

    def healthy(self,
                required_set: NullNoneOr[Set[Type['EcsManager']]]
                ) -> VerediHealth:
        '''
        Returns:
          - HEALTHY if all required managers are attending the meeting.

          - UNHEALTHY if a required manager is explicitly absent
            (that is, we have it set to False).

          - PENDING if a required manager is implicitly absent
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
        if IdentityManager in required_set and not self._identity_manager:
            return (VerediHealth.UNHEALTHY
                    if self._identity_manager is False else
                    VerediHealth.PENDING)

        # Otherwise we're good.
        return VerediHealth.HEALTHY

    # -------------------------------------------------------------------------
    # Properties - Access the Managers
    # -------------------------------------------------------------------------

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

    @property
    def identity(self) -> Union[IdentityManager, bool, Null]:
        '''
        Returns IdentityManager. If this returns 'False' (as opposed to
        Null/Falsy), that is explicitly stating the explicit absense of an
        IdentityManager.
        '''
        # Stupid code-wise, but I want to explicitly state that False is the
        # explicit absense of an IdentityManager.
        if self._identity_manager is False:
            return False
        return self._identity_manager

    # -------------------------------------------------------------------------
    # Inter-Managerial Helpers
    # -------------------------------------------------------------------------

    def create_attach(self,
                      entity_id:              EntityId,
                      component_name_or_type: Union[str, Type['Component']],
                      context:                Optional['VerediContext'],
                      *args:                  Any,
                      **kwargs:               Any) -> ComponentId:
        '''
        Asks ComponentManager to create the `component_name_or_type`
        with `context`, `args`, `kwargs`.

        Then asks EntityManager to attach it to `entity_id`.

        Returns the created component's ComponentId.
        '''
        if not self.component or not self.entity:
            return ComponentId.INVALID

        retval = self.component.create(component_name_or_type,
                                       context,
                                       *args, **kwargs)
        self.entity.attach(entity_id, retval)

        return retval

    def get_with_log(self,
                     caller: str,
                     entity_id: 'EntityId',
                     comp_type: Type['Component'],
                     event:     NullNoneOr['Event']         = None,
                     context:   NullNoneOr['VerediContext'] = None,
                     preface:   Optional[str]               = None
                     ) -> Tuple[Nullable['Entity'], Nullable['Component']]:
        '''
        Checks to see if entity exists and has a component of the correct type.

        Returns a tuple of (entity, component) if so.
        Logs at INFO level and returns Null() for non-existant pieces, so:
            (Null(), Null())
          or
            (entity, Null())
        '''
        # Just `get` entity... `ComponentManager.get_with_log()` will call
        # `EntityManager.get_with_log()`, and that will give us both logs if
        # needed.
        entity = self.entity.get(entity_id)
        component = self.component.get_with_log(caller,
                                                entity_id,
                                                comp_type,
                                                event=event,
                                                context=context,
                                                preface=preface)
        # entity or Null(), and
        # component or Null(), so...
        return (entity, component)


    # -------------------------------------------------------------------------
    # Life-Cycle Management
    # -------------------------------------------------------------------------

    def life_cycle(self,
                   cycle_from: SystemTick,
                   cycle_to:   SystemTick,
                   tick_from:  SystemTick,
                   tick_to:    SystemTick) -> VerediHealth:
        '''
        Engine calls this for a valid life-cycle transition and for valid tick
        transitions of interest.

        Valid life-cycle transitions are best checked in engine's
        _run_trans_validate(), but here's a summary of both life-cycle and tick
        transitions:

          - INVALID -> TICKS_START:
            - INVALID -> GENESIS
            - GENESIS -> INTRA_SYSTEM

          - TICKS_START -> TICKS_RUN

          - ??? -> TICKS_END:
            - ???        -> APOPTOSIS
            - APOPTOSIS  -> APOCALYPSE
            - APOCALYPSE -> THE_END

        NOTE: This is only called if there is a valid life-cycle/tick-cycle of
        interest.

        Updates self._health with result of life-cycle function. Returnns
        result of life-cycle function (not necessarily what self._health is).
        '''
        health = self._each_existing('life_cycle',
                                     cycle_from, cycle_to,
                                     tick_from, tick_to)
        return health

    # -------------------------------------------------------------------------
    # Life-Cycle Management
    # -------------------------------------------------------------------------

    def _each_existing(self,
                       function_name: str,
                       *args: Any,
                       **kwargs: Any) -> VerediHealth:
        '''
        Gets function attribute from each non-None/Null manager. Runs
        "manager.`function`(*`args`, **`kwargs`)" if attribute is found.

        Returns VerediHealth.
          - If functions return a VerediHealth value, keep a running total and
            return that. Otherwise returns HEALTHY.
        '''
        health = VerediHealth.HEALTHY

        # ------------------------------
        # Time Manager
        # ------------------------------
        if not null_or_none(self._time_manager):
            function = getattr(self._time_manager,
                               function_name,
                               Null())
            result = function(*args, **kwargs)
            if isinstance(result, VerediHealth):
                health = health.update(result)

        # ------------------------------
        # Event Manager
        # ------------------------------
        if not null_or_none(self._event_manager):
            function = getattr(self._event_manager,
                               function_name,
                               Null())
            result = function(*args, **kwargs)
            if isinstance(result, VerediHealth):
                health = health.update(result)

        # ------------------------------
        # Component Manager
        # ------------------------------
        if not null_or_none(self._component_manager):
            function = getattr(self._component_manager,
                               function_name,
                               Null())
            result = function(*args, **kwargs)
            if isinstance(result, VerediHealth):
                health = health.update(result)

        # ------------------------------
        # Entity Manager
        # ------------------------------
        if not null_or_none(self._entity_manager):
            function = getattr(self._entity_manager,
                               function_name,
                               Null())
            result = function(*args, **kwargs)
            if isinstance(result, VerediHealth):
                health = health.update(result)

        # ------------------------------
        # System Manager
        # ------------------------------
        if not null_or_none(self._system_manager):
            function = getattr(self._system_manager,
                               function_name,
                               Null())
            result = function(*args, **kwargs)
            if isinstance(result, VerediHealth):
                health = health.update(result)

        # ------------------------------
        # Identity Manager
        # ------------------------------
        if not null_or_none(self._identity_manager):
            function = getattr(self._identity_manager,
                               function_name,
                               Null())
            result = function(*args, **kwargs)
            if isinstance(result, VerediHealth):
                health = health.update(result)

        return health
