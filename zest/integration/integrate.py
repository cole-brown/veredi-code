# coding: utf-8

'''
Base Class for Integration Tests.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, List

import unittest

from veredi.base.null               import Null
from veredi.logger                  import log
from veredi.zest                    import zload
from veredi.zest.zpath              import TestType

from veredi.base.context            import VerediContext, UnitTestContext
from veredi.game.ecs.base.system    import System
from veredi.game.ecs.base.entity    import (Entity,
                                            EntityLifeCycle)
from veredi.game.ecs.base.identity  import EntityId
from veredi.game.ecs.base.component import (Component,
                                            ComponentLifeCycle)
from veredi.game.ecs.event          import Event
from veredi.game.data.event         import DataLoadedEvent
from veredi.game.ecs.meeting        import Meeting

from veredi.input.system            import InputSystem
from veredi.input.command.reg       import CommandRegistrationBroadcast

# from veredi.game.ecs.const        import DebugFlag


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Base Class
# -----------------------------------------------------------------------------

class IntegrationTest(unittest.TestCase):
    '''
    Base testing class with some setup and helpers.

    For testing integrations where EcsManagers, events, data, and multiple
    Systems are needed.
    '''

    def setUp(self) -> None:
        '''
        unittest.TestCase setUp function. Make one for your test class, and
        call stuff like so, possibly with more stuff:

        super().setUp()
        self.init_required(...)
        self.init_system(...)
        '''
        self.debugging:      bool          = False
        self.events:         List[Event]   = []
        self.reg_open:       CommandRegistrationBroadcast = None
        self.manager:        Meeting       = None
        self.context:        VerediContext = None
        self.input_system:   InputSystem   = None

    def init_required(self) -> None:
        '''
        Calls zload.set_up to create Meeting of EcsManagers, and a context from
        a config file.
        '''
        (self.manager,
         self.context, _) = zload.set_up(self.__class__.__name__,
                                         'setUp',
                                         self.debugging,
                                         test_type=TestType.INTEGRATION)

    def init_input(self) -> None:
        '''
        Creates/initializes InputSystem and registers for
        CommandRegistrationBroadcast.
        '''
        self.input_system = self.init_a_system(InputSystem)
        self.manager.event.subscribe(CommandRegistrationBroadcast,
                                     self.event_cmd_reg)

    def init_many_systems(self, *sys_types: System) -> None:
        '''
        Initializes several systems you need but don't need to hang on to
        directly for your test.

        NOTE: Already created RepositorySystem, CodecSystem, DataSystem in
        init_required.
        '''
        sids = zload.create_systems(self.manager.system,
                                    self.context,
                                    *sys_types)
        return sids

    def init_a_system(self, sys_type: System) -> System:
        '''
        Initializes a system and returns its object.
        '''
        sid = zload.create_system(self.manager.system,
                                  self.context,
                                  sys_type)
        return self.manager.system.get(sid)

    def tearDown(self) -> None:
        self.debugging      = False
        self.apoptosis()
        self.events         = None
        self.reg_open       = None
        self.manager        = None
        self.context        = None
        self.input_system   = None

    def apoptosis(self) -> None:
        self.manager.time.apoptosis()
        self.manager.event.apoptosis(self.manager.time)
        self.manager.component.apoptosis(self.manager.time)
        self.manager.entity.apoptosis(self.manager.time)
        self.manager.system.apoptosis(self.manager.time)

    # -------------------------------------------------------------------------
    # Event Helpers / Handlers
    # -------------------------------------------------------------------------

    def sub_loaded(self) -> None:
        '''
        Include this in your _sub_events_test or elsewhere to receive
        DataLoadedEvent.
        '''
        self.manager.event.subscribe(DataLoadedEvent, self.event_loaded)

    def _sub_events_test(self) -> None:
        '''
        Subscribe to the events your want to be the (or just a)
        receiver/handler for here. Called from event_setup() for tests that
        want to do events.

        e.g.:
        self.manager.event.subscribe(JeffEvent,
                                     self.event_cmd_jeff)
        '''
        pass

    def _sub_events_systems(self) -> None:
        '''
        This has all systems that SystemManager knows about (which /should/ be
        every single one) get their subscribe() call.
        '''
        with log.LoggingManager.on_or_off(self.debugging):
            # Let all our pieces set up their subs.
            self.manager.time.subscribe(self.manager.event)
            self.manager.component.subscribe(self.manager.event)
            self.manager.entity.subscribe(self.manager.event)
            self.manager.system.subscribe(self.manager.event)

    def event_setup(self) -> None:
        '''
        Rolls _sub_events_* into one call.
        '''
        self._sub_events_test()
        self._sub_events_systems()

    def clear_events(self) -> None:
        '''
        Clears out the `self.events` queue.
        '''
        self.events.clear()

    def event_now(self,
                  event:         Event,
                  num_publishes: int = 3) -> None:
        '''
        Notifies the event for immediate action. Which /should/ cause something
        to process it and queue up an event? So we publish() in order to get
        that one sent out. Which /may/ cause something to process that and
        queue up another. So we'll publish as many times as asked in
        `num_publishes`.

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
        Sanity asserts on inputs, then we call event_now() to immediately
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
        self.event_now(event, num_publishes)

        if expected_events == 0:
            self.assertFalse(self.events)
            self.assertEqual(len(self.events), 0)
            return

        self.assertTrue(self.events)
        self.assertEqual(len(self.events), expected_events)

    def event_loaded(self, event: Event) -> None:
        '''
        Receiver for DataLoadedEvent.

        Does not work unless self.sub_loaded() was called in your derived
        class.
        '''
        self.events.append(event)

    def event_cmd_reg(self, event):
        self.assertIsInstance(event,
                              CommandRegistrationBroadcast)
        self.reg_open = event

        self.make_commands(event)

    # -------------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------------

    def allow_registration(self):
        if self.reg_open:
            return

        event = self.input_system._commander.registration(
            self.input_system.id,
            Null())
        self.trigger_events(event,
                            expected_events=0,
                            num_publishes=1)
        # Now registration is open.
        self.assertTrue(self.reg_open)

    def make_commands(self, event: CommandRegistrationBroadcast) -> None:
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
        _TYPE_DONT_CARE = 1

        # TODO [2020-06-01]: When we get to Entities-For-Realsies,
        # probably change to an EntityContext or something...
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

    # -------------------------------------------------------------------------
    # Examples
    # -------------------------------------------------------------------------
    # Probably should delete sooner rather than later. After one or two
    # integration tests use this. Blocks of commented out code aren't good for
    # examples for long before they rot...

    # def load_request(self, type):
    #     '''
    #     A load request example.
    #     '''
    #     ctx = self.context.spawn(DataLoadContext,
    #                              'unit-testing', None,
    #                              type,
    #                              'test-campaign')
    #     if type == DataGameContext.Type.MONSTER:
    #         ctx.sub['family'] = 'dragon'
    #         ctx.sub['monster'] = 'aluminum dragon'
    #     else:
    #         raise LoadError(
    #             f"No DataGameContext.Type to ID conversion for: {type}",
    #             None,
    #             ctx)
    #
    #     event = DataLoadRequest(
    #         42,
    #         ctx.type,
    #         ctx)
    #
    #     return event

    # def test_init(self):
    #     self.assertTrue(self.manager)
    #     self.assertTrue(self.context)
    #     self.assertTrue(self.manager.system)
    #
    #     # All your stuff here maybe.

    # def test_set_up(self):
    #     self.set_up_subs()
    #
    #     # Make our request event.
    #     request = self.load_request(DataGameContext.Type.MONSTER)
    #     self.assertFalse(self.events)
    #
    #     # Ask for our aluminum_dragon to be loaded.
    #     self.make_it_so(request)
    #     self.assertTrue(self.events)
    #     self.assertEqual(len(self.events), 1)
    #
    #     # And we have a DataLoadedEvent!
    #     loaded_event = self.events[0]
    #     self.assertIsInstance(loaded_event, DataLoadedEvent)
    #
    #     # Did it make a thing?
    #     self.assertNotEqual(loaded_event.component_id, ComponentId.INVALID)
    #
    #     # Get the thing and check it.
    #     component = self.manager.component.get(loaded_event.component_id)
    #     self.assertIsNotNone(component)
    #     self.assertEqual(loaded_event.component_id,
    #                      component.id)
    #     self.assertIsInstance(component, health.HealthComponent)
    #
    #     health_data = component.persistent
    #     self.assertEqual(health_data['health']['current']['permanent'],
    #                      200)
    #     self.assertEqual(health_data['health']['maximum']['hit-points'],
    #                      200)
    #     self.assertEqual(health_data['health']['death']['hit-points'],
    #                      -50)
    #     self.assertEqual(health_data['health']['resistance']['slashing'],
    #                      10)
    #     self.assertEqual(health_data['health']['resistance']['cold'],
    #                      3)
    #     self.assertEqual(health_data['health']['immunity']['bludgeoning'],
    #                      True)
