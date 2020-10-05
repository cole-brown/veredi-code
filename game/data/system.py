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

from typing import Optional, Any, Set, Type, Union, Mapping
from decimal import Decimal

from veredi.logger          import log
from veredi.data            import background
from veredi.base.const      import VerediHealth
from veredi.base.exceptions import VerediError
from veredi.base.context    import VerediContext

# Game / ECS Stuff
from ..ecs.manager          import EcsManager
from ..ecs.event            import EventManager
from ..ecs.time             import TimeManager
from ..ecs.component        import ComponentManager
from ..ecs.entity           import EntityManager

from ..ecs.const            import (SystemTick,
                                    SystemPriority)

from ..ecs.base.identity    import ComponentId
from ..ecs.base.system      import (System,
                                    SystemErrorV)
from ..ecs.base.component   import Component

# Events
# Do we need these system events?
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

    def _configure(self, context: VerediContext) -> None:
        '''
        Make our repo from config data.
        '''

        self._component_type: Type[Component] = None
        '''DataSystem doesn't have a component type.'''

        # ---
        # Health Stuff
        # ---
        self._required_managers:    Optional[Set[Type[EcsManager]]] = {
            TimeManager,
            EventManager,
            ComponentManager
        }
        self._health_meter_update:  Optional[Decimal] = None
        self._health_meter_event:   Optional[Decimal] = None

        # ---
        # Ticking Stuff
        # ---
        self._components: Optional[Set[Type[Component]]] = [DataComponent]
        # Experimental: Keep data processing out of the standard tick?
        self._ticks: SystemTick = (SystemTick.TICKS_RUN & ~SystemTick.STANDARD)
        # Apoptosis will be our end-of-game saving.
        # ---

        # ---
        # Context Stuff
        # ---
        # No context stuff for us.

        bg_data, bg_owner = self.background
        background.data.set(background.Name.DATA_SYS,
                            bg_data,
                            bg_owner)

    @property
    def background(self):
        '''
        Data for the Veredi Background context.

        Returns: (data, background.Ownership)
        '''
        return self._make_background(), background.Ownership.SHARE

    def _make_background(self):
        '''
        Basic background.data info for this service.
        '''
        return {
            'dotted': self.dotted,
        }

    @property
    def dotted(self) -> str:
        return 'veredi.game.data.system'

    # -------------------------------------------------------------------------
    # System Registration / Definition
    # -------------------------------------------------------------------------

    def priority(self) -> Union[SystemPriority, int]:
        '''
        Returns a SystemPriority (or int) for when, relative to other systems,
        this should run. Highest priority goes firstest.
        '''
        return SystemPriority.DATA_REQ

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def _subscribe(self) -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        # DataSystem subs to:
        # - DecodedEvent
        #   The data has been interpreted into Python/Veredi. Now it needs to
        #   be stuffed into a component or something and attached to an entity
        #   or something.
        #   - We create a DataLoadedEvent once this is done.
        self._manager.event.subscribe(DecodedEvent,
                                      self.event_decoded)

        # DataSystem subs to:
        # - SerializedEvent
        #   Once data is serialized to repo, we want to say it's been saved.
        #   - We'll creates a DataSavedEvent to do this.
        self._manager.event.subscribe(SerializedEvent,
                                      self.event_serialized)

        return VerediHealth.HEALTHY

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
                SystemErrorV,
                "{} could not create anything from event {}. "
                "args: {}, kwargs: {}, context: {}",
                self.__class__.__name__,
                event, event.context
            )

        # Create this registered component from their "multipass"
        # with this data.
        retval = self._manager.component.create(multipass,
                                                event.context,
                                                data=doc)
        return retval

    def event_decoded(self, event: DecodedEvent) -> None:
        '''
        Decoded data needs to be put into game. Once that's done, trigger a
        DataLoadedEvent.
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

        # Check metadata doc?
        #   - Use version to get correct component class?
        #   - Or not... just use each component's meta.registry?

        # Walk list of data... try to figure out which ones we should
        # try to create.
        cid = ComponentId.INVALID
        for doc in event.data:
            try:
                if 'record-type' in doc:
                    log.debug("Processing event {}, rec: {}, doc: {}.",
                              event,
                              doc['record-type'],
                              doc['doc-type'])
                else:
                    log.debug("Processing event {}, rec: {}, doc: {}.",
                              event,
                              None,
                              doc['doc-type'])
                if 'doc-type' in doc and doc['doc-type'] == 'component':
                    log.debug("Found component; requesting creation.")
                    cid = self.request_creation(doc, event)
            except SystemErrorV:
                # Ignore these - bubble up.
                raise
            except VerediError as error:
                # Chain/wrap in a SystemErrorV.
                raise log.exception(
                    error,
                    SystemErrorV,
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
                event = DataLoadedEvent(event.id, event.type, event.context,
                                        component_id=cid)
                self._event_notify(event)

    def event_serialized(self, event: SerializedEvent) -> None:
        '''
        Data is serialized. Now we can trigger DataSavedEvent.
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

        pass

        # TODO: Clear out any dirty or save flag?

        # TODO: Do DataSavedEvent to alert whoever asked for the save that
        # it's done now?

        # context = self._repository.context.push(event.context)
        #
        # # §-TODO-§ [2020-05-22]: Encode it.
        # raise NotImplementedError
        # serialized = None
        #
        # # Done; fire off event for whoever wants the next step.
        # event = SerializedEvent(event.id, event.type, event.context,
        #                         component_id=cid)
        # self._event_notify(event)

    # -------------------------------------------------------------------------
    # Game Update Loop/Tick Functions
    # -------------------------------------------------------------------------

    def update_tick(self,
                    tick:          SystemTick,
                    time_mgr:      TimeManager,
                    component_mgr: ComponentManager,
                    entity_mgr:    EntityManager) -> VerediHealth:
        '''
        Generic tick function. We do the same thing every tick state we process
        so do it all here.
        '''
        # Doctor checkup.
        if not self._healthy(tick):
            self._health_meter_update = self._health_log(
                self._health_meter_update,
                log.Level.WARNING,
                "HEALTH({}): Skipping ticks - our system health "
                "isn't good enough to process.",
                self.health)
            return self._health_check(tick)

        # TODO [2020-05-26]: this

        # Do DataLoadRequest / DataSaveRequest?
        # Or is DataLoadRequest an event we should subscribe to?

        return self._health_check(tick)
