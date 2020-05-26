# coding: utf-8

'''
System for Encoding & Decoding data (components?) for the Game.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, Optional, Set, Type, Union, Iterable


from veredi.logger import log
from veredi.data.config import registry
from veredi.data.repository.base import BaseRepository

# Game / ECS Stuff
from ...ecs.event import EventManager
from ...ecs.time import TimeManager

from ...ecs.const import (SystemTick,
                          SystemPriority,
                          SystemHealth,
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
    SerializedEvent,
    DeserializedEvent,
    # Our subscriptions
    EncodedEvent,
    DataLoadRequest)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# Â§-TODO-Â§ [2020-05-22]: Saving/Loading system...
# DirtyFlagSystem: looks for a dirty flag, fires off encode events?
#   - or name it DataSaveSystem?
#   - or name it DataSystem?

class RepositorySystem(System):
    def __init__(self,
                 sid: SystemId,
                 *args: Any,
                 **kwargs: Any) -> None:
        super().__init__(sid, *args, **kwargs)

        # ---
        # Ticking Stuff
        # Don't think I need any, actually. Think we're entirely event-driven.
        # ---
        # self._components: Optional[Set[Type[Component]]] = None
        # self._ticks: SystemTick = (SystemTick.SET_UP         # Initial loading.
        #                            | SystemTick.TIME         # In-game loading.
        #                            | SystemTick.DESTRUCTION) # In-game saving.
        # # Apoptosis will be our end-of-game saving.
        # ---

        self._event_manager: Optional[EventManager] = None

        # TODO: Event to ask ConfigSystem what the specific repository is?
        # Maybe that's what we need a SET_UP tick for?
        # self._repository: Optional[BaseRepository] = None
        from veredi.data.repository.file import FileTreeRepository
        self._repository = FileTreeRepository(kwargs.get('repository_base',
                                                         None))

    # --------------------------------------------------------------------------
    # System Registration / Definition
    # --------------------------------------------------------------------------

    def priority(self) -> Union[SystemPriority, int]:
        '''
        Returns a SystemPriority (or int) for when, relative to other systems,
        this should run. Highest priority goes firstest.
        '''
        # Probably want HIGH so we can load new things ASAP in the ticks. HIGH +
        # 1 (currently) puts us ahead of the CodecSystem, if we do start using
        # ticks.
        # ...though we want to be behind the CodecSystem during saves... Hmm.
        return SystemPriority.HIGH + 1

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

    def apoptosis(self, time: 'TimeManager') -> SystemHealth:
        '''
        Game is ending gracefully. Do graceful end-of-the-world stuff...
        '''
        return SystemHealth.APOPTOSIS

    def _health(self, current_health=SystemHealth.HEALTHY):
        if self._event_manager is False:
            # We rely on events to function, so we're bad if it doesn't exist.
            return SystemHealth.UNHEALTHY
        if not self._event_manager:
            # We rely on EventManager to function, and we don't have it, but we
            # haven't confirmed it doesn't exist yet...
            return SystemHealth.PENDING

        return current_health

    # --------------------------------------------------------------------------
    # Events
    # --------------------------------------------------------------------------

    def subscribe(self, event_manager: 'EventManager') -> SystemHealth:
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
        # - DataLoadRequest
        #   The data needs to be fetched and deserialized.
        #   - Repository creates a DeserializedEvent once it has done this.
        self._event_manager.subscribe(DataLoadRequest,
                                      self.event_data_load_request)

        # Repository subs to:
        # - EncodedEvent
        #   Once data is encoded, it needs to be serialized to repo.
        #   - Repository creates an SerializedEvent once it has done this.
        self._event_manager.subscribe(EncodedEvent,
                                      self.event_encoded)

        return self._health()

    def event_data_load_request(self, event: DataLoadRequest) -> None:
        '''
        Request for data to be loaded. We must ask the repo for it and pack it
        into a DeserializedEvent.
        '''
        context = self._repository.context.merge(event.context)

        # Ask my repository for this data.
        # Load data info is in the request context.
        deserialized = self._repository.load(context)
        # Get back deserialized data stream.

        # Take our repository load result and set into DeserializedEvent.
        # Then have EventManager fire off event for whoever wants the next step.
        self.event(self._event_manager,
                   DeserializedEvent,
                   event.id,
                   event.type,
                   context,
                   False,
                   data=deserialized)

    def event_encoded(self, event: EncodedEvent) -> None:
        '''
        Data is encoded and now must be saved.
        '''
        context = self._repository.context.merge(event.context)

        # Â§-TODO-Â§ [2020-05-22]: Encode it.
        raise NotImplementedError
        serialized = None

        # Done; fire off event for whoever wants the next step.
        self.event(self._event_manager,
                   SerializedEvent,
                   event.id,
                   event.type,
                   context,
                   False,
                   data=serialized)

    # --------------------------------------------------------------------------
    # Game Update Loop/Tick Functions
    # --------------------------------------------------------------------------

    def update_set_up(self,
                      time_mgr:      'TimeManager',
                      component_mgr: 'ComponentManager',
                      entity_mgr:    'EntityManager') -> SystemHealth:
        '''
        Proceeds the normal loop. A loop just to wait until all systems say
        they're done getting set up and are ready for the main game loop.
        '''
        return self._health()

    def update_time(self,
                    time_mgr:      'TimeManager',
                    component_mgr: 'ComponentManager',
                    entity_mgr:    'EntityManager') -> SystemHealth:
        '''
        First in Game update loop. Systems should use this rarely as the game
        time clock itself updates in this part of the loop.
        '''
        return self._health()

    def update_destruction(self,
                           time_mgr:      'TimeManager',
                           component_mgr: 'ComponentManager',
                           entity_mgr:    'EntityManager') -> SystemHealth:
        '''
        Final upate. Death/deletion part of life cycles managed here.
        '''
        return self._health()
