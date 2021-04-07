# coding: utf-8

'''
Base class for testing an ECS System or Engine. Used by ZestSystem and
ZestEngine. No one currently uses this directly [2020-08-24].
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type, List, Iterable, Dict)
if TYPE_CHECKING:
    from veredi.run.system               import SysCreateType

from veredi.logs                         import log
from veredi.base                         import random

from .unit                               import ZestBase
from ..                                  import zload
from ..exceptions                        import UnitTestError
from ..zpath                             import TestType

from veredi.base.context                 import VerediContext, UnitTestContext
from veredi.debug.const                  import DebugFlag

from veredi.base.null                    import Null, null_or_none
from veredi.data.config.config           import Configuration
from veredi.data.context                 import DataAction
from veredi.data.records                 import DataType

from veredi.game.ecs.base.system         import System
from veredi.game.ecs.base.entity         import (Entity,
                                                 EntityLifeCycle)
from veredi.game.ecs.base.identity       import EntityId
from veredi.game.ecs.base.component      import (Component,
                                                 ComponentLifeCycle)
from veredi.game.ecs.event               import Event, EventTypeInput
from veredi.game.data.event              import (DataRequestEvent,
                                                 DataLoadedEvent)
from veredi.game.data.identity.event     import (IdentityRequest,
                                                 CodeIdentityRequest)
from veredi.game.data.identity.component import IdentityComponent


from veredi.game.ecs.time                import TimeManager
from veredi.game.ecs.event               import EventManager
from veredi.game.ecs.component           import ComponentManager
from veredi.game.ecs.entity              import EntityManager
from veredi.game.ecs.system              import SystemManager
from veredi.game.data.manager            import DataManager
from veredi.game.data.identity.manager   import IdentityManager
from veredi.game.engine                  import Engine
from veredi.game.ecs.meeting             import Meeting

from veredi.interface.input.system       import InputSystem
from veredi.interface.input.command.reg  import CommandRegistrationBroadcast

from veredi.interface.output.system      import OutputSystem


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Base Class for Testing Systems
# -----------------------------------------------------------------------------

class ZestEcs(ZestBase):
    '''
    Base class for testing an ECS System or Engine. Used by ZestSystem and
    ZestEngine. No one currently uses this directly [2020-08-24].
    '''

    _REQUIRE_ENGINE = False

    LOG_LEVEL = log.Level.INFO
    '''
    Test should set this to desired during set_up().

    TODO: Start using this in base classes?
    '''

    # -------------------------------------------------------------------------
    # Set-Up
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Defines ZestSystem's instance variables with type hinting, docstrs.
        '''
        super()._define_vars()

        # ------------------------------
        # Events
        # ------------------------------

        self.events: List[Event] = []
        '''
        Simple queue for receiving events.
        '''

        self._event_debug_counter: int = 0
        '''
        Counter that is used for debugging Events.
        '''

        self.reg_open: CommandRegistrationBroadcast = None
        '''
        Separate variable for holding a received command registration
        broadcast event.
        '''

        # ------------------------------
        # ECS
        # ------------------------------

        self.manager: Meeting = None
        '''
        If class uses ECS, the Meeting of ECS Managers should go here.
        zload.set_up_ecs() can provide this.
        '''

        # ------------------------------
        # Engine
        # ------------------------------

        self.engine: Engine = None
        '''
        The ECS Game Engine.
        zload.set_up_ecs() can provide this.
        '''

    def set_up(self) -> None:
        '''
        Override this!

        super().set_up()
        <your test stuff>
        self.init_self_system(...)
        '''
        self._set_up_ecs()

    # ------------------------------
    # Set-Up ECS
    # ------------------------------

    def _set_up_ecs(self,
                    # Will be class.type if None:
                    test_type:         Optional[TestType]         = None,
                    # Optional ECS:
                    require_engine:    Optional[bool]             = None,
                    desired_systems:   Iterable['SysCreateType']  = None,
                    # Optional to pass in - else we'll make:
                    configuration:     Optional[Configuration]    = None,
                    time_manager:      Optional[TimeManager]      = None,
                    event_manager:     Optional[EventManager]     = None,
                    component_manager: Optional[ComponentManager] = None,
                    entity_manager:    Optional[EntityManager]    = None,
                    system_manager:    Optional[SystemManager]    = None,
                    data_manager:      Optional[DataManager]      = None,
                    identity_manager:  Optional[IdentityManager]  = None,
                    # Optional to pass in - else we'll make  if asked:
                    engine:            Optional[Engine]           = None
                    ) -> None:
        '''
        Calls zload.set_up to create Meeting of EcsManagers, and a context from
        a config file.

        None of the args are needed, usually.
          - `test_type` will become `self.type` if it is None.
          - `require_engine` will become `self._REQUIRE_ENGINE` if it is None.
        '''
        if test_type is None:
            test_type = self.type
        if require_engine is None:
            require_engine = self._REQUIRE_ENGINE
        if configuration is None and self.config:
            configuration = self.config

        (self.manager, self.engine,
         self.context, _) = zload.set_up_ecs(
             __file__,
             self,
             '_set_up_ecs',
             self.debugging,
             test_type=test_type,
             debug_flags=self.debug_flags,
             require_engine=require_engine,
             desired_systems=desired_systems,
             configuration=configuration,
             time_manager=time_manager,
             event_manager=event_manager,
             component_manager=component_manager,
             entity_manager=entity_manager,
             system_manager=system_manager,
             data_manager=data_manager,
             identity_manager=identity_manager,
             engine=engine)

    # ------------------------------
    # Input / Output Set-Up
    # ------------------------------

    def set_up_input(self) -> None:
        '''
        Creates self.input_system and registers self._eventsub_cmd_reg for
        CommandRegistrationBroadcast. Broadcast will be received into
        self.reg_open.
        '''
        self.manager.event.subscribe(CommandRegistrationBroadcast,
                                     self._eventsub_cmd_reg)
        self.input_system = self.init_one_system(InputSystem)

    def set_up_output(self) -> None:
        '''
        Creates/initializes OutputSystem.
        '''
        self.output_system = self.init_one_system(OutputSystem)

    # ------------------------------
    # Event Set-Up
    # ------------------------------

    def set_up_events(self,
                      clear_self:    bool = True,
                      clear_manager: bool = True) -> None:
        '''
        Does all event subscription/set-up by calling self._sub_*() functions.
        '''
        self._sub_data_loaded()
        if not self.engine and not self._REQUIRE_ENGINE:
            # Engine should be in charge of telling people to "subscribe now!"
            self._sub_events_systems()
        self.sub_events()

        # Clear out events if needed.
        if clear_self:
            # Self and possibly manager.
            self.clear_events(clear_manager=clear_manager)
        elif clear_manager:
            # Only manager.
            self._clear_manager_events()

    def sub_events(self) -> None:
        '''
        Subscribe to the events your want to be the (or just a)
        receiver/handler for here. Called from set_up_event() for tests that
        want to do events.

        e.g.:
        self.manager.event.subscribe(JeffEvent,
                                     self.event_cmd_jeff)
        '''
        ...

    def _sub_data_loaded(self) -> None:
        '''
        Automatically called in set_up_events() currently.
        '''
        if not self.manager or not self.manager.event:
            return

        self.manager.event.subscribe(DataLoadedEvent, self._eventsub_loaded)

    def _sub_events_systems(self) -> None:
        '''
        Tells each ECS Manager to subscribe().

        SystemManager will tell all Systems it knows about (which /should/ be
        every single one) to subscribe().
        '''
        if not self.manager:
            return

        # Let all our ECS pieces set up their subs.
        # Extra if checks in case a test only uses part of ECS.
        with log.LoggingManager.on_or_off(self.debugging):
            if self.manager.component:
                self.manager.component.subscribe(self.manager.event)

            if self.manager.entity:
                self.manager.entity.subscribe(self.manager.event)

            if self.manager.system:
                self.manager.system.subscribe(self.manager.event)

            if self.manager.data:
                self.manager.data.subscribe(self.manager.event)

            if self.manager.identity:
                self.manager.identity.subscribe(self.manager.event)

    # -------------------------------------------------------------------------
    # Tear-Down
    # -------------------------------------------------------------------------

    def tear_down(self):
        '''
        Override this to add your own tear-down!

        Tears down the ECS (and Engine, if there is one).

        <your tear-down stuff>
        super().tear_down()
        '''
        self._tear_down_ecs()

    def _tear_down_ecs(self):
        '''
        Calls zload.tear_down_ecs to have meeting/managers run any tear-down
        they happen to have.
        '''
        zload.tear_down_ecs(__file__,
                            self,
                            '_tear_down_ecs',
                            self.debugging,
                            self.manager,
                            engine=self.engine)

    # -------------------------------------------------------------------------
    # System Creation Helpers
    # -------------------------------------------------------------------------

    def init_many_systems(self, *sys_types: System) -> None:
        '''
        Initializes several systems you need but don't need to hang on to
        directly for your test.
        '''
        sids = zload.create_systems(None,
                                    self.context,
                                    *sys_types)
        return sids

    # Could do something like this if we need args/kwargs and many systems.
    # def init_many_systems(self, *args, **kwargs):
    #     sids = []
    #     for each in args:
    #         if isinstance(each, tuple):
    #             sids.append(self.init_one_system(each[0], self.context,
    #                                              *each[1:], **each[2:]))
    #         else:
    #             sids.append(self.init_one_system(each, self.context))
    #
    #     return sids

    def init_one_system(self,
                        sys_type: System,
                        *args:    Any,
                        **kwargs: Any) -> System:
        '''
        Initializes a system and returns its instance object.
        '''
        context = UnitTestContext(
            self,
            data=({}
                  if not kwargs else
                  {'system': kwargs}))

        sid = self.manager.system.create(sys_type, context)
        return self.manager.system.get(sid)

    # -------------------------------------------------------------------------
    # Debugging
    # -------------------------------------------------------------------------

    def _debug_on(self,
                  debug_flags:      DebugFlag,
                  set_this_test:    bool = False,
                  set_all_systems:  bool = False,
                  set_all_managers: bool = False,
                  set_engine:       bool = False) -> None:
        '''
        Turn on these debug flags.
        '''
        # If all flags false, why you do that even?
        if not (set_this_test or set_all_systems
                or set_all_managers or set_engine):
            msg = ("Cannot turn DebugFlag on for nothing. "
                   "All `set` bools are False.")
            error = UnitTestError(msg,
                                  data={
                                      'debug_flags_on': debug_flags,
                                      'set_this_test': set_this_test,
                                      'set_all_systems': set_all_systems,
                                      'set_all_managers': set_all_managers,
                                      'set_engine': set_engine,
                                  })
            raise log.exception(error, msg)

        # ---
        # Set stuff.
        # ---
        if set_this_test:
            self.debug_flags = self.debug_flags.set(debug_flags)

        if set_all_systems:
            # As of now [2020-12-18], the systems use the Meeting's DebugFlag.
            self.manager._debug = self.manager._debug.set(debug_flags)

            # If the systems get their own flags, we could do this:
            # for system in self.manager.system._ut_each_system():
            #    ...

        if set_all_managers:
            # Set Meeting's? Managers don't use, but we're setting all
            # managers' debug flags, so it makes sense.
            self.manager._debug = self.manager._debug.set(debug_flags)

            for manager in self.manager._each_existing():
                manager._debug = manager._debug.set(debug_flags)

        if set_engine:
            # Engine doesn't always exist in ZestEcs, so check first.
            if self.engine:
                self.engine._debug = self.engine._debug.set(debug_flags)

    def _debug_off(self,
                   debug_flags:      DebugFlag,
                   set_this_test:    bool = False,
                   set_all_systems:  bool = False,
                   set_all_managers: bool = False,
                   set_engine:       bool = False) -> None:
        '''
        Turn off these debug flags.
        '''
        # If all flags false, why you do that even?
        if not (set_this_test or set_all_systems
                or set_all_managers or set_engine):
            msg = ("Cannot turn DebugFlag off for nothing. "
                   "All `set` bools are False.")
            error = UnitTestError(msg,
                                  data={
                                      'debug_flags_on': debug_flags,
                                      'set_this_test': set_this_test,
                                      'set_all_systems': set_all_systems,
                                      'set_all_managers': set_all_managers,
                                      'set_engine': set_engine,
                                  })
            raise log.exception(error, msg)

        # ---
        # Set stuff.
        # ---
        if set_this_test:
            self.debug_flags = self.debug_flags.unset(debug_flags)

        if set_all_systems:
            # As of now [2020-12-18], the systems use the Meeting's DebugFlag.
            self.manager._debug = self.manager._debug.unset(debug_flags)

            # If the systems get their own flags, we could do this:
            # for system in self.manager.system._ut_each_system():
            #    etc...

        if set_all_managers:
            # Unset Meeting's? Managers don't use, but we're setting all
            # managers' debug flags, so it makes sense.
            self.manager._debug = self.manager._debug.unset(debug_flags)

            for manager in self.manager._each_existing():
                manager._debug = manager._debug.unset(debug_flags)

        if set_engine:
            # Engine doesn't always exist in ZestEcs, so check first.
            if self.engine:
                self.engine._debug = self.engine._debug.unset(debug_flags)

    def _event_debugging(self,
                         event: Event,
                         title: str) -> None:
        '''
        Increments `self._event_debug_counter` by one.

        Logs something about an event if our event debugging flag is on.
        '''
        self._event_debug_counter += 1
        if self.manager.event._debug.has(DebugFlag.EVENTS):
            log.ultra_hyper_debug(event,
                                  title=title)

    # -------------------------------------------------------------------------
    # Event Helpers
    # -------------------------------------------------------------------------

    def event_type_dont_care(self) -> int:
        '''
        Don't care about event type? Why not a random number?
        '''
        return random.randint(0, 100)

    def clear_events(self, clear_manager: bool = False) -> None:
        '''
        Clears out the `self.events` queue.

        if `clear_manager` is True, also clears out EventManager's event queue.
        '''
        self.events.clear()
        if clear_manager:
            self._clear_manager_events()

    def _clear_manager_events(self) -> Iterable[Event]:
        '''
        If we have an EventManager, clear out any queued events it has.
        '''
        if not self.manager or not self.manager.event:
            return []

        return self.manager.event._ut_clear_events()

    def _event_now(self,
                   event:         Event,
                   num_publishes: int = 3) -> None:
        '''
        Helper for self.trigger_events, mostly. Though could be used if
        trigger_events' assertions aren't wanted.

        Notifies the event for immediate action (that is, it immediately gets
        published and its subscribers immediately receive it).

        Which /should/ cause something to process it and queue up an event? So
        we publish() in order to get that one sent out. Which /may/ cause
        something to process that and queue up another. So we'll publish as
        many times as asked in `num_publishes`.

        NOTE: This has a LoggingManager in it, so set self.debugging to true if
        you need to output all the logs during events.
        '''
        with log.LoggingManager.on_or_off(self.debugging):
            self.manager.event.notify(event, True)

            for each in range(num_publishes):
                self.manager.event.publish()

    def trigger_events(self,
                       event:           Event,
                       num_publishes:   int = 3,
                       expected_events: int = 1) -> None:
        '''
        Sanity asserts on inputs, then we call _event_now() to immediately
        trigger event and response. Then we check our events queue against
        `expected_events` (set to zero if you don't expect any).

        NOTE: This has a LoggingManager in it, so set self.debugging to true if
        you need to output all the logs during events.
        '''
        self.assertTrue(event)
        self.assertTrue(num_publishes > 0)
        self.assertTrue(expected_events >= 0)

        # This has a LoggingManager in it, so set self.debugging to true if you
        # need to output all the logs during events.
        self._event_now(event, num_publishes)

        # Build a message for all the events existing if we are about to fail
        # and we are verbose?
        event_msg = None
        if (len(self.events) != expected_events
                and (self._ut_is_verbose or self.LOG_LEVEL >= log.Level.INFO)):
            event_strs = [str(event) for event in self.events]
            event_msg = "\nUnexpected number of events in self.events!:"
            for string in event_strs:
                event_msg += f"\n\n  {string}"
        self.assertEqual(len(self.events), expected_events,
                         event_msg)

    def _eventsub_generic_append(self, event: Event) -> None:
        '''
        Receiver for any event where you just want to append event to
        self.events list.

        Just use as the callback for an event:
          self.manager.event.subscribe(SomeEvent,
                                       self._eventsub_generic_append)
        '''
        self._event_debugging(event,
                              (f'{self.__class__.__name__}.'
                               '_eventsub_generic_append('
                               f'{type(event)}, class-id:{id(event)})'))
        self.events.append(event)

    def _eventsub_loaded(self, event: Event) -> None:
        '''
        Receiver for DataLoadedEvent.

        Only receives DataLoadedEvents if self.sub_data_loaded() was called in
        your derived class (probably in self.setup_events()).
        '''
        self.events.append(event)

    def _eventsub_cmd_reg(self, event) -> None:
        '''
        Receiver for CommandRegistrationBroadcast event. Stores
        CommandRegistrationBroadcast event in self.reg_open.

        Calls self.register_commands(self.reg_open)
        '''
        self.assertIsInstance(event,
                              CommandRegistrationBroadcast)
        self.reg_open = event

        self.register_commands(self.reg_open)

    # -------------------------------------------------------------------------
    # Data Helpers
    # -------------------------------------------------------------------------

    def data_request(self,
                     entity_id:   EntityId,
                     *taxonomy:   Any,
                     event_type:  Optional[EventTypeInput] = None,
                     data_type:   DataType   = DataType.SAVED,
                     data_action: DataAction = DataAction.LOAD
                     ) -> DataRequestEvent:
        '''
        Create a DataLoadRequest or DataSavedRequest from the given taxonomy.

        If an `event_type` is not supplied, `self.event_type_dont_care()`
        will be used.
        '''
        taxon = self.manager.data.taxon(data_type,
                                        *taxonomy)

        if null_or_none(event_type):
            event_type = self.event_type_dont_care()

        request = self.manager.data.request(self.dotted,
                                            entity_id,
                                            event_type,
                                            data_action,
                                            taxon)
        return request

    # -------------------------------------------------------------------------
    # Command Helpers
    # -------------------------------------------------------------------------

    def allow_registration(self) -> None:
        '''
        If we have a self.input_system, get the CommandRegistrationBroadcast
        from its Commander and trigger that event via self.trigger_events().
        This should result in all commands being registered after this function
        is complete.
        '''
        # Ignore if we've already allowed registration or if we have no
        # input_system to get the CommandRegistrationBroadcast from.
        if self.reg_open or not self.input_system:
            return

        event = self.input_system._commander.registration(
            self.input_system.id,
            Null())
        self.trigger_events(event,
                            expected_events=0,
                            num_publishes=1)

        # Now registration is open.
        self.assertTrue(self.reg_open)

    def register_commands(self, event: CommandRegistrationBroadcast) -> None:
        '''
        Do things here to make your test's commands if you have any.
        '''
        self.assertIsInstance(event, CommandRegistrationBroadcast)

    # -------------------------------------------------------------------------
    # Create Things for Tests
    # -------------------------------------------------------------------------

    def create_entity(self,
                      clear_received_events=True,
                      clear_manager_event_queue=True,
                      force_entity_alive=False) -> Entity:
        '''
        Creates an empty entity of type _TYPE_DONT_CARE.
        '''
        # TODO: move this somewhere better like class.
        _TYPE_DONT_CARE = 1

        # TODO [2020-06-01]: When we get to Entities-For-Realsies,
        # probably change to an EntityContext or something?..
        context = UnitTestContext(self)  # no initial sub-context

        # Set up an entity to load the component on to.
        eid = self.manager.entity.create(_TYPE_DONT_CARE,
                                         context)
        self.assertNotEqual(eid, EntityId.INVALID)
        entity = self.manager.entity.get(eid)
        self.assertTrue(entity)
        # Entity should not be alive just yet.
        self.assertNotEqual(entity.life_cycle, EntityLifeCycle.ALIVE)

        # Throw away entity creation events if desired.
        if clear_received_events:
            self.clear_events(clear_manager=clear_manager_event_queue)

        # Short-circuit entity to alive?
        if force_entity_alive:
            entity._life_cycled(EntityLifeCycle.ALIVE)

        return entity

    def create_component(self,
                         entity:                  Entity,
                         event:                   Event,
                         expected_component_type: Type[Component],
                         expected_events:         int  = 0,
                         clear_event_queue:       bool = True
                         ) -> Entity:
        '''
        Ensures event is for the entity, publishes it via
        self.trigger_events(event, expected_events=`expected_events`), and
        assumes it is an event that will result in a component being created on
        the entity.

        The event will be sent out to do its thing, then if
        `clear_event_queue` is set, we will call self.clear_events().

        Checks that the entity has a component attached of the
        `expected_component_type`.

        Finally, we will call ComponentManager.creation() in order to put the
        component into the ALIVE life-cycle.
        '''
        if event:
            # Event provided; just make sure it's for the right guy.
            self.assertEqual(event.id, entity.id)
            self.assertEqual(event.type, entity.type_id)

        else:
            # Fail - dunno how to proceed.
            self.fail("create_component got no event Cannot create identity. "
                      f"event: {event}, expected: {expected_component_type}, "
                      f"expected_events: {expected_events}, entity: {entity}")

        # We aren't registered to receive the reply, so don't expect anything.
        self.trigger_events(event, expected_events=0)

        # But clear it out just in cases and to be a good helper function.
        if clear_event_queue:
            self.clear_events()

        self.manager.component.creation(self.manager.time)
        component = entity.get(expected_component_type)
        # Not None, not Null(), not nothing except expected_component_type.
        self.assertIsInstance(component, expected_component_type)

    def create_identity(self,
                        entity:  Entity,
                        request:           Optional[IdentityRequest] = None,
                        data:              Optional[Dict[str, str]]  = None,
                        expected_events:   int                       = 0,
                        clear_event_queue: bool                      = True
                        ) -> Entity:
        '''
        Ensures (Code)IdentityRequest `identity` is for the entity, then does
        the necessary steps to get it attached to the entity.

        Provide /EITHER/ `request` or `data`.
          - If `request` is provided, it takes priority over `data`. We will
            force it to be for the EntityId/EntityType of `entity`.
          - If `data` is provided, we will create a CodeIdentityRequest with
            it.

        The IdentityRequest event will be sent out to do its thing, then if
        `clear_event_queue` is set, we will call self.clear_events().

        Finally, we will call ComponentManager.creation() in order to put the
        component into the ALIVE life-cycle.
        '''
        if request:
            # Request provided; just make sure it's for the right guy.
            self.assertEqual(request.id, entity.id)
            self.assertEqual(request.type_id, entity.type)
            event = request

        elif data:
            context = UnitTestContext(self)  # no initial sub-context

            # Create a request for our dude get an identity assigned via data
            # dictionary.
            event = CodeIdentityRequest(
                entity.id,
                entity.type_id,
                context,
                data)

        else:
            # Fail - dunno how to proceed.
            self.fail("create_identity got no IdentityRequest and no "
                      "identity data. Cannot create identity. request: "
                      f"{request}, data: {data}, entity: {entity}")

        self.create_component(entity,
                              event,
                              IdentityComponent,
                              expected_events=0,
                              clear_event_queue=True)

    def force_alive(self,
                    *ents_or_comps: Union[Entity, Component, Null]) -> None:
        '''
        Forces each entity or component to be in the ALIVE part
        of its life-cycle.
        '''
        for each in ents_or_comps:
            # Set ents and comps to ALIVE, make sure rest are Null?
            if isinstance(each, Entity):
                each._life_cycle = EntityLifeCycle.ALIVE
            elif isinstance(each, Component):
                each._life_cycle = ComponentLifeCycle.ALIVE
            else:
                self.assertIs(each, Null())
