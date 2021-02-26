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

from typing import Optional, Any, Set, Type, Mapping, Dict, List
from veredi.base.null import Nullable, NullNoneOr


# ---
# Veredi Stuff
# ---
from veredi.logs                           import log

from veredi.base.strings                   import label
from veredi.base.const                     import VerediHealth
from veredi.base.exceptions                import VerediError
from veredi.base.context                   import VerediContext

from veredi.debug.const                    import DebugFlag

# ---
# Game Data
# ---
from veredi.data                           import background
from veredi.data.exceptions                import DataRequirementsError
from veredi.data.records                   import (DataType,
                                                   AnyDocTypeInput,
                                                   DocType,
                                                   Definition,
                                                   Saved)
from veredi.data.config.config             import Configuration
from veredi.data.context                   import (DataAction,
                                                   DataGameContext,
                                                   DataLoadContext,
                                                   DataSaveContext)
from veredi.data.repository.base           import BaseRepository
from veredi.data.repository.taxon          import Taxon, LabelTaxon, SavedTaxon
from veredi.data.serdes.base               import BaseSerdes, DeserializeTypes

from veredi.rules.game                     import RulesGame

# ---
# Game / ECS Stuff
# ---
from ..ecs.event                           import (EventIdInput,
                                                   EventTypeInput,
                                                   Event,
                                                   EventManager,
                                                   EcsManagerWithEvents)
from ..ecs.time                            import TimeManager
from ..ecs.component                       import ComponentManager

from ..ecs.const                           import SystemTick, tick_health_init
from ..ecs.exceptions                      import EventError, EcsManagerError

from ..ecs.base.identity                   import ComponentId
from ..ecs.base.component                  import Component

# ---
# Our Stuff
# ---
from .event import (
    # Should be all of them, but call them each out.

    # Requests from Game
    DataRequestEvent,  # Parent class for two below; used for type hinting.
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

from .component import DataComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class DataManager(EcsManagerWithEvents):

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # ------------------------------
    # Logging
    # ------------------------------

    _LOG_INIT: List[log.Group] = [
        log.Group.START_UP,
        log.Group.DATA_PROCESSING
    ]
    '''
    Group of logs we use a lot for log.group_multi().
    '''

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
        # Special Data
        # ------------------------------
        self._game: Optional[RulesGame] = None
        '''
        Game definition and saved data from our repository.
        '''

        # ------------------------------
        # Health
        # ------------------------------

        self._health_meter_event:   Optional[int] = None
        '''
        Store timing information for our timed/metered 'system isn't healthy'
        messages that fire off during event things.
        '''

        self._health_meter_update:  Optional[int] = None
        '''
        Stores timing information for our timed/metered 'system isn't healthy'
        messages that fire off during system tick things.
        '''

        # ------------------------------
        # Ticking
        # ------------------------------

        # Experimental: Keep data processing out of the standard tick?
        # Just let everyone else go at it.
        self._ticks: Optional[SystemTick] = (SystemTick.TICKS_BIRTH
                                             # All but standard...
                                             | (SystemTick.TICKS_LIFE
                                                & ~SystemTick.STANDARD)
                                             | SystemTick.TICKS_DEATH)
        '''
        The ticks we desire to run in. Just for our own checking...
        '''

        # Autophagy will be our end-of-game saving.

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
        # Misc.
        # ------------------------------

        self._bg: Dict[Any, Any] = None
        '''
        Our background context / meta-data for DataContexts.
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
        super().__init__(event_manager, debug_flags)
        self._log_start_up(self.dotted(),
                           "Creating DataManager...")

        # ---
        # Required Other Managers
        # ---
        self._time = time_manager
        self._component = component_manager

        # ---
        # Config Stuff
        # ---
        # We must have a config...
        if not config:
            msg = ("DataManager could not initialize. Require a Configuration "
                   f"and got: {config}")
            self._log_group_multi(self._LOG_INIT,
                                  self.dotted(),
                                  msg,
                                  log_success=False)
            raise background.config.exception(None, msg)

        # Create our serdes & repo from the config data.
        key_serdes = ('data', 'serdes')
        key_repo = ('data', 'repository', 'type')
        self._serdes = config.create_from_config(*key_serdes)
        self._repository = config.create_from_config(*key_repo)

        if not self._serdes:
            msg = ("DataManager could not create Serdes "
                   "(Serializer/Deserializer) from "
                   f"config data: {label.normalize(key_serdes)} "
                   f"{config.get(key_serdes)}")
            self._log_group_multi(self._LOG_INIT,
                                  self.dotted(),
                                  msg,
                                  log_success=False)
            context = config.make_config_context()
            raise background.config.exception(context, msg)
        if not self._repository:
            msg = ("DataManager could not create Repository from "
                   f"config data: {label.normalize(key_repo)} "
                   f"{config.get(key_repo)}")
            self._log_group_multi(self._LOG_INIT,
                                  self.dotted(),
                                  msg,
                                  log_success=False)
            context = config.make_config_context()
            raise background.config.exception(context, msg)

        # ---
        # Load Data
        # ---
        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              "DataManager loading initial data...")
        self._game = config.rules(None)
        self._init_load()
        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              "DataManager done.",
                              log_success=True)

    def get_background(self):
        '''
        Data for the Veredi Background context.
        '''
        if not self._bg:
            serdes_data, _ = self._serdes.background
            repo_data, _ = self._repository.background

            self._bg = {
                background.Name.DOTTED.key: self.dotted(),
                background.Name.SERDES.key: serdes_data,
                background.Name.REPO.key:   repo_data,
            }

        return self._bg

    @classmethod
    def dotted(klass: 'DataManager') -> str:
        return 'veredi.game.data.manager'

    # -------------------------------------------------------------------------
    # Loading & Saving
    # -------------------------------------------------------------------------

    def taxon(self,
              data_type: DataType,
              *taxonomy: Any,
              context:   Optional['VerediContext'] = None) -> Taxon:
        '''
        Create and return a Taxon of the correct sub-class for the `data_type`
        and the game rules.

        `context` only (currently [2021-01-21]) used for error log.

        E.g. DataType.SAVED with game rules 'veredi.rules.d20.pf2' returns a
        PF2SavedTaxon.
        '''
        taxon = self._game.taxon(data_type,
                                 *taxonomy,
                                 context=context)
        self._log_data_processing(self.dotted(),
                                  "DataManager created taxon: {}",
                                  taxon,
                                  log_minimum=log.Level.DEBUG)
        return taxon

    # -------------------------------------------------------------------------
    # Data Requests & Contexts
    # -------------------------------------------------------------------------

    def request(self,
                caller_dotted: label.DotStr,
                event_id:      EventIdInput,
                event_type:    EventTypeInput,
                data_action:   DataAction,
                taxon:         Taxon,
                context:       Optional['VerediContext'] = None
                ) -> DataRequestEvent:
        '''
        Create a DataLoadRequest or DataSaveRequest.

        Creates a DataLoadContext/DataSaveContext from the params via
        `DataManager.context()`, unless `context` is provided and is already a
        DataLoadContext/DataSaveContext /and/ matches `data_action` (e.g.
        DataLoadContext for LOAD).

        If `context` is not a DataLoadContext/DataSaveContext, it will just be
        used for error/logging purposes.

        Creates the request from the DataLoadContext/DataSaveContext and other
        inputs.

        Raises DataRequirementsError input checks fail.
        '''
        create_context = False
        request_ctx = context

        # ------------------------------
        # Sanity checks...
        # ------------------------------
        if (not context
                or not isinstance(context,
                                  (DataLoadContext, DataSaveContext))):
            # Nothing usable; create one.
            create_context = True

        elif isinstance(context, DataLoadContext):
            # Do we have the matching action?
            create_context = (data_action == DataAction.LOAD)

        elif isinstance(context, DataSaveContext):
            # Do we have the matching action?
            create_context = (data_action == DataAction.SAVE)

        else:
            # Failed sanity checks - error out.
            msg = ("Failed context checks - don't know how to create this "
                   "DataLoadRequest/DataSaveRequest.")
            error = DataRequirementsError(msg,
                                          context=context,
                                          data={
                                              'caller_dotted': caller_dotted,
                                              'event_id': event_id,
                                              'event_type': event_type,
                                              'data_action': data_action,
                                              'taxon': taxon,
                                          })
            raise self._log_exception(error, msg, context=context)

        # ------------------------------
        # Make the context if needed.
        # ------------------------------
        if create_context:
            request_ctx = self.context(caller_dotted,
                                       data_action,
                                       taxon,
                                       context)

        # Now request_ctx is ready to be put into a DataRequest Event.

        # ------------------------------
        # Make, return the request.
        # ------------------------------
        request = None
        if data_action == DataAction.LOAD:
            request = DataLoadRequest(event_id, event_type, request_ctx)

        elif data_action == DataAction.SAVE:
            request = DataLoadRequest(event_id, event_type, request_ctx)

        else:
            # Fail out on unknown DataAction.
            msg = (f"Unknown DataAction '{data_action}' - cannot create "
                   f"DataLoadRequest/DataSaveRequest for '{caller_dotted}'.")
            error = DataRequirementsError(msg,
                                          context=context,
                                          data={
                                              'caller_dotted': caller_dotted,
                                              'event_id': event_id,
                                              'event_type': event_type,
                                              'data_action': data_action,
                                              'taxon': taxon,
                                          })
            raise self._log_exception(error, msg, context=context)

        # Log about it and be done.
        self._log_data_processing(self.dotted(),
                                  "DataManager created request: {}",
                                  request,
                                  log_minimum=log.Level.DEBUG)
        return request

    def context(self,
                caller_dotted: label.DotStr,
                data_action:   DataAction,
                taxon:         Taxon,
                context:       Optional['VerediContext'] = None
                ) -> DataGameContext:
        '''
        Returns a DataLoadContext or DataSaveContext with the correct taxonomy
        sub-class for the game rules.
        '''
        # ---
        # Make or die!
        # ---
        data_context = None
        if data_action == DataAction.LOAD:
            data_context = DataLoadContext(caller_dotted, taxon, self._bg)

        elif data_action == DataAction.SAVE:
            data_context = DataSaveContext(caller_dotted, taxon, self._bg)

        else:
            msg = (f"Unknown DataAction '{data_action}' - cannot create "
                   f"DataLoadContext/DataSaveContext for '{caller_dotted}'.")
            error = DataRequirementsError(msg,
                                          context=context,
                                          data={
                                              'caller_dotted': caller_dotted,
                                              'data_action': data_action,
                                              'taxon': taxon,
                                          })
            raise self._log_exception(error, msg, context=context)

        # ---
        # Return or!.. no, just return.
        # ---
        self._log_data_processing(self.dotted(),
                                  "DataManager created context: {}",
                                  data_context,
                                  log_minimum=log.Level.DEBUG)
        return data_context

    # -------------------------------------------------------------------------
    # Loading...
    # -------------------------------------------------------------------------

    def _load(self, context: DataLoadContext) -> Nullable[DeserializeTypes]:
        '''
        Use the context to load something from the repo and deserialize it via
        the serdes.

        Returns the deserialized result or Null.
        '''
        loaded = self._repository.load(context)
        decoded = self._serdes.deserialize_all(loaded, context)
        return decoded

    def _init_load(self) -> None:
        '''
        Load everything needed from the very start.
        '''
        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              "DataManager initial loading...",
                              log_minimum=log.Level.DEBUG)
        self._load_game()

    def _load_game(self) -> None:
        '''
        Load game definition and saved data from repository.
        '''
        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              "DataManager initial game loading...",
                              log_minimum=log.Level.DEBUG)

        # ---
        # Load Game Definition...
        # ---
        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              "DataManager loading definition...",
                              log_minimum=log.Level.DEBUG)
        definition = self.load_definition(self.dotted(),
                                          DocType.definition.game,
                                          self._game.game_definition())

        # ---
        # Load Game Save...
        # ---
        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              "DataManager loading saved...",
                              log_minimum=log.Level.DEBUG)
        saved = self.load_saved(self.dotted(),
                                DocType.saved.game,
                                self._game.game_saved())

        # ---
        # Tell our RulesGame object about 'em.
        # ---
        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              "DataManager finalizing game rules...",
                              log_minimum=log.Level.DEBUG)
        self._game.loaded(definition, saved)

        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              "DataManager initial game loading complete.",
                              log_minimum=log.Level.DEBUG,
                              log_success=True)

    def load_definition(self,
                        caller_dotted: str,
                        doc_type:      AnyDocTypeInput,
                        taxon:         LabelTaxon) -> Definition:
        '''
        Out-of-band data load for a Definition record.

        Systems and such may use this during their initialization and/or during
        TICKS_BIRTH.

        NOTE: DO NOT USE DURING NORMAL OPERATION.
        '''
        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              "DataManager load Definition for {}: {} {}...",
                              caller_dotted, doc_type, taxon,
                              log_minimum=log.Level.DEBUG)
        context_definition = DataLoadContext(caller_dotted, taxon, self._bg)
        data = self._load(context_definition)
        definition = Definition(doc_type, data)
        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              "DataManager load Definition complete.",
                              log_minimum=log.Level.DEBUG,
                              log_success=True)
        return definition

    def load_saved(self,
                   caller_dotted: str,
                   doc_type:      AnyDocTypeInput,
                   taxon:         SavedTaxon) -> Saved:
        '''
        Out-of-band data load for a Saved record.

        Systems and such may use this during their initialization and/or during
        TICKS_BIRTH.

        NOTE: DO NOT USE DURING NORMAL OPERATION.
        '''
        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              "DataManager load Saved for {}: {} {}...",
                              caller_dotted, doc_type, taxon,
                              log_minimum=log.Level.DEBUG)
        context_saved = DataLoadContext(caller_dotted, taxon, self._bg)
        data = self._load(context_saved)
        saved = Saved(doc_type, data)
        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              "DataManager load Saved complete.",
                              log_minimum=log.Level.DEBUG,
                              log_success=True)
        return saved

    # -------------------------------------------------------------------------
    # Saving...
    # -------------------------------------------------------------------------

    # TODO

    # -------------------------------------------------------------------------
    # Special Data
    # -------------------------------------------------------------------------

    @property
    def game(self) -> Optional[RulesGame]:
        '''
        Returns our RulesGame object.
        '''
        return self._game

    @property
    def game_definition(self) -> Optional[Definition]:
        '''
        Returns our RulesGame's Definition data.
        '''
        return self._game.definition

    @property
    def game_saved(self) -> Optional[Saved]:
        '''
        Returns our RulesGame's Saved data.
        '''
        return self._game.saved

    # -------------------------------------------------------------------------
    # Health
    # -------------------------------------------------------------------------

    def _health_log(self,
                    log_meter: int,
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
                f"HEALTH({str(self.health)}): " + msg,
                args, kwargs)
        return maybe_updated_meter

    def _meter_log(self,
                   meter:     int,
                   msg:       str,
                   *args:     Any,
                   log_level: log.Level = log.Level.WARNING,
                   **kwargs:  Any) -> int:
        '''
        Log a metered log. Or ignore if the output log meter says no
        logging right now.

        Returns the updated `meter`, which caller should assign back:
          self._a_meter = self._meter_log(self._a_meter,
                                          "Hello there.")
        '''
        output_log, meter = self._time.metered(meter)
        if output_log:
            kwargs = self._log_stack(**kwargs)
            self._health_meter_event = self._health_log(
                self._health_meter_event,
                log.Level.WARNING,
                msg,
                *args,
                **kwargs)

        # Caller should update the meter they used to call us.
        return meter

    def _health_ok_event(self,
                         event: 'Event') -> bool:
        '''
        Check health, log if needed, and return True if able to proceed.
        '''
        if self._healthy(self._time.engine_tick_current):
            return True

        # Unhealthy? Log (maybe) and return False.
        meter = self._health_meter_event
        output_log, meter = self._time.metered(meter)
        self._health_meter_event = meter
        if output_log:
            msg = ("Dropping event {} - DataManager's health "
                   "isn't good enough to process.")
            kwargs = self._log_stack()
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
        kwargs = self._log_stack()
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
        Idempotently subscribe to DataManager's events.

        In the general case, only DataLoadRequest and DataSaveRequest will be
        subscribed to, but tests and such may do something special and trigger
        intermediate/internal events, so we are able to subscribe to all if set
        up to.
        '''
        self._log_start_up(self.dotted(),
                           "DataManager.subscribe()...",
                           log_minimum=log.Level.DEBUG)
        # ---
        # MUST BE IDEMPOTENT!
        # ---
        # That is... This must be callable multiple times with it doing the
        # correct thing once and only once.
        # ---
        super().subscribe(event_manager)

        # ------------------------------
        # External/Expected: Request for Load / Save
        # ------------------------------

        # - DataLoadRequest
        #   The data needs to be fetched and loaded.
        #   - Repository creates a _LoadedEvent once it has done this.
        if not self._event.is_subscribed(DataLoadRequest,
                                         self._event_data_load_request):
            self._log_start_up(self.dotted(),
                               "DataManager subscribing to DataLoadRequest...")
            self._event.subscribe(DataLoadRequest,
                                  self._event_data_load_request)

        # - DataSaveRequest
        #   Data needs to be serialized before it can be saved.
        #   - Serdes creates an _SerializedEvent once it has done this.
        if not self._event.is_subscribed(DataSaveRequest,
                                         self._event_data_save_request):
            self._log_start_up(self.dotted(),
                               "DataManager subscribing to DataSaveRequest...")
            self._event.subscribe(DataSaveRequest,
                                  self._event_data_save_request)

        # ------------------------------
        # Normal Path: Done
        # ------------------------------
        if not self._ut_all_events_external:
            self._log_start_up(
                self.dotted(),
                "DataManager subscribed to all standard events.",
                log_success=True)
            return VerediHealth.HEALTHY
        # Unit Testing? Subscribe to the internal events too.

        self._log_start_up(self.dotted(),
                           "DataManager.subscribe() is subscribing to all its "
                           "internal events as well (unit testing?).",
                           log_minimum=log.Level.INFO)

        # ------------------------------
        # Internal: Serialize / Deserialize with Serdes
        # ------------------------------

        # - _DeserializedEvent
        #   The data has been interpreted into Python/Veredi. Now it needs to
        #   be stuffed into a component or something and attached to an entity
        #   or something.
        #   - We create a DataLoadedEvent once this is done.
        if not self._event.is_subscribed(_DeserializedEvent,
                                         self._event_deserialized):
            self._log_start_up(
                self.dotted(),
                "DataManager subscribing to _DeserializedEvent...")
            self._event.subscribe(_DeserializedEvent,
                                  self._event_deserialized)

        # - _SerializedEvent
        #   Once data is serialized, it needs to be saved to repo.
        #   - Repository creates an _SavedEvent once it has done this.
        if not self._event.is_subscribed(_SerializedEvent,
                                         self._event_serialized):
            self._log_start_up(
                self.dotted(),
                "DataManager subscribing to _SerializedEvent...")
            self._event.subscribe(_SerializedEvent,
                                  self._event_serialized)

        # ------------------------------
        # Internal: Load / Save from Repository
        # ------------------------------

        # - _SavedEvent
        #   Once data is saved to repo, we want to say it's been saved.
        #   - We'll creates a DataSavedEvent to do this.
        if not self._event.is_subscribed(_SavedEvent,
                                         self._event_saved):
            self._log_start_up(
                self.dotted(),
                "DataManager subscribing to _SavedEvent...")
            self._event.subscribe(_SavedEvent,
                                  self._event_saved)

        # - _LoadedEvent
        #   Loaded Data needs to be deserialized so it can be used in game.
        #   - Serdes creates a _DeserializedEvent once it has done this.
        if not self._event.is_subscribed(_LoadedEvent,
                                         self._event_loaded):
            self._log_start_up(
                self.dotted(),
                "DataManager subscribing to _LoadedEvent...")
            self._event.subscribe(_LoadedEvent,
                                  self._event_loaded)

        self._log_start_up(
            self.dotted(),
            "DataManager subscribed to all standard & "
            "internal events.",
            log_success=True)
        return VerediHealth.HEALTHY

    # -------------------------------------------------------------------------
    # Events: Request for Load / Save
    # -------------------------------------------------------------------------

    def _event_data_load_request(self, event: DataLoadRequest) -> None:
        '''
        Request for data to be loaded. We must ask the repo for it and pack it
        into a _LoadedEvent.
        '''
        # TODO: group_multi w/ EVENTS group?
        self._log_data_processing(
            self.dotted(),
            "DataManager event handling: DataLoadRequest...")

        # Doctor checkup.
        if not self._health_ok_event(event):
            self._log_data_processing(self.dotted(),
                                      "DataManager[DataLoadRequest] failed "
                                      "health check...",
                                      log_success=False)
            return

        context = event.context

        self._log_data_processing(self.dotted(),
                                  "DataManager[DataLoadRequest] loading...")

        # Ask my repository for this data.
        # Load data info is in the request context.
        loaded = self._repository.load(context)
        # Get back loaded data stream.

        self._log_data_processing(self.dotted(),
                                  "DataManager[DataLoadRequest] creating "
                                  "result _LoadedEvent...")

        # Take our repository load result and set into _LoadedEvent. Then
        # have EventManager fire off event for whoever wants the next step.
        event = _LoadedEvent(event.id, event.type, context,
                             data=loaded)

        # Special Shenanigans: Publish this event, wait for it to come back.
        if self._ut_all_events_external:
            self._log_data_processing(
                self.dotted(),
                "DataManager[DataLoadRequest] publishing "
                "result _LoadedEvent...")
            self._event_notify(event, False)

        # Normal Case: Pass on to process loaded data
        else:
            self._log_data_processing(self.dotted(),
                                      "DataManager[DataLoadRequest] handling "
                                      "result _LoadedEvent internally...")
            self._event_loaded(event)

        self._log_data_processing(self.dotted(),
                                  "DataManager[DataLoadRequest] done.",
                                  log_success=True)

    def _event_data_save_request(self, event: DataSaveRequest) -> None:
        '''
        Data wants saved. It must be serialized first.
        '''
        # TODO: group_multi w/ EVENTS group?
        self._log_data_processing(
            self.dotted(),
            "DataManager event handling: DataSaveRequest...")

        # Doctor checkup.
        if not self._health_ok_event(event):
            self._log_data_processing(self.dotted(),
                                      "DataManager[DataSaveRequest] failed "
                                      "health check...",
                                      log_success=False)
            return

        context = self._serdes.context.push(event.context)

        self._log_data_processing(self.dotted(),
                                  "DataManager[DataSaveRequest] saving...")

        # TODO [2020-05-22]: Serialize it...
        raise NotImplementedError(
            f"{self.__class__.__name__}.event_data_save_request() "
            "is not yet implemented...")

        serialized = None

        self._log_data_processing(self.dotted(),
                                  "DataManager[DataSaveRequest] creating "
                                  "result _SavedEvent...")

        # Done; fire off event for whoever wants the next step.
        event = _SerializedEvent(event.id,
                                 event.type,
                                 context,
                                 data=serialized)

        # Special Shenanigans: Publish this event, wait for it to come back.
        if self._ut_all_events_external:
            self._log_data_processing(
                self.dotted(),
                "DataManager[DataSaveRequest] publishing "
                "result _SavedEvent...")
            self._event_notify(event, False)

        # Normal Case: Pass on to process deserialized data.
        else:
            self._log_data_processing(self.dotted(),
                                      "DataManager[DataSaveRequest] handling "
                                      "result _SavedEvent internally...")
            self._event_serialized(event)

        self._log_data_processing(self.dotted(),
                                  "DataManager[DataSaveRequest] done.",
                                  log_success=True)

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
            raise self._log_exception(
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
                    self._log_debug(
                        "Processing event {}, rec: {}, document: {}.",
                        event,
                        document['record-type'],
                        document['doc-type'])
                else:
                    self._log_debug(
                        "Processing event {}, rec: {}, document: {}.",
                        event,
                        None,
                        document['doc-type'])
                if ('doc-type' in document
                        and document['doc-type'] == 'component'):
                    self._log_debug("Found component; requesting creation.")
                    cid = self._request_creation(document, event)

            except EventError:
                # self._request_creation() failed - bubble up.
                raise

            except VerediError as error:
                # Chain/wrap in a EcsManagerError.
                raise self._log_exception(
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
            return VerediHealth.IGNORE

        # Doctor checkup.
        if not self._health_ok_tick(tick):
            return self.health

        # ------------------------------
        # Tick Types
        # ------------------------------
        # Run the specific tick cycle.
        if tick in SystemTick.TICKS_BIRTH:
            self.health = self._update_start(tick)
            return self.health

        elif tick in SystemTick.TICKS_LIFE:
            self.health = self._update_run(tick)
            return self.health

        elif tick in SystemTick.TICKS_DEATH:
            health = self._update_end(tick)
            self.health = health
            return self.health

        # ------------------------------
        # Error!
        # ------------------------------
        # ...else... What tick is this tick even?
        self._health_meter_update = self._meter_log(
            self._health_meter_update,
            f"Unknown tick {tick}?! Setting health to FATAL!")
        health = VerediHealth.FATAL
        self.health = health
        return health

    def _update_start(self, tick: SystemTick) -> VerediHealth:
        '''
        Tick processing specific to SystemTick.TICKS_BIRTH
        '''
        if tick not in SystemTick.TICKS_BIRTH:
            self._health_meter_update = self._meter_log(
                self._health_meter_update,
                f"Tick {tick} is not in SystemTick.TICKS_BIRTH. Why are we "
                "in this function then?! Setting health to FATAL!")
            health = VerediHealth.FATAL
            self.health = health
            return health

        # Do Tick Things Here.
        health = tick_health_init(tick)
        self.health = health
        return health

    def _update_run(self, tick: SystemTick) -> VerediHealth:
        '''
        Tick processing specific to SystemTick.TICKS_LIFE
        '''
        health = tick_health_init(tick)

        if tick not in SystemTick.TICKS_LIFE:
            self._health_meter_update = self._meter_log(
                self._health_meter_update,
                f"Tick {tick} is not in SystemTick.TICKS_LIFE. Why are we "
                "in this function then?! Setting health to FATAL!")
            health = VerediHealth.FATAL
            self.health = health
            return health

        # ------------------------------
        # Full Tick Rate: Start
        # ------------------------------

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
        # if not self._time.is_reduced_tick(
        #         tick,
        #         self._reduced_tick_rate):
        #     self.health = health
        #     return self.health
        # - - - - - - - - - - -
        # !! REDUCED Tick Rate: START !!
        # ------------------------------

        self.health = health
        return health

    def _update_end(self, tick: SystemTick) -> VerediHealth:
        '''
        Tick processing specific to SystemTick.TICKS_DEATH
        '''
        # Specific end ticks:
        if tick is SystemTick.AUTOPHAGY:
            # Do Tick Things Here.

            # Check for events; return VerediHealth.AUTOPHAGY,
            # VerediHealth.AUTOPHAGY_SUCCESSFUL based on if processed any?
            health = VerediHealth.AUTOPHAGY_SUCCESSFUL
            self.health = health
            return health

        elif tick is SystemTick.APOPTOSIS:
            # If apoptosis is still in progress, return
            # VerediHealth.APOPTOSIS.
            health = VerediHealth.APOPTOSIS_DONE
            self.health = health
            return health

        elif tick is SystemTick.NECROSIS:
            health = VerediHealth.NECROSIS
            self.health = health
            return health

        # Uh... What tick then? Already checked.
        self._health_meter_update = self._meter_log(
            self._health_meter_update,
            f"Tick {tick} is not in SystemTick.TICKS_DEATH. Why are we "
            "in this function then?! Setting health to FATAL!")
        health = VerediHealth.FATAL
        self.health = health
        return health

    # -------------------------------------------------------------------------
    # Unit Testing Helpers
    # -------------------------------------------------------------------------

    def _ut_set_up(self) -> None:
        '''
        Any unit-testing set-up for DataManager or its members to do (e.g.
        repository)?
        '''
        self._repository._ut_set_up()

    def _ut_tear_down(self) -> None:
        '''
        Any unit-testing tear-down for DataManager or its members to do (e.g.
        repository)?
        '''
        self._repository._ut_tear_down()
