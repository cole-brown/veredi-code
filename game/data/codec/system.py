# coding: utf-8

'''
System for Encoding & Decoding data (components?) for the Game.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, Optional, Set, Type


from veredi.logger import log
from veredi.data.config import registry
from veredi.data.codec.base import BaseCodec

# Game / ECS Stuff
from ..ecs.event import EventManager
from ..ecs.time import TimeManager
from ..ecs.component import (ComponentManager,
                             ComponentEvent,
                             ComponentLifeEvent)

from ..ecs.const import (SystemTick,
                         SystemPriority,
                         SystemHealth,
                         DebugFlag)

from ..ecs.base.identity import (ComponentId,
                                 EntityId,
                                 SystemId)
from ..ecs.base.component import (Component,
                                  ComponentError)
from ..ecs.base.system import (System,
                               SystemLifeCycle)

# Events
# Do we need these system events?
from ..ecs.system import (SystemEvent,
                          SystemLifeEvent)
from ..event import (
    # Our events
    DecodedEvent,
    EncodedEvent,
    # Our subscriptions
    DataSaveRequest,
    DeserializedEvent)

# Components
from .component import (
    # Base Classes
    EncoderComponent,
    DecoderComponent)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# §-TODO-§ [2020-05-22]: Saving/Loading system...
# DirtyFlagSystem: looks for a dirty flag, fires off encode events?
#   - or name it DataSaveSystem?
#   - or name it DataSystem?

class CodecSystem:
    def __init__(self,
                 sid: SystemId,
                 *args: Any,
                 **kwargs: Any) -> None:
        super().__init__(sid, *args, **kwargs)

        self._components: Optional[Set[Type[Component]]] = None

        self._ticks: SystemTick = (SystemTick.SET_UP   # Initial loading.
                                   | SystemTick.TIME   # While-in-game loading.
                                   | SystemTick.DEATH) # While-in-game saving.
        # Apoptosis will be our end-of-game saving.

        self._event_manager: Optional[EventManager] = None

        # TODO: Event to ask ConfigSystem what the specific codec is?
        # self._codec: Optional[BaseCodec] = None
        from veredi.data.codec.yaml.codec import YamlCodec
        self._codec: Optional[BaseCodec] = YamlCodec()

    # --------------------------------------------------------------------------
    # System Registration / Definition
    # --------------------------------------------------------------------------

    def priority(self) -> Union[SystemPriority, int]:
        '''
        Returns a SystemPriority (or int) for when, relative to other systems,
        this should run. Highest priority goes firstest.
        '''
        # Probably want HIGH so we can load new things ASAP in the ticks.
        return SystemPriority.HIGH

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

        # Codec subs to:
        # - DeserializedEvent
        #   Deserialized Data needs to be decoded so it can be used in game.
        #   - Codec creates a DecodedEvent once it has done this.
        self.event_mgr.subscribe(DeserializedEvent,
                                 self.event_deserialized)

        # Codec subs to:
        # - DataSaveRequest
        #   Data needs to be encoded before it can be saved.
        #   - Codec creates an EncodedEvent once it has done this.
        self.event_mgr.subscribe(DataSaveRequest,
                                 self.event_data_save_request)

        return self._health()

    def event_deserialized(self, event: DeserializedEvent) -> None:
        '''
        Data has been deserialized. We must decode it and pass it along.
        '''
        # §-TODO-§ [2020-05-22]: Decode it.

        # Get data from event

        # Send into my codec

        # Take codec data result (just a python dict?)

        # Set result into DecodedEvent data/context/whatever.

        # Done; fire off event for whoever wants the next step.
        self.event(self._event_manager,
                   DecodedEvent,
                   event.id,
                   event.type,
                   # TODO: Our own context? Merge contexts?
                   event.context)

    def event_data_save_request(self, event: DataSaveRequest) -> None:
        '''
        Data wants saved. It must be encoded first.
        '''
        # §-TODO-§ [2020-05-22]: Encode it.

        # Done; fire off event for whoever wants the next step.
        self.event(self._event_manager,
                   EncodedEvent,
                   event.id,
                   event.type,
                   # TODO: Our own context? Merge contexts?
                   event.context)

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
