# coding: utf-8

'''
Tests for component.py (ComponentManager class).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from veredi.zest import zmake
from veredi.base.context import UnitTestContext

from .event import EventManager
from .component import (ComponentManager,
                        ComponentEvent,
                        ComponentLifeEvent)
from .base.identity import ComponentId
from .base.component import (ComponentLifeCycle,
                             Component,
                             ComponentError)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Mockups
# -----------------------------------------------------------------------------

class CompOne(Component):
    pass


class CompTwo(CompOne):

    def _configure(self,
                   context):
        self.x = context.sub['unit-test-args']['x']
        self.y = context.sub['unit-test-args']['y']


class CompThree(Component):
    pass


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------


class Test_ComponentManager(unittest.TestCase):

    def setUp(self):
        self.config    = zmake.config()
        self.event_mgr = None
        self.finish_setUp()

    def finish_setUp(self):
        self.comp_mgr = ComponentManager(self.config, self.event_mgr)

        self.events_recv = {}

    def tearDown(self):
        self.config    = None
        self.event_mgr = None
        self.comp_mgr  = None

        self.events_recv = None

    def register_events(self):
        self.event_mgr.subscribe(ComponentEvent, self.event_comp_recv)
        self.event_mgr.subscribe(ComponentLifeEvent, self.event_comp_recv)

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
        self.assertTrue(self.comp_mgr)

    def test_create(self):
        self.assertEqual(self.comp_mgr._component_id.peek(),
                         ComponentId.INVALID)

        cid = self.comp_mgr.create(CompOne, None)
        self.assertNotEqual(cid, ComponentId.INVALID)

        self.assertEqual(len(self.comp_mgr._component_create), 1)
        self.assertEqual(len(self.comp_mgr._component_destroy), 0)
        self.assertEqual(len(self.comp_mgr._component_by_id), 1)

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

            event = self.events_recv[ComponentLifeEvent][0]
            self.assertIsNotNone(event)
            self.assertEqual(event.id, cid)
            self.assertEqual(event.type, ComponentLifeCycle.CREATING)
            self.assertIsNone(event.context)

        # Component should exist and be in CREATING state now...
        component = self.comp_mgr.get(cid)
        self.assertIsNotNone(component)
        self.assertIsInstance(component,
                              Component)
        self.assertEqual(component.id, cid)
        self.assertEqual(component.life_cycle,
                         ComponentLifeCycle.CREATING)

    def test_create_args(self):
        self.assertEqual(self.comp_mgr._component_id.peek(),
                         ComponentId.INVALID)

        context = UnitTestContext(
            self.__class__.__name__,
            'test_create_args',
            {'unit-test-args': {'x': 1, 'y':2}})

        cid = self.comp_mgr.create(CompTwo, context)
        self.assertNotEqual(cid, ComponentId.INVALID)

        # Component should exist and have its args assigned.
        component = self.comp_mgr.get(cid)
        self.assertIsNotNone(component)
        self.assertIsInstance(component,
                              CompTwo)
        self.assertEqual(component.life_cycle,
                         ComponentLifeCycle.CREATING)
        self.assertEqual(component.x, 1)
        self.assertEqual(component.y, 2)

    def test_destroy(self):
        self.assertEqual(self.comp_mgr._component_id.peek(),
                         ComponentId.INVALID)

        cid = 1
        self.comp_mgr.destroy(cid)
        # Component doesn't exist, so nothing happened.
        self.assertEqual(len(self.comp_mgr._component_create), 0)
        self.assertEqual(len(self.comp_mgr._component_destroy), 0)

        cid = self.comp_mgr.create(CompOne, None)
        # Now we should have a create...
        self.assertNotEqual(cid, ComponentId.INVALID)
        self.assertEqual(len(self.comp_mgr._component_create), 1)
        self.clear_events() # don't care about create event
        # ...a destroy...
        self.comp_mgr.destroy(cid)
        self.assertEqual(len(self.comp_mgr._component_destroy), 1)
        # ...and a DESTROYING state.
        component = self.comp_mgr.get(cid)
        self.assertIsNotNone(component)
        self.assertIsInstance(component,
                              CompOne)
        self.assertEqual(component.life_cycle,
                         ComponentLifeCycle.DESTROYING)

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

            event = self.events_recv[ComponentLifeEvent][0]
            self.assertIsNotNone(event)
            self.assertEqual(event.id, cid)
            self.assertEqual(event.type, ComponentLifeCycle.DESTROYING)
            self.assertIsNone(event.context)

    def test_creation(self):
        cid = self.comp_mgr.create(CompOne, None)
        self.assertNotEqual(cid, ComponentId.INVALID)

        # Component should exist and be in CREATING state now...
        component = self.comp_mgr.get(cid)
        self.assertIsNotNone(component)
        self.assertEqual(component.id, cid)
        self.assertEqual(component.life_cycle,
                         ComponentLifeCycle.CREATING)
        self.clear_events() # don't care about create event

        # Tick past creation to get new component finished.
        self.comp_mgr.creation(None)

        # Component should still exist and be in ALIVE state now.
        self.assertIsNotNone(component)
        self.assertIsInstance(component,
                              CompOne)
        self.assertEqual(component.id, cid)
        self.assertEqual(component.life_cycle,
                         ComponentLifeCycle.ALIVE)

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

            event = self.events_recv[ComponentLifeEvent][0]
            self.assertIsNotNone(event)
            self.assertEqual(event.id, cid)
            self.assertEqual(event.type, ComponentLifeCycle.ALIVE)
            self.assertIsNone(event.context)

    def test_destruction(self):
        cid = self.comp_mgr.create(CompOne, None)
        self.assertNotEqual(cid, ComponentId.INVALID)

        # Component should exist and be in CREATING state now...
        component = self.comp_mgr.get(cid)
        self.assertIsNotNone(component)
        self.assertEqual(component.id, cid)
        self.assertEqual(component.life_cycle,
                         ComponentLifeCycle.CREATING)

        # Now (ask for) destroy!
        self.comp_mgr.destroy(cid)
        self.clear_events() # don't care about create/destroy event

        # Tick past destruction to get poor new component DEAD.
        self.comp_mgr.destruction(None)

        # Component should not exist as far as ComponentManager cares,
        # and be in DEAD state now.
        self.assertIsNone(self.comp_mgr.get(cid))
        self.assertIsNotNone(component)
        self.assertIsInstance(component,
                              CompOne)
        self.assertEqual(component.id, cid)
        self.assertEqual(component.life_cycle,
                         ComponentLifeCycle.DEAD)

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

            event = self.events_recv[ComponentLifeEvent][0]
            self.assertIsNotNone(event)
            self.assertEqual(event.id, cid)
            self.assertEqual(event.type, ComponentLifeCycle.DEAD)
            self.assertIsNone(event.context)


class Test_ComponentManager_Events(Test_ComponentManager):
    def setUp(self):
        # Add EventManager so that tests in parent class will
        # generate/check events.
        self.config    = zmake.config()
        self.event_mgr = EventManager(self.config)
        self.finish_setUp()
        self.register_events()
