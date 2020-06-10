# coding: utf-8

'''
Integration Test for data load path.

Start with the data "saved" and "in the repository" (i.e. a file on disk).
Create a DataLoadedEvent and kick it off, then sit back and wait for our
DataSystem, Repository, Codec, DataEvents, etc. to do Stuff and make Things
happen.

We will end up with a Component and verify its data.

This Integration Test avoids using the game Engine. All this is event-driven
and doesn't really need the engine.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from veredi.logger                      import log
from veredi.data.context                import DataGameContext, DataLoadContext
from veredi.data.exceptions             import LoadError
from veredi.zest                        import zpath, zmake, zontext

from veredi.game.ecs.time               import TimeManager
from veredi.game.ecs.event              import EventManager
from veredi.game.ecs.component          import ComponentManager
from veredi.game.ecs.entity             import EntityManager
from veredi.game.ecs.system             import SystemManager
from veredi.game.ecs.const              import DebugFlag

from veredi.game.ecs.base.identity      import ComponentId

from veredi.game.data.system            import DataSystem
from veredi.game.data.repository.system import RepositorySystem
from veredi.game.data.codec.system      import CodecSystem
from veredi.game.data.event             import DataLoadRequest, DataLoadedEvent


# Make sure this guy registers himself.
from veredi.rules.d20                   import health


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_DataLoad_DiskToGame(unittest.TestCase):

    def setUp(self):
        self.events         = []
        self.debug          = False
        self.config         = zmake.config(zpath.TestType.INTEGRATION)
        self.context        = zontext.real_config(
            self.__class__.__name__,
            'setUp',
            config=self.config,
            test_type=zpath.TestType.INTEGRATION)

        self.time_manager   = TimeManager()
        self.event_manager  = EventManager(self.config)
        self.comp_manager   = ComponentManager(self.config,
                                               self.event_manager)
        self.entity_manager = EntityManager(self.config,
                                            self.event_manager,
                                            self.comp_manager)
        self.system_manager = SystemManager(self.config,
                                            self.time_manager,
                                            self.event_manager,
                                            self.comp_manager,
                                            self.entity_manager,
                                            DebugFlag.UNIT_TESTS)
        with log.LoggingManager.on_or_off(self.debug):
            self.create_systems(RepositorySystem, CodecSystem, DataSystem)

    def tearDown(self):
        self.debug          = False
        self.apoptosis()
        self.events         = None
        self.config         = None
        self.context        = None
        self.time_manager   = None
        self.event_manager  = None
        self.comp_manager   = None
        self.entity_manager = None
        self.system_manager = None

    def apoptosis(self):
        self.time_manager.apoptosis()
        self.event_manager.apoptosis(self.time_manager)
        self.comp_manager.apoptosis(self.time_manager)
        self.entity_manager.apoptosis(self.time_manager)
        self.system_manager.apoptosis(self.time_manager)

    def create_system(self, sys_type, *args, **kwargs):
        sub = self.context.sub
        if kwargs:
            sub['system'] = kwargs
        else:
            sub.pop('system', None)

        sid = self.system_manager.create(sys_type,
                                         self.context)

        sub.pop('system', None)
        return sid

    def create_systems(self, *args, **kwargs):
        '''
        e.g.:
          self.create_systems(SomeSystem)
          self.create_systems((SomeSystem, arg1, arg2))
          self.create_systems((SomeSystem, arg1, arg2), TwoSystem)
        '''
        sids = []
        for each in args:
            if isinstance(each, tuple):
                sids.append(self.create_system(each[0], self.context,
                                               *each[1:], **each[2:]))
            else:
                sids.append(self.create_system(each, self.context))

        return sids

    def sub_loaded(self):
        self.event_manager.subscribe(DataLoadedEvent, self.event_loaded)

    def set_up_subs(self):
        with log.LoggingManager.on_or_off(self.debug):
            # Let all our pieces set up their subs.
            self.time_manager.subscribe(self.event_manager)
            self.comp_manager.subscribe(self.event_manager)
            self.entity_manager.subscribe(self.event_manager)
            self.system_manager.subscribe(self.event_manager)

            # And the final event.
            self.sub_loaded()

    def event_loaded(self, event):
        self.events.append(event)

    def load_request(self, type):
        ctx = self.context.spawn(DataLoadContext,
                                 'unit-testing', None,
                                 type,
                                 'test-campaign')
        if type == DataGameContext.Type.MONSTER:
            ctx.sub['family'] = 'dragon'
            ctx.sub['monster'] = 'aluminum dragon'
        else:
            raise LoadError(
                f"No DataGameContext.Type to ID conversion for: {type}",
                None,
                ctx)

        event = DataLoadRequest(
            42,
            ctx.type,
            ctx)

        return event

    def make_it_so(self, event, num_publishes=3):
        '''
        Notifies the event for immediate action. Which /should/ cause something
        to process it and queue up an event. So we publish() in order to get
        that one sent out. Which /should/ cause something to process that and
        queue up another. So we'll publish as many times as asked. Then assert
        we ended up with an event in our self.events list.
        '''
        with log.LoggingManager.on_or_off(self.debug):
            self.event_manager.notify(event, True)

            for each in range(num_publishes):
                self.event_manager.publish()

        self.assertTrue(self.events)

    def test_init(self):
        self.assertTrue(self.config)
        self.assertTrue(self.time_manager)
        self.assertTrue(self.event_manager)
        self.assertTrue(self.comp_manager)
        self.assertTrue(self.entity_manager)
        self.assertTrue(self.system_manager)

    def test_set_up(self):
        self.set_up_subs()

        # Make our request event.
        request = self.load_request(DataGameContext.Type.MONSTER)
        self.assertFalse(self.events)

        # Ask for our aluminum_dragon to be loaded.
        self.make_it_so(request)
        self.assertTrue(self.events)
        self.assertEqual(len(self.events), 1)

        # And we have a DataLoadedEvent!
        loaded_event = self.events[0]
        self.assertIsInstance(loaded_event, DataLoadedEvent)

        # Did it make a thing?
        self.assertNotEqual(loaded_event.component_id, ComponentId.INVALID)

        # Get the thing and check it.
        component = self.comp_manager.get(loaded_event.component_id)
        self.assertIsNotNone(component)
        self.assertEqual(loaded_event.component_id,
                         component.id)
        self.assertIsInstance(component, health.HealthComponent)

        health_data = component.persistent
        self.assertEqual(health_data['health']['current']['permanent'],
                         200)
        self.assertEqual(health_data['health']['maximum']['hit-points'],
                         200)
        self.assertEqual(health_data['health']['death']['hit-points'],
                         -50)
        self.assertEqual(health_data['health']['resistance']['slashing'],
                         10)
        self.assertEqual(health_data['health']['resistance']['cold'],
                         3)
        self.assertEqual(health_data['health']['immunity']['bludgeoning'],
                         True)
