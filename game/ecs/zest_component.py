# coding: utf-8

'''
Tests for component.py (ComponentManager class).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from .component import ComponentManager
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
    def __init__(self, component_id, *args, x=None, y=None, **kwargs):
        super().__init__(component_id, *args, **kwargs)
        self.x = x
        self.y = y

class CompThree(Component):
    pass


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_ComponentManager(unittest.TestCase):

    def setUp(self):
        self.comp_mgr = ComponentManager()

    def tearDown(self):
        self.comp_mgr = None

    def test_init(self):
        self.assertTrue(self.comp_mgr)

    def test_create(self):
        self.assertEqual(self.comp_mgr._component_id.peek(),
                         ComponentId.INVALID)

        cid = self.comp_mgr.create(CompOne)
        self.assertNotEqual(cid, ComponentId.INVALID)

        self.assertEqual(len(self.comp_mgr._component_create), 1)
        self.assertEqual(len(self.comp_mgr._component_destroy), 0)
        self.assertEqual(len(self.comp_mgr._component_by_id), 1)

        # TODO EVENT HERE?

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

        cid = self.comp_mgr.create(CompTwo, x=1, y=2)
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

        cid = self.comp_mgr.create(CompOne)
        # Now we should have a create...
        self.assertNotEqual(cid, ComponentId.INVALID)
        self.assertEqual(len(self.comp_mgr._component_create), 1)
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

        # TODO EVENT HERE?

    def test_creation(self):
        cid = self.comp_mgr.create(CompOne)
        self.assertNotEqual(cid, ComponentId.INVALID)

        # Component should exist and be in CREATING state now...
        component = self.comp_mgr.get(cid)
        self.assertIsNotNone(component)
        self.assertEqual(component.id, cid)
        self.assertEqual(component.life_cycle,
                         ComponentLifeCycle.CREATING)

        # Tick past creation to get new component finished.
        self.comp_mgr.creation(None)

        # Component should still exist and be in ALIVE state now.
        self.assertIsNotNone(component)
        self.assertIsInstance(component,
                              CompOne)
        self.assertEqual(component.id, cid)
        self.assertEqual(component.life_cycle,
                         ComponentLifeCycle.ALIVE)

        # TODO EVENT HERE?

    def test_destruction(self):
        cid = self.comp_mgr.create(CompOne)
        self.assertNotEqual(cid, ComponentId.INVALID)

        # Component should exist and be in CREATING state now...
        component = self.comp_mgr.get(cid)
        self.assertIsNotNone(component)
        self.assertEqual(component.id, cid)
        self.assertEqual(component.life_cycle,
                         ComponentLifeCycle.CREATING)

        # Now (ask for) destroy!
        self.comp_mgr.destroy(cid)

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

        # TODO EVENT HERE?
