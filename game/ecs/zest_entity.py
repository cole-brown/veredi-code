# coding: utf-8

'''
Tests for entity.py (EntityManager class).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from .entity import EntityManager
from .component import ComponentManager
from veredi.entity.component import (ComponentId,
                                     INVALID_COMPONENT_ID,
                                     Component,
                                     ComponentError)
from veredi.entity.entity import (EntityId,
                                  INVALID_ENTITY_ID,
                                  Entity,
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
        self.entities = EntityManager(ComponentManager())

    def tearDown(self):
        self.entities = None

    def test_init(self):
        self.assertTrue(self.entities)

    def test_create(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        eid = self.entities.create(self._TYPE_DONT_CARE, CompOne(0), CompTwo(1))
        self.assertNotEqual(eid, INVALID_ENTITY_ID)

        self.assertEqual(len(self.entities._entity_create), 1)
        self.assertEqual(len(self.entities._entity_destroy), 0)
        self.assertEqual(len(self.entities._entity), 1)

        # TODO EVENT HERE!

        # Entity should only have the components we asked for.
        entity = self.entities.get(eid)
        self.assertIsNotNone(entity)
        self.assertIsInstance(entity,
                              Entity)
        self.assertTrue(entity.contains({CompOne, CompTwo}))
        self.assertEqual(entity.life_cycle,
                         EntityLifeCycle.CREATING)

    def test_destroy(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        # destroy non-existant == no-op
        eid = 1
        self.entities.destroy(eid)
        self.assertEqual(len(self.entities._entity), 0)
        self.assertEqual(len(self.entities._entity_create), 0)
        self.assertEqual(len(self.entities._entity_destroy), 0)

        eid = self.entities.create(self._TYPE_DONT_CARE, CompOne(0), CompTwo(1))
        self.assertNotEqual(eid, INVALID_ENTITY_ID)
        # Now we should have a create...
        self.assertEqual(len(self.entities._entity), 1)
        self.assertEqual(len(self.entities._entity_create), 1)
        # ...a destroy...
        self.entities.destroy(eid)
        self.assertEqual(len(self.entities._entity_destroy), 1)
        # ...and a DESTROYING state.
        entity = self.entities.get(eid)
        self.assertIsNotNone(entity)
        self.assertIsInstance(entity,
                              Entity)
        self.assertEqual(entity.life_cycle,
                         EntityLifeCycle.DESTROYING)

        # TODO EVENT HERE?

    def test_add(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        eid = self.entities.create(self._TYPE_DONT_CARE, CompOne(0), CompTwo(1))
        self.assertNotEqual(eid, INVALID_ENTITY_ID)

        # Entity should only have the components we asked for.
        entity = self.entities.get(eid)
        self.assertIsInstance(entity,
                              Entity)
        self.assertTrue(entity.contains({CompOne, CompTwo}))

        # Now we add a third
        self.entities.add(eid, CompThree(2))

        # And the Entity should now have that as well.
        entity = self.entities.get(eid)
        self.assertIsInstance(entity,
                              Entity)
        self.assertTrue(entity.contains({CompOne, CompTwo, CompThree}))

        # TODO Event?

    def test_remove(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        comp1 = CompOne(1)
        comp2 = CompTwo(2)
        eid = self.entities.create(self._TYPE_DONT_CARE, comp1, comp2)
        self.assertNotEqual(eid, INVALID_ENTITY_ID)

        # Entity should have the components we asked for.
        entity = self.entities.get(eid)
        self.assertIsInstance(entity,
                              Entity)
        self.assertTrue(entity.contains({CompOne, CompTwo}))

        # Now we remove one...
        self.entities.remove(eid, type(comp2))

        # And the Entity should now have just the one.
        entity = self.entities.get(eid)
        self.assertIsInstance(entity,
                              Entity)
        self.assertFalse(entity.contains({CompOne, CompTwo}))
        self.assertFalse(entity.contains({CompTwo}))
        self.assertTrue(entity.contains({CompOne}))

        # TODO Event?

    def test_creation(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        comp1 = CompOne(1)
        comp2 = CompTwo(2)
        eid = self.entities.create(self._TYPE_DONT_CARE, comp1, comp2)
        self.assertNotEqual(eid, INVALID_ENTITY_ID)

        # Entity should exist and be in CREATING state now...
        entity = self.entities.get(eid)
        self.assertIsNotNone(entity)
        self.assertEqual(entity.id, eid)
        self.assertEqual(entity.life_cycle,
                         EntityLifeCycle.CREATING)

        # Tick past creation to get new entity finished.
        self.entities.creation(None)

        # Entity should still exist and be in ALIVE state now.
        self.assertIsNotNone(entity)
        self.assertIsInstance(entity,
                              Entity)
        self.assertEqual(entity.id, eid)
        self.assertEqual(entity.life_cycle,
                         EntityLifeCycle.ALIVE)

        # TODO EVENT HERE?

    def test_destruction(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        # create so we can destroy...
        eid = self.entities.create(self._TYPE_DONT_CARE, CompOne(2), CompTwo(0))
        self.assertNotEqual(eid, INVALID_ENTITY_ID)
        self.entities.creation(None)
        entity = self.entities.get(eid)
        self.assertTrue(entity)
        self.assertTrue(entity.contains({CompOne, CompTwo}))

        # Now (ask for) destroy!
        self.entities.destroy(eid)

        # Now (actually do) destroy!
        self.entities.destruction(None)

        # EntityManager should no longer have them...
        self.assertIsNone(self.entities.get(eid))
        # ...and they should be dead (via our old handle).
        self.assertEqual(entity.life_cycle,
                         EntityLifeCycle.DEAD)

        # TODO EVENT HERE!
