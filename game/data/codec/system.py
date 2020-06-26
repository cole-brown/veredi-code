# coding: utf-8

'''
System for Encoding & Decoding data (components?) for the Game.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Set, Type, Union
from decimal import Decimal

from veredi.logger import log
from veredi.data import background
from veredi.base.const import VerediHealth
from veredi.base.context import VerediContext
from veredi.data.codec.base import BaseCodec

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

class CodecSystem(System):

    # -------------------------------------------------------------------------
    # System Set Up
    # -------------------------------------------------------------------------

    def _configure(self, context: VerediContext) -> None:
        '''
        Make our repo from config data.
        '''
        self._codec: Optional[BaseCodec] = None

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
            self._codec = config.make(None,
                                      'data',
                                      'codec')

        bg_data, bg_owner = self._codec.background
        background.data.set(background.Name.CODEC,
                            bg_data,
                            bg_owner)
        background.data.link_set(background.data.Link.CODEC,
                                 self._codec)

    @property
    def name(self) -> str:
        '''
        The 'dotted string' name this system has. Probably what they used to
        register.
        '''
        return 'veredi.game.data.codec.system'

    def priority(self) -> Union[SystemPriority, int]:
        '''
        Returns a SystemPriority (or int) for when, relative to other systems,
        this should run. Highest priority goes firstest.
        '''
        return SystemPriority.DATA_CODEC

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def subscribe(self, event_manager: 'EventManager') -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        super().subscribe(event_manager)

        # Codec subs to:
        # - DeserializedEvent
        #   Deserialized Data needs to be decoded so it can be used in game.
        #   - Codec creates a DecodedEvent once it has done this.
        self._manager.event.subscribe(DeserializedEvent,
                                      self.event_deserialized)

        # Codec subs to:
        # - DataSaveRequest
        #   Data needs to be encoded before it can be saved.
        #   - Codec creates an EncodedEvent once it has done this.
        self._manager.event.subscribe(DataSaveRequest,
                                      self.event_data_save_request)

        return self._health_check()

    def event_deserialized(self, event: DeserializedEvent) -> None:
        '''
        Data has been deserialized. We must decode it and pass it along.
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

        # Get deserialized data stream from event.
        serial = event.data
        context = event.context

        # Send into my codec for decoding.
        decoded = self._codec.decode_all(serial, context)

        # Take codec data result (just a python dict?) and set into
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
        if not self._healthy():
            self._health_meter_event = self._health_log(
                self._health_meter_event,
                log.Level.WARNING,
                "HEALTH({}): Dropping event {} - our system health "
                "isn't good enough to process.",
                self.health, event,
                context=event.context)
            return

        context = self._codec.context.push(event.context)

        # TODO [2020-05-22]: Encode it.
        raise NotImplementedError
        encoded = None

        # Done; fire off event for whoever wants the next step.
        event = EncodedEvent(event.id,
                             event.type,
                             context,
                             data=encoded)

        self._event_notify(event,
                           False)
