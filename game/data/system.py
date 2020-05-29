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

from typing import Any, Optional, Set, Type, Union, Iterable, Mapping


from veredi.logger import log
from veredi.base.const import VerediHealth
from veredi.base.exceptions import VerediError

# Game / ECS Stuff
from ..ecs.event import EventManager
from ..ecs.time import TimeManager
from ..ecs.component import ComponentManager

from ..ecs.const import (SystemTick,
                         SystemPriority,
                         DebugFlag)

from ..ecs.base.identity import (ComponentId,
                                 EntityId,
                                 SystemId)
from ..ecs.base.system import (System,
                               SystemLifeCycle,
                               SystemError)
from ..ecs.base.component import Component

# Events
# Do we need these system events?
from ..ecs.system import (SystemEvent,
                          SystemLifeEvent)
from .event import (
    # Our events
    DataLoadRequest,
    DataSaveRequest,
    DataLoadedEvent,
    DataSavedEvent,
    # Our subscriptions
    DecodedEvent,
    SerializedEvent)

# Our friendly component.
from .component import DataComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class DataSystem(System):
    def __init__(self,
                 sid:               SystemId,
                 *args:             Any,
                 **kwargs:          Any) -> None:
        super().__init__(sid, *args, **kwargs)

        # ---
        # Ticking Stuff
        # ---
        self._components: Optional[Set[Type[Component]]] = [DataComponent]
        # Experimental: Keep data processing out of the standard tick?
        self._ticks: SystemTick = (SystemTick.ALL & ~SystemTick.STANDARD)
        # Apoptosis will be our end-of-game saving.
        # ---

    # --------------------------------------------------------------------------
    # System Registration / Definition
    # --------------------------------------------------------------------------

    def priority(self) -> Union[SystemPriority, int]:
        '''
        Returns a SystemPriority (or int) for when, relative to other systems,
        this should run. Highest priority goes firstest.
        '''
        return SystemPriority.DATA_REQ

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

        # DataSystem subs to:
        # - DecodedEvent
        #   The data has been interpreted into Python/Veredi. Now it needs to be
        #   stuffed into a component or something and attached to an entity or
        #   something.
        #   - We create a DataLoadedEvent once this is done.
        self._event_manager.subscribe(DecodedEvent,
                                      self.event_decoded)

        # DataSystem subs to:
        # - SerializedEvent
        #   Once data is serialized to repo, we want to say it's been saved.
        #   - We'll creates a DataSavedEvent to do this.
        self._event_manager.subscribe(SerializedEvent,
                                      self.event_serialized)

        return self._health()

    def request_creation(self,
                         doc: Mapping[str, Any],
                         event: DecodedEvent) -> ComponentId:
        '''
        Asks ComponentManager to create this doc from this event,
        whatever it is.

        Returns created component's ComponentId or ComponentId.INVALID
        '''
        leeloo_dallas = doc.get('meta', None)
        multipass =  leeloo_dallas.get('registry', None)
        if not multipass:
            raise log.exception(
                None,
                SystemError,
                "{} could not create anything from event {}. "
                "args: {}, kwargs: {}, context: {}",
                self.__class__.__name__,
                event, context
            ) from error

        # Create this registered component from their "multipass" with this data.
        retval = self._component_manager.create(multipass,
                                                event.context,
                                                data=doc)
        return retval

    def event_decoded(self, event: DecodedEvent) -> None:
        '''
        Decoded data needs to be put into game. Once that's done, trigger a
        DataLoadedEvent.
        '''
        if not self._component_manager:
            raise log.exception(
                None,
                SystemError,
                "{} could not create anything from event {} - it has no "
                "ContextManager. context: {}",
                self.__class__.__name__,
                event, event.context
            )

        # Check metadata doc?
        #   - Use version to get correct component class?
        #   - Or not... just use each component's meta.registry?

        # Walk list of data... try to figure out which ones we should
        # try to create.
        cid = ComponentId.INVALID
        for doc in event.data:
            try:
                if 'doc-type' in doc and doc['doc-type'] == 'component':
                    cid = self.request_creation(doc, event)
            except SystemError:
                # Ignore these - bubble up.
                raise
            except VerediError as error:
                # Chain/wrap in a SystemError.
                raise log.exception(
                    error,
                    SystemError,
                    "{} failed when trying "
                    "to create from data. event: {}, "
                    "context: {}",
                    self.__class__.__name__, event,
                    event.context,
                    context=event.context) from error

            # Ask someone to attach to... something? An entity? Actually, no.
            # That should be in the event itself. We should just pass it along
            # into the DataLoadedEvent.
            #
            # Have EventManager create and fire off event for whoever wants the
            # next step.
            if cid != ComponentId.INVALID:
                self.event(self._event_manager,
                           DataLoadedEvent,
                           # This is who it's for, assuming we've successfully
                           # chained it the whole way through.
                           event.id,
                           event.type,
                           event.context,
                           False,
                           component_id=cid)

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
