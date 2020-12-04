# coding: utf-8

'''
General Data System for the Game. Becomes a Specific Data System via config
data.

Contains a repository and a serdes (serializer/deserializer) for handling data.

Handles:
  - load/save requests
  - loading/unloading data in components

That is, it is the start and end point of loads and saves.
'''

# encode -> serialize


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, Set, Type, Union, Mapping

# ---
# Veredi Stuff
# ---
from veredi.logger          import log
from veredi.base import dotted as label
from veredi.base.const      import VerediHealth
from veredi.base.exceptions import VerediError
from veredi.base.context    import VerediContext
from veredi.data            import background

from veredi.data.repository.base import BaseRepository
from veredi.data.serdes.base import BaseSerdes
from veredi.data.codec.encodable import Encodable
from veredi.data.exceptions                    import ConfigError

# ---
# Game / ECS Stuff
# ---
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

# ---
# Data Events
# ---
from .event import (
    # Should be all of them, but call them each out.

    # Requests from Game
    DataLoadRequest,
    DataSaveRequest,

    # Final result
    DataLoadedEvent,
    DataSavedEvent,

    # Interim events for Serdes
    _DeserializedEvent,
    _SerializedEvent,

    # Interim events for Repository
    _LoadedEvent,
    _SavedEvent
)

# Our friendly component.
from .component import DataComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class DataSystem(System):

    def _define_vars(self):
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        super()._define_vars()

        self._ut_all_events_external: bool = False
        '''
        Subscribe to all our events (requests and internals), not just the
        requests (DataLoadRequest and DataSaveRequest).

        Also publish all our events instead of handling the internals
        internally.
        '''

        self._serdes: Optional[BaseSerdes] = None
        '''
        Our Serializer/Deserializer for saving/loading data.
        '''

        self._repository: Optional[BaseRepository] = None
        '''
        Our Repository for storing data.
        '''

    def _configure(self, context: VerediContext) -> None:
        '''
        Make our repo from config data.
        '''

        self._component_type = None
        '''DataSystem doesn't have a required component type.'''

        # ---
        # Health Stuff
        # ---
        self._required_managers:    Optional[Set[Type[EcsManager]]] = {
            TimeManager,
            EventManager,
            ComponentManager
        }

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
        config = background.config.config
        key_serdes = ('data', 'serdes')
        key_repo = ('data', 'repository', 'type')
        if config:
            self._serdes = config.make(None, *key_serdes)
            self._repository = config.make(None, *key_repo)

        if not self._serdes:
            msg = ("Could not create Serdes (serializer/Deserializer) from "
                   f"config data: {label.join(key_serdes)} "
                   f"{config.get(key_serdes)}")
            error = ConfigError(msg, None)
            raise log.exception(error, None, msg)
        if not self._repository:
            msg = ("Could not create Repository from "
                   f"config data: {label.join(key_repo)} "
                   f"{config.get(key_repo)}")
            error = ConfigError(msg, None)
            raise log.exception(error, None, msg)

        # ---
        # Background Stuff
        # ---
        bg_data, bg_owner = self.background
        background.data.set(background.Name.SYS,
                            bg_data,
                            bg_owner)
        background.data.link_set(background.data.Link.SERDES,
                                 self._serdes)
        background.data.link_set(background.data.Link.REPO,
                                 self._repository)

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
        serdes_data, serdes_owner = self._serdes.background
        repo_data, repo_owner = self._repository.background

        return {
            background.Name.DOTTED.key: self.dotted(),
            background.Name.SERDES.key: serdes_data,
            background.Name.REPO.key:   repo_data,
        }

    @classmethod
    def dotted(klass: 'DataSystem') -> str:
        return 'veredi.game.data.system'

    # -------------------------------------------------------------------------
    # System Registration / Definition
    # -------------------------------------------------------------------------

    def priority(self) -> Union[SystemPriority, int]:
        '''
        Returns a SystemPriority (or int) for when, relative to other systems,
        this should run. Highest priority goes firstest.
        '''
        # We have a specific priority to use as the data system.
        return SystemPriority.DATA

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def _subscribe(self) -> VerediHealth:
        '''
        Subscribe to DataSystem's events.

        In the general case, only DataLoadRequest and DataSaveRequest will be
        subscribed to, but tests and such may do something special and trigger
        intermediate/internal events, so we are able to subscribe to all if set
        up to.
        '''

        # ------------------------------
        # External/Expected: Request for Load / Save
        # ------------------------------

        # - DataLoadRequest
        #   The data needs to be fetched and loaded.
        #   - Repository creates a _LoadedEvent once it has done this.
        self._manager.event.subscribe(DataLoadRequest,
                                      self.event_data_load_request)

        # - DataSaveRequest
        #   Data needs to be serialized before it can be saved.
        #   - Serdes creates an _SerializedEvent once it has done this.
        self._manager.event.subscribe(DataSaveRequest,
                                      self.event_data_save_request)

        # ------------------------------
        # Normal Path: Done
        # ------------------------------
        if not self._ut_all_events_external:
            return VerediHealth.HEALTHY
        # Unit Testing? Subscribe to the internal events too.

        # ------------------------------
        # Internal: Serialize / Deserialize with Serdes
        # ------------------------------

        # - _DeserializedEvent
        #   The data has been interpreted into Python/Veredi. Now it needs to
        #   be stuffed into a component or something and attached to an entity
        #   or something.
        #   - We create a DataLoadedEvent once this is done.
        self._manager.event.subscribe(_DeserializedEvent,
                                      self.event_deserialized)

        # - _SerializedEvent
        #   Once data is serialized, it needs to be saved to repo.
        #   - Repository creates an _SavedEvent once it has done this.
        self._manager.event.subscribe(_SerializedEvent,
                                      self.event_serialized)

        # ------------------------------
        # Internal: Load / Save from Repository
        # ------------------------------

        # - _SavedEvent
        #   Once data is saved to repo, we want to say it's been saved.
        #   - We'll creates a DataSavedEvent to do this.
        self._manager.event.subscribe(_SavedEvent,
                                      self.event_saved)

        # - _LoadedEvent
        #   Loaded Data needs to be deserialized so it can be used in game.
        #   - Serdes creates a _DeserializedEvent once it has done this.
        self._manager.event.subscribe(_LoadedEvent,
                                      self.event_loaded)

        return VerediHealth.HEALTHY

    # -------------------------------------------------------------------------
    # Events: Request for Load / Save
    # -------------------------------------------------------------------------

    def event_data_load_request(self, event: DataLoadRequest) -> None:
        '''
        Request for data to be loaded. We must ask the repo for it and pack it
        into a _LoadedEvent.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
            return

        context = event.context

        # Ask my repository for this data.
        # Load data info is in the request context.
        loaded = self._repository.load(context)
        # Get back loaded data stream.

        # print("\nloaded:")
        # print(loaded.read(None))
        # print("\n")

        # Take our repository load result and set into _LoadedEvent. Then
        # have EventManager fire off event for whoever wants the next step.
        event = _LoadedEvent(event.id, event.type, context,
                             data=loaded)

        # Special Shenanigans: Publish this event, wait for it to come back.
        if self._ut_all_events_external:
            self._event_notify(event,
                               False)

        # Normal Case: Pass on to process loaded data
        else:
            self.event_loaded(event)

    def event_data_save_request(self, event: DataSaveRequest) -> None:
        '''
        Data wants saved. It must be serialized first.
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

        # TODO [2020-05-22]: Serialize it...
        raise NotImplementedError(
            f"{self.__class__.__name__}.event_data_save_request() "
            "is not yet implemented...")

        serialized = None

        # Done; fire off event for whoever wants the next step.
        event = _SerializedEvent(event.id,
                                 event.type,
                                 context,
                                 data=serialized)

        # Special Shenanigans: Publish this event, wait for it to come back.
        if self._ut_all_events_external:
            self._event_notify(event,
                               False)

        # Normal Case: Pass on to process deserialized data.
        else:
            self.event_serialized(event)

    # -------------------------------------------------------------------------
    # Events: Serialize / Deserialize with Serdes
    # -------------------------------------------------------------------------

    def request_creation(self,
                         doc: Mapping[str, Any],
                         event: _DeserializedEvent) -> ComponentId:
        '''
        Asks ComponentManager to create this doc from this event,
        whatever it is.

        Returns created component's ComponentId or ComponentId.INVALID
        '''
        metadata = doc.get('meta', None)
        dotted_from_meta =  metadata.get('registry', None)
        if not dotted_from_meta:
            raise log.exception(
                None,
                SystemErrorV,
                "{} could not create anything from event {}. "
                "args: {}, kwargs: {}, context: {}",
                self.__class__.__name__,
                event, event.context
            )

        # Create this registered component from their 'dotted name'
        # with this data.
        retval = self._manager.component.create(dotted_from_meta,
                                                event.context,
                                                data=doc)
        return retval

    def event_deserialized(self, event: _DeserializedEvent) -> None:
        '''
        Deserialized data needs to be put into game. Once that's done, trigger
        a DataLoadedEvent.
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

    def event_serialized(self, event: _SerializedEvent) -> None:
        '''
        Data is serialized and now must be saved.
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

        context = self._repository.context.push(event.context)

        # TODO [2020-05-22]: Save it.
        raise NotImplementedError(
            f"{self.__class__.__name__}.event_serialized() "
            "is not yet implemented.")
        serialized = None

        # ---
        # Done; fire off event for whoever wants the next step.
        # ---
        event = _SavedEvent(event.id, event.type, context,
                            data=serialized)

        # Special Shenanigans: Publish this event, wait for it to come back.
        if self._ut_all_events_external:
            self._event_notify(event,
                               False)

        # Normal Case: Pass on to process saved data.
        else:
            self.event_saved(event)

    # -------------------------------------------------------------------------
    # Events: Load / Save from Repository
    # -------------------------------------------------------------------------

    def event_saved(self, event: _SavedEvent) -> None:
        '''
        Data is saved. Now we can trigger DataSavedEvent.
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

        self._log.warning(f"{self.__class__.__name__}.event_saved() "
                          "is not really implemented... ignoring event: {}",
                          event)

        # TODO: Clear out any dirty or save flag?

        # TODO: Do DataSavedEvent to alert whoever asked for the save that
        # it's done now?

        # context = self._repository.context.push(event.context)
        #
        # # TODO [2020-05-22]: Serialize it.
        # raise NotImplementedError(
        #     f"{self.__class__.__name__}.event_saved() "
        #     "is not implemented.")
        # saved = None
        #
        # # Done; fire off event for whoever wants the next step.
        # event = DataSavedEvent(event.id, event.type, event.context,
        #                         component_id=cid)
        # self._event_notify(event)

    def event_loaded(self, event: _LoadedEvent) -> None:
        '''
        Data has been loaded. We must deserialize it and pass it along.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
            return

        # Get loaded data stream from event.
        loaded = event.data(seek_to=0)
        context = event.context

        # Send into my serdes for decoding.
        deserialized = self._serdes.deserialize_all(loaded, context)

        # Take serdes data result (just a python dict?) and set into
        # _DeserializedEvent data/context/whatever. Then have EventManager fire
        # off event for whoever wants the next step.
        event = _DeserializedEvent(event.id,
                                   event.type,
                                   context,
                                   data=deserialized)

        # Special Shenanigans: Publish this event, wait for it to come back.
        if self._ut_all_events_external:
            self._event_notify(event,
                               False)

        # Normal Case: Pass on to process deserialized data.
        else:
            self.event_deserialized(event)

    # -------------------------------------------------------------------------
    # Game Update Loop/Tick Functions
    # -------------------------------------------------------------------------

    def update_tick(self,
                    tick: SystemTick) -> VerediHealth:
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

        # TODO [2020-12-01]: Change this to happen on a specific tick, not
        # every tick.

        # TODO [2020-12-01]: Make a 'max requests per tick'. Use as the max for
        # both this and events combined?
        #  - But needs to be ignored during start-up/shut-down ticks, probably.

        # TODO [2020-05-26]: Check for queued up stuff due to delays due to
        # large influx of requests.
        #   - Process some if present.

        # Do DataLoadRequest / DataSaveRequest?
        # Or is DataLoadRequest an event we should subscribe to?

        return self._health_check(tick)
