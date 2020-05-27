# coding: utf-8

'''
General Data System for the Game. Handles:
  - initiating load/save requests
  - loading/unloading data in components for codec

That is, it is the start and end point of loads and saves.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, Optional, Set, Type, Union, Iterable


from veredi.logger import log
from veredi.base.const import VerediHealth

# Game / ECS Stuff
from ...ecs.event import EventManager
from ...ecs.time import TimeManager

from ...ecs.const import (SystemTick,
                          SystemPriority,
                          DebugFlag)

from ...ecs.base.identity import (ComponentId,
                                  EntityId,
                                  SystemId)
from ...ecs.base.system import (System,
                                SystemLifeCycle)
from ...ecs.base.component import Component

# Events
# Do we need these system events?
from ...ecs.system import (SystemEvent,
                           SystemLifeEvent)
from ..event import (
    # Our events
    DataLoadRequest,
    DataSaveRequest,
    DataLoadedEvent,
    DataSavedEvent,
    # Our subscriptions
    DecodedEvent,
    SerializedEvent)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class DataSystem(System):
    def __init__(self,
                 sid: SystemId,
                 *args: Any,
                 **kwargs: Any) -> None:
        super().__init__(sid, *args, **kwargs)

        # ---
        # Ticking Stuff
        # ---
        self._components: Optional[Set[Type[Component]]] = [DataComponent]
        # Experimental: Keep data processing out of the standard tick?
        self._ticks: SystemTick = (SystemTick.ALL & ~SystemTick.STANDARD)
        # Apoptosis will be our end-of-game saving.
        # ---

        self._event_manager: Optional[EventManager] = None

    # --------------------------------------------------------------------------
    # System Registration / Definition
    # --------------------------------------------------------------------------

    def priority(self) -> Union[SystemPriority, int]:
        '''
        Returns a SystemPriority (or int) for when, relative to other systems,
        this should run. Highest priority goes firstest.
        '''
        return SystemPriority.DATA_REQ

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

    def _health(self, current_health=VerediHealth.HEALTHY):
        if self._event_manager is False:
            # We rely on events to function, so we're bad if it doesn't exist.
            return VerediHealth.UNHEALTHY
        if not self._event_manager:
            # We rely on EventManager to function, and we don't have it, but we
            # haven't confirmed it doesn't exist yet...
            return VerediHealth.PENDING

        return current_health

    # --------------------------------------------------------------------------
    # Events
    # --------------------------------------------------------------------------

    def subscribe(self, event_manager: 'EventManager') -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        self._event_manager = event_manager
        if not self._event_manager:
            self._event_manager = False
            # We rely on events to function, so we're not any good now...
            return self._health()

        # Repository subs to:
        # - DecodedEvent
        #   The data needs to be stuffed into a component or something and
        #   attached to an entity or something.
        #   - Repository creates a DataLoadedEvent once it has done this.
        self._event_manager.subscribe(DecodedEvent,
                                      self.event_decoded)

        # Repository subs to:
        # - SerializedEvent
        #   Once data is serialized to repo, we want to say it's been saved.
        #   - Repository creates an DataSavedEvent once it has done this.
        self._event_manager.subscribe(SerializedEvent,
                                      self.event_serialized)

        return self._health()

    def event_decoded(self, event: DecodedEvent) -> None:
        '''
        Decoded data needs to be put into game. Once that's done, trigger a
        DataLoadedEvent.
        '''
        pass

        # Check metadata doc?
        #   - Use version to get correct component class?
        #   - Or not... just use each component's meta.registry?

        # For each doc:
        #   if component
        #     check meta.registry
        #     Ask ComponentManager to construct component if registered?
        #       - Verify data maybe?
        #     Ask someone to attach to an entity?
        #
        # Do DecodedEvent.


        # context = self._repository.context.merge(event.context)
        #
        # # Ask my repository for this data.
        # # Load data info is in the request context.
        # deserialized = self._repository.load(context)
        # # Get back deserialized data stream.
        #
        # # Take our repository load result and set into DeserializedEvent.
        # # Then have EventManager fire off event for whoever wants the next step.
        # self.event(self._event_manager,
        #            DeserializedEvent,
        #            event.id,
        #            event.type,
        #            context,
        #            False,
        #            data=deserialized)

    def event_serialized(self, event: SerializedEvent) -> None:
        '''
        Data is serialized. Now we can trigger DataSavedEvent.
        '''
        pass

        # Clear out any dirty or save flag?

        # Do DataSavedEvent to alert whoever asked for the save that
        # it's done now?


        # context = self._repository.context.merge(event.context)
        #
        # # Â§-TODO-Â§ [2020-05-22]: Encode it.
        # raise NotImplementedError
        # serialized = None
        #
        # # Done; fire off event for whoever wants the next step.
        # self.event(self._event_manager,
        #            SerializedEvent,
        #            event.id,
        #            event.type,
        #            context,
        #            False,
        #            data=serialized)

    # --------------------------------------------------------------------------
    # Game Update Loop/Tick Functions
    # --------------------------------------------------------------------------

    def update_tick(self,
                    tick:          SystemTick,
                    time_mgr:      'TimeManager',
                    component_mgr: 'ComponentManager',
                    entity_mgr:    'EntityManager') -> VerediHealth:
        '''
        Generic tick function. We do the same thing every tick state we process
        so do it all here.
        '''
        # §-TODO-§ [2020-05-26]: this

        # Do DataLoadRequest / DataSaveRequest?
        # Or is DataLoadRequest an event we should subscribe to?

        return self._health()
