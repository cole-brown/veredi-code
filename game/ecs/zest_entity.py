# coding: utf-8

'''
Tests for entity.py (EntityManager class).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from .event import EventManager
from .component import (ComponentManager,
                        ComponentEvent,
                        ComponentLifeEvent)
from .entity import (EntityManager,
                     EntityEvent,
                     EntityEventType,
                     EntityLifeEvent)
from .base.identity import (ComponentId,
                            EntityId)
from .base.component import (Component,
                             ComponentError)
from .base.entity import (Entity,
                          EntityLifeCycle)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Mockups
# -----------------------------------------------------------------------------

class CompOne(Component):
    pass

class CompTwo(Component):
    pass

class CompThree(Component):
    pass


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_EntityManager(unittest.TestCase):
    _TYPE_DONT_CARE = 1

    def setUp(self):
        self.event_mgr  = None
        self.finish_setUp()

    def finish_setUp(self):
        self.comp_mgr   = ComponentManager(self.event_mgr)
        self.entity_mgr = EntityManager(self.event_mgr, self.comp_mgr)

        self.events_recv = {}

    def tearDown(self):
        self.event_mgr   = None
        self.comp_mgr    = None
        self.entity_mgr  = None
        self.events_recv = None

    def register_events(self):
        self.event_mgr.subscribe(EntityEvent, self.event_comp_recv)
        self.event_mgr.subscribe(EntityLifeEvent, self.event_comp_recv)

    def clear_events(self):
        self.events_recv.clear()
        if self.event_mgr:
            self.event_mgr._events.clear()

    def event_comp_recv(self, event):
        if not self.events_recv:
            self.events_recv = {}
        self.events_recv.setdefault(type(event), []).append(event)

    def do_events(self):
        return bool(self.comp_mgr._event_manager)

    def test_init(self):
        self.assertTrue(self.entity_mgr)

    def test_create(self):
        self.assertEqual(self.entity_mgr._entity_id.peek(),
                         EntityId.INVALID)

        eid = self.entity_mgr.create(self._TYPE_DONT_CARE, CompOne(0), CompTwo(1))
        self.assertNotEqual(eid, EntityId.INVALID)

        self.assertEqual(len(self.entity_mgr._entity_create), 1)
        self.assertEqual(len(self.entity_mgr._entity_destroy), 0)
        self.assertEqual(len(self.entity_mgr._entity), 1)

        if self.do_events():
            num_events = 0
            for ev_type in (self.events_recv or ()):
                num_events += len(self.events_recv[ev_type])
            self.assertEqual(num_events, 0)
            self.assertTrue(len(self.event_mgr._events) > 0)

            self.event_mgr.publish()
            num_events = 0
            for ev_type in (self.events_recv or ()):
                num_events += len(self.events_recv[ev_type])
            self.assertEqual(num_events, 1)

            event = self.events_recv[EntityLifeEvent][0]
            self.assertIsNotNone(event)
            self.assertEqual(event.id, eid)
            self.assertEqual(event.type, EntityLifeCycle.CREATING)
            self.assertIsNone(event.context)

        # Entity should only have the components we asked for.
        entity = self.entity_mgr.get(eid)
        self.assertIsNotNone(entity)
        self.assertIsInstance(entity,
                              Entity)
        self.assertTrue(entity.contains({CompOne, CompTwo}))
        self.assertEqual(entity.life_cycle,
                         EntityLifeCycle.CREATING)

    def test_destroy(self):
        self.assertEqual(self.entity_mgr._entity_id.peek(),
                         EntityId.INVALID)

        # destroy non-existant == no-op
        eid = 1
        self.entity_mgr.destroy(eid)
        self.assertEqual(len(self.entity_mgr._entity), 0)
        self.assertEqual(len(self.entity_mgr._entity_create), 0)
        self.assertEqual(len(self.entity_mgr._entity_destroy), 0)

        eid = self.entity_mgr.create(self._TYPE_DONT_CARE, CompOne(0), CompTwo(1))
        self.assertNotEqual(eid, EntityId.INVALID)
        # Now we should have a create...
        self.assertEqual(len(self.entity_mgr._entity), 1)
        self.assertEqual(len(self.entity_mgr._entity_create), 1)
        self.clear_events() # don't care about create event
        # ...a destroy...
        self.entity_mgr.destroy(eid)
        self.assertEqual(len(self.entity_mgr._entity_destroy), 1)
        # ...and a DESTROYING state.
        entity = self.entity_mgr.get(eid)
        self.assertIsNotNone(entity)
        self.assertIsInstance(entity,
                              Entity)
        self.assertEqual(entity.life_cycle,
                         EntityLifeCycle.DESTROYING)

        if self.do_events():
            num_events = 0
            for ev_type in (self.events_recv or ()):
                num_events += len(self.events_recv[ev_type])
            self.assertEqual(num_events, 0)
            self.assertTrue(len(self.event_mgr._events) > 0)

            self.event_mgr.publish()
            num_events = 0
            for ev_type in (self.events_recv or ()):
                num_events += len(self.events_recv[ev_type])
            self.assertEqual(num_events, 1)

            event = self.events_recv[EntityLifeEvent][0]
            self.assertIsNotNone(event)
            self.assertEqual(event.id, eid)
            self.assertEqual(event.type, EntityLifeCycle.DESTROYING)
            self.assertIsNone(event.context)

    def test_add(self):
        self.assertEqual(self.entity_mgr._entity_id.peek(),
                         EntityId.INVALID)

        eid = self.entity_mgr.create(self._TYPE_DONT_CARE, CompOne(0), CompTwo(1))
        self.assertNotEqual(eid, EntityId.INVALID)

        # Entity should only have the components we asked for.
        entity = self.entity_mgr.get(eid)
        self.assertIsInstance(entity,
                              Entity)
        self.assertTrue(entity.contains({CompOne, CompTwo}))
        self.clear_events() # don't care about previous events

        # Now we add a third
        self.entity_mgr.add(eid, CompThree(2))

        # And the Entity should now have that as well.
        entity = self.entity_mgr.get(eid)
        self.assertIsInstance(entity,
                              Entity)
        self.assertTrue(entity.contains({CompOne, CompTwo, CompThree}))

        if self.do_events():
            num_events = 0
            for ev_type in (self.events_recv or ()):
                num_events += len(self.events_recv[ev_type])
            self.assertEqual(num_events, 0)
            self.assertTrue(len(self.event_mgr._events) > 0)

            self.event_mgr.publish()
            num_events = 0
            for ev_type in (self.events_recv or ()):
                num_events += len(self.events_recv[ev_type])
            self.assertEqual(num_events, 1)

            event = self.events_recv[EntityEvent][0]
            self.assertIsNotNone(event)
            self.assertEqual(event.id, eid)
            self.assertEqual(event.type, EntityEventType.COMPONENT_ADD)
            self.assertIsNone(event.context)

    def test_remove(self):
        self.assertEqual(self.entity_mgr._entity_id.peek(),
                         EntityId.INVALID)

        comp1 = CompOne(1)
        comp2 = CompTwo(2)
        eid = self.entity_mgr.create(self._TYPE_DONT_CARE, comp1, comp2)
        self.assertNotEqual(eid, EntityId.INVALID)

        # Entity should have the components we asked for.
        entity = self.entity_mgr.get(eid)
        self.assertIsInstance(entity,
                              Entity)
        self.assertTrue(entity.contains({CompOne, CompTwo}))
        self.clear_events() # don't care about create event

        # Now we remove one...
        self.entity_mgr.remove(eid, type(comp2))

        # And the Entity should now have just the one.
        entity = self.entity_mgr.get(eid)
        self.assertIsInstance(entity,
                              Entity)
        self.assertFalse(entity.contains({CompOne, CompTwo}))
        self.assertFalse(entity.contains({CompTwo}))
        self.assertTrue(entity.contains({CompOne}))

        if self.do_events():
            num_events = 0
            for ev_type in (self.events_recv or ()):
                num_events += len(self.events_recv[ev_type])
            self.assertEqual(num_events, 0)
            self.assertTrue(len(self.event_mgr._events) > 0)

            self.event_mgr.publish()
            num_events = 0
            for ev_type in (self.events_recv or ()):
                num_events += len(self.events_recv[ev_type])
            self.assertEqual(num_events, 1)

            event = self.events_recv[EntityEvent][0]
            self.assertIsNotNone(event)
            self.assertEqual(event.id, eid)
            self.assertEqual(event.type, EntityEventType.COMPONENT_REMOVE)
            self.assertIsNone(event.context)

    def test_creation(self):
        self.assertEqual(self.entity_mgr._entity_id.peek(),
                         EntityId.INVALID)

        comp1 = CompOne(1)
        comp2 = CompTwo(2)
        eid = self.entity_mgr.create(self._TYPE_DONT_CARE, comp1, comp2)
        self.assertNotEqual(eid, EntityId.INVALID)

        # Entity should exist and be in CREATING state now...
        entity = self.entity_mgr.get(eid)
        self.assertIsNotNone(entity)
        self.assertEqual(entity.id, eid)
        self.assertEqual(entity.life_cycle,
                         EntityLifeCycle.CREATING)
        self.clear_events() # don't care about create event

        # Tick past creation to get new entity finished.
        self.entity_mgr.creation(None)

        # Entity should still exist and be in ALIVE state now.
        self.assertIsNotNone(entity)
        self.assertIsInstance(entity,
                              Entity)
        self.assertEqual(entity.id, eid)
        self.assertEqual(entity.life_cycle,
                         EntityLifeCycle.ALIVE)

        if self.do_events():
            num_events = 0
            for ev_type in (self.events_recv or ()):
                num_events += len(self.events_recv[ev_type])
            self.assertEqual(num_events, 0)
            self.assertTrue(len(self.event_mgr._events) > 0)

            self.event_mgr.publish()
            num_events = 0
            for ev_type in (self.events_recv or ()):
                num_events += len(self.events_recv[ev_type])
            self.assertEqual(num_events, 1)

            event = self.events_recv[EntityLifeEvent][0]
            self.assertIsNotNone(event)
            self.assertEqual(event.id, eid)
            self.assertEqual(event.type, EntityLifeCycle.ALIVE)
            self.assertIsNone(event.context)

    def test_destruction(self):
        self.assertEqual(self.entity_mgr._entity_id.peek(),
                         EntityId.INVALID)

        # create so we can destroy...
        eid = self.entity_mgr.create(self._TYPE_DONT_CARE, CompOne(2), CompTwo(0))
        self.assertNotEqual(eid, EntityId.INVALID)
        self.entity_mgr.creation(None)
        entity = self.entity_mgr.get(eid)
        self.assertTrue(entity)
        self.assertTrue(entity.contains({CompOne, CompTwo}))

        # Now (ask for) destroy!
        self.entity_mgr.destroy(eid)
        self.clear_events() # don't care about create/destroy event

        # Now (actually do) destroy!
        self.entity_mgr.destruction(None)

        # EntityManager should no longer have them...
        self.assertIsNone(self.entity_mgr.get(eid))
        # ...and they should be dead (via our old handle).
        self.assertEqual(entity.life_cycle,
                         EntityLifeCycle.DEAD)

        if self.do_events():
            num_events = 0
            for ev_type in (self.events_recv or ()):
                num_events += len(self.events_recv[ev_type])
            self.assertEqual(num_events, 0)
            self.assertTrue(len(self.event_mgr._events) > 0)

            self.event_mgr.publish()
            num_events = 0
            for ev_type in (self.events_recv or ()):
                num_events += len(self.events_recv[ev_type])
            self.assertEqual(num_events, 1)

            event = self.events_recv[EntityLifeEvent][0]
            self.assertIsNotNone(event)
            self.assertEqual(event.id, eid)
            self.assertEqual(event.type, EntityLifeCycle.DEAD)
            self.assertIsNone(event.context)


class Test_EntityManager_Events(Test_EntityManager):
    def setUp(self):
        # Add EventManager so that tests in parent class will
        # generate/check events.
        self.event_mgr = EventManager()
        self.finish_setUp()
        self.register_events()
