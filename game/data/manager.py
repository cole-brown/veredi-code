# coding: utf-8

'''
Data Manager for the Game. This is always the data manager. It manages data
of various types from various sources by getting a repository and a serdes
(serializer/deserializer) from the Configuration.

Handles:
  - load/save requests
  - loading/unloading data in components
  - loading/holding/saving game (meta, saved, etc) data.

That is, it is the start and end point of loads and saves. As well as the place
to go for accessing Game Config/Save (as opposed to Entity/Component) data.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, Set, Type, Mapping
from veredi.base.null import NullNoneOr


from decimal import Decimal


# ---
# Veredi Stuff
# ---
from veredi.logger               import log

from veredi.base                 import label
from veredi.base.const           import VerediHealth
from veredi.base.exceptions      import VerediError
from veredi.base.context         import VerediContext

from veredi.debug.const          import DebugFlag

from veredi.data                 import background
from veredi.data.config.config   import Configuration
from veredi.data.repository.base import BaseRepository
from veredi.data.serdes.base     import BaseSerdes


# ---
# Game / ECS Stuff
# ---
from ..ecs.event                 import (EventManager,
                                         EcsManagerWithEvents,
                                         Event)
from ..ecs.time                  import TimeManager
from ..ecs.component             import ComponentManager

from ..ecs.const                 import SystemTick
from ..ecs.exceptions            import EventError, EcsManagerError

from ..ecs.base.identity         import ComponentId
from ..ecs.base.component        import Component

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

class DataManager(EcsManagerWithEvents):

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self):
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        super()._define_vars()

        # ------------------------------
        # Data Handlers
        # ------------------------------

        self._serdes: Optional[BaseSerdes] = None
        '''
        Our Serializer/Deserializer for saving/loading data.
        '''

        self._repository: Optional[BaseRepository] = None
        '''
        Our Repository for storing data.
        '''

        # ------------------------------
        # Health
        # ------------------------------

        self._health_meter_event:   Optional['Decimal'] = None
        '''
        Store timing information for our timed/metered 'system isn't healthy'
        messages that fire off during event things.
        '''

        self._health_meter_update:  Optional['Decimal'] = None
        '''
        Stores timing information for our timed/metered 'system isn't healthy'
        messages that fire off during system tick things.
        '''

        # ------------------------------
        # Ticking
        # ------------------------------

        # Experimental: Keep data processing out of the standard tick?
        # Just let everyone else go at it.

        self._ticks: Optional[SystemTick] = (SystemTick.TICKS_RUN
                                             & ~SystemTick.STANDARD)
        '''
        The ticks we desire to run in.

        Systems will always get the TICKS_START and TICKS_END ticks. The
        default _cycle_<tick> and _update_<tick> for those ticks should be
        acceptable if the system doesn't care.
        '''

        # Apoptosis will be our end-of-game saving.

        self._components_req: Optional[Set[Type['Component']]] = [
            DataComponent
        ]
        '''
        The components we /absolutely require/ to function.
        '''

        # ------------------------------
        # Required Other Managers
        # ------------------------------
        # Also require EventManager, but that's defined in
        # EcsManagerWithEvents._define_vars().

        self._time: TimeManager = None
        '''
        The ECS Time Manager.
        '''

        self._component: ComponentManager = None
        '''
        The ECS Component Manager.
        '''

        # ------------------------------
        # Unit Testing
        # ------------------------------

        self._ut_all_events_external: bool = False
        '''
        Subscribe to all our events (requests and internals), not just the
        requests (DataLoadRequest and DataSaveRequest).

        Also publish all our events instead of handling the internals
        internally.
        '''

    def __init__(self,
                 config:            Optional[Configuration],
                 time_manager:      TimeManager,
                 event_manager:     EventManager,
                 component_manager: ComponentManager,
                 debug_flags:       NullNoneOr[DebugFlag]) -> None:
        '''
        Make our stuff from context/config data.
        '''
        super().__init__(debug_flags)

        # ---
        # Required Other Managers
        # ---
        self._time = time_manager
        self._event = event_manager
        self._component = component_manager

        # ---
        # Config Stuff
        # ---
        key_serdes = ('data', 'serdes')
        key_repo = ('data', 'repository', 'type')
        if config:
            self._serdes = config.make(None, *key_serdes)
            self._repository = config.make(None, *key_repo)

        if not self._serdes:
            context = config.make_config_context()
            msg = ("Could not create Serdes (serializer/Deserializer) from "
                   f"config data: {label.join(key_serdes)} "
                   f"{config.get(key_serdes)}")
            raise background.config.exception(context, msg)
        if not self._repository:
            context = config.make_config_context()
            msg = ("Could not create Repository from "
                   f"config data: {label.join(key_repo)} "
                   f"{config.get(key_repo)}")
            raise background.config.exception(context, msg)

        # ---
        # Background Stuff
        # ---
        bg_data, bg_owner = self._make_background()
        background.data.set(background.Name.SYS,
                            bg_data,
                            bg_owner)
        background.data.link_set(background.data.Link.SERDES,
                                 self._serdes)
        background.data.link_set(background.data.Link.REPO,
                                 self._repository)

    def _make_background(self):
        '''
        Data for the Veredi Background context.

        Returns: (data, background.Ownership)
        '''
        serdes_data, serdes_owner = self._serdes.background
        repo_data, repo_owner = self._repository.background

        return (
            {
                background.Name.DOTTED.key: self.dotted(),
                background.Name.SERDES.key: serdes_data,
                background.Name.REPO.key:   repo_data,
            },
            background.Ownership.SHARE
        )

    @classmethod
    def dotted(klass: 'DataManager') -> str:
        return 'veredi.game.data.manager'

    # -------------------------------------------------------------------------
    # Health
    # -------------------------------------------------------------------------

    def _health_log(self,
                    log_meter: 'Decimal',
                    log_level: log.Level,
                    msg:       str,
                    *args:     Any,
                    **kwargs:  Any):
        '''
        Do a metered health log if meter allows. Will log out at `log_level`.

        WARNING is a good default. Not using an optional param so args/kwargs
        are more explicitly separated.
        '''
        output_log, maybe_updated_meter = self._time.metered(log_meter)
        if output_log:
            kwargs = self._log_stack(**kwargs)
            self._log_at_level(
                log_level,
                f"HEALTH({self.health}): " + msg,
                args, kwargs)
        return maybe_updated_meter

    def _health_ok_event(self,
                         event: 'Event') -> bool:
        '''
        Check health, log if needed, and return True if able to proceed.
        '''
        if self._healthy(self._time.engine_tick_current):
            return True

        # Unhealthy? Log (maybe) and return False.
        meter = self._health_meter_event
        output_log, meter = self.time.metered(meter)
        self._health_meter_event = meter
        if output_log:
            msg = ("Dropping event {} - DataManager's health "
                   "isn't good enough to process.")
            kwargs = self._log_stack(None)
            self._health_meter_event = self._health_log(
                self._health_meter_event,
                log.Level.WARNING,
                msg,
                event,
                context=event.context,
                **kwargs)
        return False

    def _health_ok_tick(self,
                        tick: 'SystemTick',
                        context:  NullNoneOr['VerediContext'] = None) -> bool:
        '''
        Check health, log if needed, and return True if able to proceed.
        '''
        if self._healthy(tick):
            return True

        # Unhealthy? Log (maybe) and return False.
        msg = ("Skipping tick {} - DataManager's health "
               "isn't good enough to process.")
        kwargs = self._log_stack(None)
        self._health_meter_update = self._health_log(
            self._health_meter_update,
            log.Level.WARNING,
            msg,
            tick,
            context=context,
            **kwargs)
        return False

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def subscribe(self, event_manager: EventManager) -> VerediHealth:
        '''
        Subscribe to DataManager's events.

        In the general case, only DataLoadRequest and DataSaveRequest will be
        subscribed to, but tests and such may do something special and trigger
        intermediate/internal events, so we are able to subscribe to all if set
        up to.
        '''
        super().subscribe(event_manager)

        # ------------------------------
        # External/Expected: Request for Load / Save
        # ------------------------------

        # - DataLoadRequest
        #   The data needs to be fetched and loaded.
        #   - Repository creates a _LoadedEvent once it has done this.
        self._event.subscribe(DataLoadRequest,
                              self._event_data_load_request)

        # - DataSaveRequest
        #   Data needs to be serialized before it can be saved.
        #   - Serdes creates an _SerializedEvent once it has done this.
        self._event.subscribe(DataSaveRequest,
                              self._event_data_save_request)

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
        self._event.subscribe(_DeserializedEvent,
                              self._event_deserialized)

        # - _SerializedEvent
        #   Once data is serialized, it needs to be saved to repo.
        #   - Repository creates an _SavedEvent once it has done this.
        self._event.subscribe(_SerializedEvent,
                              self._event_serialized)

        # ------------------------------
        # Internal: Load / Save from Repository
        # ------------------------------

        # - _SavedEvent
        #   Once data is saved to repo, we want to say it's been saved.
        #   - We'll creates a DataSavedEvent to do this.
        self._event.subscribe(_SavedEvent,
                              self._event_saved)

        # - _LoadedEvent
        #   Loaded Data needs to be deserialized so it can be used in game.
        #   - Serdes creates a _DeserializedEvent once it has done this.
        self._event.subscribe(_LoadedEvent,
                              self._event_loaded)

        return VerediHealth.HEALTHY

    # -------------------------------------------------------------------------
    # Events: Request for Load / Save
    # -------------------------------------------------------------------------

    def _event_data_load_request(self, event: DataLoadRequest) -> None:
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

        # Take our repository load result and set into _LoadedEvent. Then
        # have EventManager fire off event for whoever wants the next step.
        event = _LoadedEvent(event.id, event.type, context,
                             data=loaded)

        # Special Shenanigans: Publish this event, wait for it to come back.
        if self._ut_all_events_external:
            self._event_notify(event, False)

        # Normal Case: Pass on to process loaded data
        else:
            self._event_loaded(event)

    def _event_data_save_request(self, event: DataSaveRequest) -> None:
        '''
        Data wants saved. It must be serialized first.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
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
            self._event_notify(event, False)

        # Normal Case: Pass on to process deserialized data.
        else:
            self._event_serialized(event)

    # -------------------------------------------------------------------------
    # Events: Serialize / Deserialize with Serdes
    # -------------------------------------------------------------------------

    def _request_creation(self,
                          document: Mapping[str, Any],
                          event:    _DeserializedEvent) -> ComponentId:
        '''
        Asks ComponentManager to create this document from this event,
        whatever it is.

        Returns created component's ComponentId or ComponentId.INVALID
        '''
        metadata = document.get('meta', None)
        dotted_from_meta =  metadata.get('registry', None)
        if not dotted_from_meta:
            raise log.exception(
                EventError,
                "{} could not create anything from event {}. "
                "args: {}, kwargs: {}, context: {}",
                self.__class__.__name__,
                event, event.context
            )

        # Create this registered component from their 'dotted name'
        # with this data.
        retval = self._component.create(dotted_from_meta,
                                        event.context,
                                        data=document)
        return retval

    def _event_deserialized(self, event: _DeserializedEvent) -> None:
        '''
        Deserialized data needs to be put into game. Once that's done, trigger
        a DataLoadedEvent.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
            return

        # Check metadata document?
        #   - Use version to get correct component class?
        #   - Or not... just use each component's meta.registry?

        # Walk list of data... try to figure out which ones we should
        # try to create.
        cid = ComponentId.INVALID
        for document in event.data:
            try:
                if 'record-type' in document:
                    log.debug("Processing event {}, rec: {}, document: {}.",
                              event,
                              document['record-type'],
                              document['doc-type'])
                else:
                    log.debug("Processing event {}, rec: {}, document: {}.",
                              event,
                              None,
                              document['doc-type'])
                if ('doc-type' in document
                        and document['doc-type'] == 'component'):
                    log.debug("Found component; requesting creation.")
                    cid = self._request_creation(document, event)

            except EventError:
                # self._request_creation() failed - bubble up.
                raise

            except VerediError as error:
                # Chain/wrap in a EcsManagerError.
                raise log.exception(
                    EcsManagerError,
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
                self._event_notify(event, False)

    def _event_serialized(self, event: _SerializedEvent) -> None:
        '''
        Data is serialized and now must be saved.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
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
            self._event_notify(event, False)

        # Normal Case: Pass on to process saved data.
        else:
            self._event_saved(event)

    # -------------------------------------------------------------------------
    # Events: Load / Save from Repository
    # -------------------------------------------------------------------------

    def _event_saved(self, event: _SavedEvent) -> None:
        '''
        Data is saved. Now we can trigger DataSavedEvent.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
            return

        self._log_warning(f"{self.__class__.__name__}.event_saved() "
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
        # self._event_notify(event, False)

    def _event_loaded(self, event: _LoadedEvent) -> None:
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
            self._event_notify(event, False)

        # Normal Case: Pass on to process deserialized data.
        else:
            self._event_deserialized(event)

    # -------------------------------------------------------------------------
    # Game Update Loop/Tick Functions
    # -------------------------------------------------------------------------

    def update(self,
               tick: SystemTick) -> VerediHealth:
        '''
        Generic tick function. We do the same thing every tick state we process
        so do it all here.
        '''
        # ------------------------------
        # Short-cuts
        # ------------------------------

        # Ignored Tick?
        if not self._ticks or not self._ticks.has(tick):
            # Don't even care about my health since we don't even want
            # this tick.
            return VerediHealth.HEALTHY

        # Doctor checkup.
        if not self._health_ok_tick(SystemTick.STANDARD):
            return self.health

        # ------------------------------
        # Full Tick Rate: Start
        # ------------------------------
        health = VerediHealth.HEALTHY

        # Doctor checkup.
        if not self._health_ok_tick(tick):
            return self.health.update(health)

        # TODO [2020-12-01]: Make a 'max requests per tick'. Use as the max for
        # both this and events combined?
        #  - But needs to be ignored during start-up/shut-down ticks, probably.
        #  - And we need to not starve out update stuff because there were too
        #    many events or vice versa...

        # TODO [2020-05-26]: Check for queued up stuff due to delays due to
        # large influx of requests.
        #   - Process some if present.

        # Do DataLoadRequest / DataSaveRequest?
        # Or is DataLoadRequest an event we should subscribe to?

        # ------------------------------
        # Full Tick Rate: End
        # - - - - - - - - - - -
        # if not self.time.is_reduced_tick(
        #         tick,
        #         self._reduced_tick_rate):
        #     self.health = health
        #     return self.health
        # - - - - - - - - - - -
        # !! REDUCED Tick Rate: START !!
        # ------------------------------

        return self.health.update(health)
