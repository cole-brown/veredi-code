# coding: utf-8

'''
Base class for testing an ECS System or Engine. Used by ZestSystem and
ZestEngine. No one currently uses this directly [2020-08-24].
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, List, Iterable

from veredi.logger                      import log
from .unit                              import ZestBase
from ..                                 import zload
from ..zpath                            import TestType
from veredi.base.context                import VerediContext, UnitTestContext

from veredi.base.null                   import Null
from veredi.data.config.config          import Configuration

from veredi.game.ecs.base.system        import System
from veredi.game.ecs.base.entity        import (Entity,
                                                EntityLifeCycle)
from veredi.game.ecs.base.identity      import EntityId
from veredi.game.ecs.base.component     import (Component,
                                                ComponentLifeCycle)
from veredi.game.ecs.event              import Event
from veredi.game.data.event             import DataLoadedEvent

from veredi.game.ecs.time               import TimeManager
from veredi.game.ecs.event              import EventManager
from veredi.game.ecs.component          import ComponentManager
from veredi.game.ecs.entity             import EntityManager
from veredi.game.ecs.system             import SystemManager
from veredi.game.engine                 import Engine
from veredi.game.ecs.meeting            import Meeting

from veredi.interface.input.system      import InputSystem
from veredi.interface.input.command.reg import CommandRegistrationBroadcast

from veredi.interface.output.system     import OutputSystem


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
    Test should set this to desired during setUp().

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

        self.events:         List[Event]   = []
        '''
        Simple queue for receiving events.
        '''

        self.reg_open:       CommandRegistrationBroadcast = None
        '''
        Separate variable for holding a received command registration
        broadcast event.
        '''

        # ------------------------------
        # ECS
        # ------------------------------

        self.manager:        Meeting       = None
        '''
        If class uses ECS, the Meeting of ECS Managers should go here.
        zload.set_up() can provide this.
        '''

        self.context:        VerediContext = None
        '''
        If class uses a set-up/config context, it should go here.
        zload.set_up() can provide this.
        '''

        self.config:         Configuration = None
        '''
        If class uses a special config, it should be saved here so set-up(s)
        can use it.
        '''

        # ------------------------------
        # Engine
        # ------------------------------

        self.engine:         Engine        = None
        '''
        The ECS Game Engine.
        zload.set_up() can provide this.
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
                    # Will be class._TEST_TYPE if None:
                    test_type:         Optional[TestType]            = None,
                    # Optional ECS:
                    require_engine:    Optional[bool]                = None,
                    desired_systems:   Iterable[zload.SysCreateType] = None,
                    # Optional to pass in - else we'll make:
                    configuration:     Optional[Configuration]       = None,
                    time_manager:      Optional[TimeManager]         = None,
                    event_manager:     Optional[EventManager]        = None,
                    component_manager: Optional[ComponentManager]    = None,
                    entity_manager:    Optional[EntityManager]       = None,
                    system_manager:    Optional[SystemManager]       = None,
                    # Optional to pass in - else we'll make  if asked:
                    engine:            Optional[Engine]              = None
                    ) -> None:
        '''
        Calls zload.set_up to create Meeting of EcsManagers, and a context from
        a config file.

        None of the args are needed, usually.
          - `test_type` will become `self._TEST_TYPE` if it is None.
          - `require_engine` will become `self._REQUIRE_ENGINE` if it is None.
        '''
        if test_type is None:
            test_type = self._TEST_TYPE
        if require_engine is None:
            require_engine = self._REQUIRE_ENGINE
        if configuration is None and self.config:
            configuration = self.config

        (self.manager, self.engine,
         self.context, _) = zload.set_up(self.__class__.__name__,
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
        Include this in your _sub_events_test or elsewhere to receive
        DataLoadedEvent.
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
            if self.manager.time:
                self.manager.time.subscribe(self.manager.event)

            if self.manager.component:
                self.manager.component.subscribe(self.manager.event)

            if self.manager.entity:
                self.manager.entity.subscribe(self.manager.event)

            if self.manager.system:
                self.manager.system.subscribe(self.manager.event)

    # -------------------------------------------------------------------------
    # System Creation Helpers
    # -------------------------------------------------------------------------

    def init_many_systems(self, *sys_types: System) -> None:
        '''
        Initializes several systems you need but don't need to hang on to
        directly for your test.

        NOTE: Already created RepositorySystem, CodecSystem, DataSystem in
        set_up_ecs() if your test called that.
        '''
        sids = zload.create_systems(self.manager.system,
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
            self.__class__.__name__,
            'test_create',
            {}
            if not kwargs else
            {'system': kwargs})

        sid = self.manager.system.create(sys_type, context)
        return self.manager.system.get(sid)

    # -------------------------------------------------------------------------
    # Event Helpers
    # -------------------------------------------------------------------------

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

    def create_entity(self) -> Entity:
        '''
        Creates an empty entity of type _TYPE_DONT_CARE.
        '''
        # TODO: move this somewhere better like class.
        _TYPE_DONT_CARE = 1

        # TODO [2020-06-01]: When we get to Entities-For-Realsies,
        # probably change to an EntityContext or something?..
        context = UnitTestContext(
            self.__class__.__name__,
            'test_create',
            {})  # no initial sub-context

        # Set up an entity to load the component on to.
        eid = self.manager.entity.create(_TYPE_DONT_CARE,
                                         context)
        self.assertNotEqual(eid, EntityId.INVALID)
        entity = self.manager.entity.get(eid)
        self.assertTrue(entity)

        return entity

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
