# coding: utf-8

'''
System for Encoding & Decoding data (components?) for the Game.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, Optional, Set, Type, Union, Iterable


from veredi.logger import log
from veredi.base.const import VerediHealth
from veredi.base.context import VerediContext
from veredi.data.config.config import Configuration
from veredi.data.config.context import ConfigContext
from veredi.data.repository.base import BaseRepository

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

class RepositorySystem(System):

    def _configure(self, context: VerediContext) -> None:
        '''
        Make our repo from config data.
        '''
        self._repository = None

        # ---
        # Health Stuff
        # ---
        self._required_managers:    Optional[Set[Type[EcsManager]]] = {
            TimeManager,
            EventManager
        }
        self._health_meter_event:   Optional[Decimal] = None

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
        if context:
            config = ConfigContext.config(context)
            if config:
                self._repository = config.make(None,
                                               'data',
                                               'game',
                                               'repository',
                                               'type')

        # §-TODO-§ [2020-05-30]: remove this - set up unit/integration/whatever
        # tests with our test configs.
        if not self._repository:
            # §-TODO-§: Event to ask ConfigSystem what the specific repository is?
            # Maybe that's what we need a SET_UP tick for?
            # self._repository: Optional[BaseRepository] = None
            from veredi.data.repository.file import FileTreeRepository
            self._repository = FileTreeRepository(kwargs.get('repository_base',
                                                             None))

    def priority(self) -> Union[SystemPriority, int]:
        '''
        Returns a SystemPriority (or int) for when, relative to other systems,
        this should run. Highest priority goes firstest.
        '''
        return SystemPriority.DATA_REPO

    # --------------------------------------------------------------------------
    # Events
    # --------------------------------------------------------------------------

    def subscribe(self, event_manager: 'EventManager') -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        super().subscribe(event_manager)

        # Repository subs to:
        # - DataLoadRequest
        #   The data needs to be fetched and deserialized.
        #   - Repository creates a DeserializedEvent once it has done this.
        self._manager.event.subscribe(DataLoadRequest,
                                      self.event_data_load_request)

        # Repository subs to:
        # - EncodedEvent
        #   Once data is encoded, it needs to be serialized to repo.
        #   - Repository creates an SerializedEvent once it has done this.
        self._manager.event.subscribe(EncodedEvent,
                                      self.event_encoded)

        return self._health_check()

    def event_data_load_request(self, event: DataLoadRequest) -> None:
        '''
        Request for data to be loaded. We must ask the repo for it and pack it
        into a DeserializedEvent.
        '''
        # Doctor checkup.
        if not self._healthy():
            self._health_meter_event = self._health_log(
                self._health_meter_event,
                log.Level.WARNING,
                "HEALTH({}): Dropping event {} - our system health "
                "isn't good enough to process.",
                self.health, event,
                context=event.context)
            return

        context = self._repository.context.push(event.context)

        # Ask my repository for this data.
        # Load data info is in the request context.
        deserialized = self._repository.load(context)
        # Get back deserialized data stream.

        # Take our repository load result and set into DeserializedEvent.
        # Then have EventManager fire off event for whoever wants the next step.
        event = DeserializedEvent(event.id, event.type, context,
                                  data=deserialized)

        self._event_notify(event,
                           False)

    def event_encoded(self, event: EncodedEvent) -> None:
        '''
        Data is encoded and now must be saved.
        '''
        # Doctor checkup.
        if not self._healthy():
            self._health_meter_event = self._health_log(
                self._health_meter_event,
                log.Level.WARNING,
                "HEALTH({}): Dropping event {} - our system health "
                "isn't good enough to process.",
                self.health, event,
                context=event.context)
            return

        context = self._repository.context.push(event.context)

        # §-TODO-§ [2020-05-22]: Encode it.
        raise NotImplementedError
        serialized = None

        # Done; fire off event for whoever wants the next step.
        event = SerializedEvent(event.id, event.type, context,
                                data=serialized)

        self._event_notify(event,
                           False)
