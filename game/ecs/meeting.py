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
    from veredi.base.context import VerediContext
    from .base.entity        import Entity
    from .base.component     import Component


from veredi.base.const       import VerediHealth
from veredi.base.exceptions  import HealthError
from veredi.debug.const      import DebugFlag
from veredi.data             import background

from .manager                import EcsManager

from .time                   import TimeManager
from .event                  import EventManager, Event
from .component              import ComponentManager
from .entity                 import EntityManager
from .system                 import SystemManager
from ..data.manager          import DataManager
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
        self._debug: NullFalseOr[DebugFlag] = Null()
        '''
        Debug flags for managers.
        '''

        self._time_manager: NullFalseOr[TimeManager] = Null()
        '''
        "Singleton" for TimeManager.
          - `False` indicates it explicitly does not exist.
          - `Null` indates it should but does not exist.
        '''

        self._event_manager: NullFalseOr[EventManager] = Null()
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

        self._entity_manager: NullFalseOr[EntityManager] = Null()
        '''
        "Singleton" for EntityManager.
          - `False` indicates it explicitly does not exist.
          - `Null` indates it should but does not exist.
        '''

        self._system_manager: NullFalseOr[SystemManager] = Null()
        '''
        "Singleton" for SystemManager.
          - `False` indicates it explicitly does not exist.
          - `Null` indates it should but does not exist.
        '''

        self._data_manager: NullFalseOr[DataManager] = Null()
        '''
        "Singleton" for DataManager.
          - `False` indicates it explicitly does not exist.
          - `Null` indates it should but does not exist.
        '''

        self._identity_manager: NullFalseOr[IdentityManager] = Null()
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
                 data_manager:      NullFalseOr[DataManager],
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
        self._data_manager      = data_manager      or self._data_manager
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
        Data about all our managers for the Veredi Background context.

        Returns: (data, background.Ownership)
        '''
        bg = {
            background.Name.DOTTED.key: self.dotted(),
            'time': self.time.get_background(),
            'event': self.event.get_background(),
            'component': self.component.get_background(),
            'entity': self.entity.get_background(),
            'system': self.system.get_background(),
            'data': self.data.get_background(),
            'identity': self.identity.get_background(),
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
        if DataManager in required_set and not self._data_manager:
            return (VerediHealth.UNHEALTHY
                    if self._data_manager is False else
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
    def data(self) -> Union[DataManager, bool, Null]:
        '''
        Returns DataManager. If this returns 'False' (as opposed to
        Null/Falsy), that is explicitly stating the explicit absense of an
        DataManager.
        '''
        # Stupid code-wise, but I want to explicitly state that False is the
        # explicit absense of an DataManager.
        if self._data_manager is False:
            return False
        return self._data_manager

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

          - INVALID -> TICKS_BIRTH:
            - INVALID   -> SYNTHESIS
            - SYNTHESIS -> MITOSIS

          - TICKS_BIRTH -> TICKS_LIFE

          - ??? -> TICKS_DEATH:
            - ???       -> AUTOPHAGY
            - AUTOPHAGY -> APOPTOSIS
            - APOPTOSIS -> NECROSIS

        NOTE: This is only called if there is a valid life-cycle/tick-cycle of
        interest.

        Updates self._health with result of life-cycle function. Returnns
        result of life-cycle function (not necessarily what self._health is).
        '''
        health = self._each_existing_health('life_cycle',
                                            cycle_from, cycle_to,
                                            tick_from, tick_to)
        return health

    # -------------------------------------------------------------------------
    # Life-Cycle Management
    # -------------------------------------------------------------------------

    def _call_if_exists(self,
                        manager: EcsManager,
                        health:  VerediHealth,
                        function_name: str,
                        *args: Any,
                        **kwargs: Any) -> VerediHealth:
        '''
        If `manager` is Null or None, do nothing and return `health`.

        Else, try to get `function_name` from manager, try to call it with
        `*args` and `**kwargs`.

        Update `health` with the function call result and return updated
        health.
        '''
        if null_or_none(manager):
            return health

        # Have a manager, at least. Use 'Null()' as fallback so we can just
        # fail for a bit and recover at the end.
        function = getattr(manager,
                           function_name,
                           Null())
        result = function(*args, **kwargs)

        # Sanity check.
        if isinstance(result, VerediHealth):
            return health.update(result)

        # Recover from Null here; works also for functions that returned an
        # incorrect type. We just fail if we got not-a-health result.
        else:
            msg = (f"Attempt to call `{function_name}` gave unexpected result "
                   "(expected a VerediHealth value). Function does not exist "
                   "or returned incorrect result.")
            error = HealthError(VerediHealth.FATAL,
                                health,
                                msg,
                                data={
                                    'manager':       manager,
                                    'prev_health':   health,
                                    'function_name': function_name,
                                    'function':      function,
                                    'result':        result,
                                })
            raise self._log_exception(error, msg)

    def _each_existing_health(self,
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
        health.update(self._call_if_exists(self._time_manager,
                                           health,
                                           function_name,
                                           *args,
                                           **kwargs))

        # ------------------------------
        # Event Manager
        # ------------------------------
        health.update(self._call_if_exists(self._event_manager,
                                           health,
                                           function_name,
                                           *args,
                                           **kwargs))

        # ------------------------------
        # Component Manager
        # ------------------------------
        health.update(self._call_if_exists(self._component_manager,
                                           health,
                                           function_name,
                                           *args,
                                           **kwargs))

        # ------------------------------
        # Entity Manager
        # ------------------------------
        health.update(self._call_if_exists(self._entity_manager,
                                           health,
                                           function_name,
                                           *args,
                                           **kwargs))

        # ------------------------------
        # System Manager
        # ------------------------------
        health.update(self._call_if_exists(self._system_manager,
                                           health,
                                           function_name,
                                           *args,
                                           **kwargs))

        # ------------------------------
        # Data Manager
        # ------------------------------
        health.update(self._call_if_exists(self._data_manager,
                                           health,
                                           function_name,
                                           *args,
                                           **kwargs))

        # ------------------------------
        # Identity Manager
        # ------------------------------
        health.update(self._call_if_exists(self._identity_manager,
                                           health,
                                           function_name,
                                           *args,
                                           **kwargs))

        # ---
        # Return Value Manager
        # ---
        return health

    def _each_existing(self) -> VerediHealth:
        '''
        Generator that yields each existing manager.
        '''
        if self._time_manager:
            yield self._time_manager

        if self._event_manager:
            yield self._event_manager

        if self._component_manager:
            yield self._component_manager

        if self._entity_manager:
            yield self._entity_manager

        if self._system_manager:
            yield self._system_manager

        if self._data_manager:
            yield self._data_manager

        if self._identity_manager:
            yield self._identity_manager

        if self._time_manager:
            yield self._time_manager
