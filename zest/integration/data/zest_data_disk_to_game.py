# coding: utf-8

'''Integration Test for data load path.

Start with the data "saved" and "in the repository" (i.e. a file on disk).
Create a DataLoadedEvent and kick it off, then sit back and wait for our
DataSystem, Repository, Codec, DataEvents, etc. to do Stuff and make Things
happen.

We will end up with a Component and verify its data.

This Integration Test avoids using the game Engine. All this is event-driven and
doesn't really need the engine.

'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from veredi.logger                      import log
from veredi.base.const                  import VerediHealth
from veredi.base.context                import DataGameContext, DataLoadContext
from veredi.zest                        import zmake, zpath

from veredi.game.ecs.time               import TimeManager
from veredi.game.ecs.event              import EventManager
from veredi.game.ecs.component          import ComponentManager
from veredi.game.ecs.entity             import EntityManager
from veredi.game.ecs.system             import SystemManager
from veredi.game.ecs.const              import DebugFlag

from veredi.game.ecs.base.identity      import (ComponentId,
                                                EntityId,
                                                SystemId)
from veredi.game.ecs.base.component     import Component
from veredi.game.ecs.base.entity        import Entity
from veredi.game.ecs.base.system        import System

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
        self.config         = zmake.config(zpath.TestType.INTEGRATION)
        self.time_manager   = TimeManager()
        self.event_manager  = EventManager(self.config)
        self.comp_manager   = ComponentManager(self.config,
                                               self.event_manager)
        self.entity_manager = EntityManager(self.config,
                                            self.event_manager,
                                            self.comp_manager)
        self.system_manager = SystemManager(self.config,
                                            self.event_manager,
                                            self.comp_manager,
                                            DebugFlag.UNIT_TESTS)
        self.create_systems(RepositorySystem, CodecSystem, DataSystem)

    def tearDown(self):
        self.apoptosis()
        self.events         = None
        self.config         = None
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

    def create_systems(self, *args):
        '''
        e.g.:
          self.create_systems(SomeSystem)
          self.create_systems((SomeSystem, arg1, arg2))
          self.create_systems((SomeSystem, arg1, arg2), TwoSystem)
        '''
        sids = []
        for each in args:
            if isinstance(each, tuple):
                sids.append(self.system_manager.create(each[0], *each[1:]))
            else:
                sids.append(self.system_manager.create(each))

        return sids

    def sub_loaded(self):
        self.event_manager.subscribe(DataLoadedEvent, self.event_loaded)

    def set_up_subs(self, debug=False):
        log_lvl_mgr = (log.LoggingManager.full_blast()
                       if debug else
                       log.LoggingManager.ignored())

        with log_lvl_mgr:
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
        ctx = DataLoadContext('unit-testing', type, 'test-campaign')
        if type == DataGameContext.Type.MONSTER:
            ctx.sub['family'] = 'dragon'
            ctx.sub['monster'] = 'aluminum dragon'
        else:
            raise exceptions.LoadError(
                f"No DataGameContext.Type to ID conversion for: {type}",
                None,
                self.context.merge(context))

        event = DataLoadRequest(
            42,
            ctx.type,
            ctx)

        return event

    def make_it_so(self, event, num_publishes=3, debug=False):
        '''
        Notifies the event for immediate action. Which /should/ cause something
        to process it and queue up an event. So we publish() in order to get
        that one sent out. Which /should/ cause something to process that and
        queue up another. So we'll publish as many times as asked. Then assert
        we ended up with an event in our self.events list.
        '''
        log_lvl_mgr = (log.LoggingManager.full_blast()
                       if debug else
                       log.LoggingManager.ignored())

        with log_lvl_mgr:
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
        full_debug = False
        self.set_up_subs(debug=full_debug)

        # Make our request event.
        request = self.load_request(DataGameContext.Type.MONSTER)
        self.assertFalse(self.events)

        # Ask for our aluminum_dragon to be loaded.
        self.make_it_so(request, debug=full_debug)
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
