# coding: utf-8

'''
Tests for entity.py (EntityManager class).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from .entity import EntityManager
from veredi.entity.component import (ComponentId,
                                     INVALID_COMPONENT_ID,
                                     Component,
                                     ComponentMetaData,
                                     ComponentError)
from veredi.entity.entity import (EntityId,
                                  INVALID_ENTITY_ID,
                                  Entity)

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
        self.entities = EntityManager()

    def tearDown(self):
        self.entities = None

    def test_init(self):
        self.assertTrue(self.entities)

    def test_request_create(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        eid = self.entities.create(self._TYPE_DONT_CARE, CompOne(0), CompTwo(1))
        self.assertNotEqual(eid, INVALID_ENTITY_ID)

        self.assertEqual(len(self.entities._entity_add), 1)
        self.assertEqual(len(self.entities._entity_remove), 0)
        self.assertEqual(len(self.entities._entity_destroy), 0)
        self.assertEqual(len(self.entities._entity), 0)

        # TODO EVENT HERE!
        # # Entities will not be 'transitioned' until the tick where they're
        # # actually added or removed.
        # added = self.entities._get_transitions(component.StateLifeCycle.ADDED)
        # removed = self.entities._get_transitions(component.StateLifeCycle.REMOVED)
        # self.assertFalse(added)
        # self.assertFalse(removed)

        # Entity should only have the components we asked for.
        entity = self.entities._entity_add[eid]
        self.assertIsInstance(self.entities._entity_add[eid],
                              Entity)
        self.assertEqual(set(entity._components.values()),
                         {CompOne, CompTwo})

    def test_request_destroy(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        eid = 1
        self.entities.destroy(eid)
        self.assertNotEqual(eid, INVALID_ENTITY_ID)

        self.assertEqual(len(self.entities._entity_add), 0)
        self.assertEqual(len(self.entities._entity_remove), 0)
        self.assertEqual(len(self.entities._entity_destroy), 1)
        self.assertEqual(len(self.entities._entity), 0)

        # TODO EVENT HERE!
        # # Entities will not be 'transitioned' until the tick where they're
        # # actually added or removed.
        # added = self.entities._get_transitions(component.StateLifeCycle.ADDED)
        # removed = self.entities._get_transitions(component.StateLifeCycle.REMOVED)
        # self.assertFalse(added)
        # self.assertFalse(removed)

    def test_request_add(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        eid = self.entities.create(self._TYPE_DONT_CARE, CompOne(0), CompTwo(1))
        self.assertNotEqual(eid, INVALID_ENTITY_ID)

        # Entity should only have the components we asked for.
        entity = self.entities._entity_add[eid]
        self.assertIsInstance(self.entities._entity_add[eid],
                              Entity)
        self.assertEqual(set(entity._components.values()),
                         {CompOne, CompTwo})

        # Now we add a third
        self.entities.add(eid, CompThree(2))

        # And the Entity should now have that as well.
        entity = self.entities._entity_add[eid]
        self.assertIsInstance(entity,
                              Entity)
        self.assertEqual(set(entity._components.values()),
                         {CompOne, CompTwo, CompThree})

    def test_request_remove(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        eid = 1
        self.assertNotEqual(eid, INVALID_ENTITY_ID)

        # ask for this eid to remove a component
        self.entities.remove(eid, CompThree)

        entity = self.entities._entity_remove[eid]
        self.assertEqual(entity,
                         {CompThree})

        # ask for this eid to remove more
        self.entities.remove(eid, CompOne)

        entity = self.entities._entity_remove[eid]
        self.assertEqual(entity,
                         {CompOne, CompThree})

    def test_full_create(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        eid = self.entities.create(self._TYPE_DONT_CARE, CompOne(3), CompTwo(7))
        self.assertNotEqual(eid, INVALID_ENTITY_ID)

        # TODO EVENT HERE!
        # # Entities will not be 'transitioned' until the tick where they're
        # # actually added or removed.
        # added = self.entities._get_transitions(component.StateLifeCycle.ADDED)
        # self.assertFalse(added)

        # Tick past creation to get new entity pushed into alive pool.
        self.entities.creation(None)

        # TODO EVENT HERE!
        # self.assertTrue(added)
        # self.assertTrue(eid in added)
        entity = self.entities.get(eid)
        self.assertTrue(entity)
        # correct component set
        self.assertEqual(set(entity._components.values()),
                         {CompOne, CompTwo})
        # wrong component set
        self.assertNotEqual(set(entity._components.values()),
                            {CompOne, CompThree})

    def test_full_destroy(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        # create so we can destroy...
        eid = self.entities.create(self._TYPE_DONT_CARE, CompOne(2), CompTwo(0))
        self.assertNotEqual(eid, INVALID_ENTITY_ID)
        self.entities.creation(None)
        entity = self.entities.get(eid)
        self.assertTrue(entity)
        self.assertEqual(set(entity._components.values()),
                         {CompOne, CompTwo})

        # Now (ask for) destroy!
        self.entities.destroy(eid)

        # Now (actually do) destroy!
        self.entities.destruction(None)
        entity = self.entities.get(eid)
        self.assertFalse(entity)
        self.assertIsNone(entity)

        # TODO EVENT HERE!
        # removed = self.entities._get_transitions(component.StateLifeCycle.REMOVED)
        # self.assertTrue(removed)
        # self.assertTrue(eid in removed)

    def test_full_add(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        eid = self.entities.create(self._TYPE_DONT_CARE, CompOne(0), CompTwo(1))
        self.assertNotEqual(eid, INVALID_ENTITY_ID)

        # TODO EVENT HERE!
        # # Entities will not be 'transitioned' until the tick where they're
        # # actually added or removed.
        # added = self.entities._get_transitions(component.StateLifeCycle.ADDED)
        # self.assertFalse(added)

        # Tick past update_life to get new entity pushed into alive pool.
        self.entities.creation(None)

        # TODO EVENT HERE!
        # self.assertTrue(added)
        # self.assertTrue(eid in added)
        entity = self.entities.get(eid)
        self.assertTrue(entity)
        self.assertEqual(set(entity._components.values()),
                         {CompOne, CompTwo})

        # Alright.... now we can test adding a component.
        self.entities.add(eid, CompThree(3))

        # And the Entity should now have that queued up...
        adding = self.entities._entity_add[eid]
        self.assertEqual(adding,
                         {CompThree})
        # ...and entity should be unchanged as of yet.
        self.assertEqual(set(entity._components.values()),
                         {CompOne, CompTwo})

        # Tick past update_life to get new component on entity.
        self.entities.creation(None)

        # TODO EVENT HERE!
        # self.assertTrue(added)
        # self.assertTrue(eid in added)
        # Handle on entity should still be valid.
        # entity = self.entities.get(eid)
        self.assertTrue(entity)
        self.assertEqual(set(entity._components.values()),
                         {CompOne, CompTwo, CompThree})

    def test_full_remove(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        # Get an entity so we can rm a component...
        eid = self.entities.create(self._TYPE_DONT_CARE, CompOne(0), CompTwo(1))
        self.assertNotEqual(eid, INVALID_ENTITY_ID)
        self.entities.creation(None)

        entity = self.entities.get(eid)
        self.assertTrue(entity)
        self.assertEqual(set(entity._components.values()),
                         {CompOne, CompTwo})

        # Alright.... now we can test removing a component.
        self.entities.remove(eid, CompTwo(1))

        # And the Entity should now have that queued up...
        removing = self.entities._entity_remove[eid]
        self.assertEqual(removing,
                         {CompTwo})

        # Tick past destruction to get new entity pushed into alive pool.
        self.entities.destruction(None)

        # TODO EVENT HERE!
        # removed = self.entities._get_transitions(component.StateLifeCycle.REMOVED)
        # self.assertTrue(removed)
        # self.assertTrue(eid in removed)

        # Handle on entity should still be valid.
        # entity = self.entities.get(eid)
        self.assertTrue(entity)
        self.assertEqual(set(entity._components.values()),
                         {CompOne})
