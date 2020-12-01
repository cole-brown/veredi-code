# coding: utf-8

'''
System for Encoding & Decoding data (components?) for the Game.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Set, Type, Union)
if TYPE_CHECKING:
    from decimal import Decimal
    from veredi.game.ecs.base.component import Component


from veredi.logger import log
from veredi.data import background
from veredi.base.const import VerediHealth
from veredi.base.context import VerediContext
from veredi.data.serdes.base import BaseSerdes

# Game / ECS Stuff
from ...ecs.manager import EcsManager
from ...ecs.event import EventManager
from ...ecs.time import TimeManager

from ...ecs.const import SystemPriority

from ...ecs.base.system import System

# Events
from ..event import (
    # Our events
    DecodedEvent,
    EncodedEvent,
    # Our subscriptions
    DataSaveRequest,
    DeserializedEvent)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class SerdesSystem(System):

    # -------------------------------------------------------------------------
    # System Set Up
    # -------------------------------------------------------------------------

    def _configure(self, context: VerediContext) -> None:
        '''
        Make our repo from config data.
        '''
        self._serdes: Optional[BaseSerdes] = None

        self._component_type: Type['Component'] = None
        '''DataSystem doesn't have a component type.'''

        # ---
        # Health Stuff
        # ---
        self._health_meter_event:   Optional[Decimal] = None
        self._required_managers:    Optional[Set[Type[EcsManager]]] = {
            TimeManager,
            EventManager
        }

        # ---
        # Ticking Stuff
        # Don't think I need any, actually. Think we're entirely event-driven.
        # Apoptosis will be our end-of-game saving.
        # ---

        config = background.config.config
        if config:
            self._serdes = config.make(None,
                                      'data',
                                      'serdes')

        bg_data, bg_owner = self._serdes.background
        background.data.set(background.Name.SERDES,
                            bg_data,
                            bg_owner)
        background.data.link_set(background.data.Link.SERDES,
                                 self._serdes)

    @classmethod
    def dotted(klass: 'SerdesSystem') -> str:
        return 'veredi.game.data.serdes.system'

    def priority(self) -> Union[SystemPriority, int]:
        '''
        Returns a SystemPriority (or int) for when, relative to other systems,
        this should run. Highest priority goes firstest.
        '''
        return SystemPriority.DATA_SERDES

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def _subscribe(self) -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''

        # Serdes subs to:
        # - DeserializedEvent
        #   Deserialized Data needs to be decoded so it can be used in game.
        #   - Serdes creates a DecodedEvent once it has done this.
        self._manager.event.subscribe(DeserializedEvent,
                                      self.event_deserialized)

        # Serdes subs to:
        # - DataSaveRequest
        #   Data needs to be encoded before it can be saved.
        #   - Serdes creates an EncodedEvent once it has done this.
        self._manager.event.subscribe(DataSaveRequest,
                                      self.event_data_save_request)

        return VerediHealth.HEALTHY

    def event_deserialized(self, event: DeserializedEvent) -> None:
        '''
        Data has been deserialized. We must decode it and pass it along.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
            return

        # Get deserialized data stream from event.
        serial = event.data
        context = event.context

        # Send into my serdes for decoding.
        decoded = self._serdes.deserialize_all(serial, context)

        # Take serdes data result (just a python dict?) and set into
        # DecodedEvent data/context/whatever. Then have EventManager fire off
        # event for whoever wants the next step.
        event = DecodedEvent(event.id,
                             event.type,
                             context,
                             data=decoded)

        self._event_notify(event,
                           False)

    def event_data_save_request(self, event: DataSaveRequest) -> None:
        '''
        Data wants saved. It must be encoded first.
        '''
        # Doctor checkup.
        if not self._healthy(self._manager.time.engine_tick_current):
            self._health_meter_event = self._health_log(
                self._health_meter_event,
                log.Level.WARNING,
                "HEALTH({}): Dropping event {} - our system health "
                "isn't good enough to process.",
                self.health, event,
                context=event.context)
            return

        context = self._serdes.context.push(event.context)

        # TODO [2020-05-22]: Encode it.
        raise NotImplementedError(
            f"{self.__class__.__name__}.event_data_save_request() "
            "is not yet implemented...")

        encoded = None

        # Done; fire off event for whoever wants the next step.
        event = EncodedEvent(event.id,
                             event.type,
                             context,
                             data=encoded)

        self._event_notify(event,
                           False)
