# coding: utf-8

'''
Tests for entity.py (SystemLifeCycle class).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from .entity import SystemLifeCycle
from veredi.entity import component
from veredi.entity.component import (EntityId,
                                     INVALID_ENTITY_ID,
                                     Component)

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

class Test_LifeCycle(unittest.TestCase):

    def setUp(self):
        self.entities = SystemLifeCycle()

    def tearDown(self):
        self.entities = None

    def test_init(self):
        self.assertTrue(self.entities)

    def test_request_create(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        eid = self.entities.create(CompOne(), CompTwo())
        self.assertNotEqual(eid, INVALID_ENTITY_ID)

        self.assertEqual(len(self.entities._entity_add), 1)
        self.assertEqual(len(self.entities._entity_rm), 0)
        self.assertEqual(len(self.entities._entity_del), 0)
        self.assertEqual(len(self.entities._entity), 0)

        # Entities will not be 'transitioned' until the tick where they're
        # actually added or removed.
        added = self.entities._get_transitions(component.StateLifeCycle.ADDED)
        removed = self.entities._get_transitions(component.StateLifeCycle.REMOVED)
        self.assertFalse(added)
        self.assertFalse(removed)

        # Entity should only have the components we asked for.
        entity = self.entities._entity_add[eid]
        self.assertEqual(entity,
                         {CompOne, CompTwo})

    def test_request_delete(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        eid = 1
        self.entities.delete(eid)
        self.assertNotEqual(eid, INVALID_ENTITY_ID)

        self.assertEqual(len(self.entities._entity_add), 0)
        self.assertEqual(len(self.entities._entity_rm), 0)
        self.assertEqual(len(self.entities._entity_del), 1)
        self.assertEqual(len(self.entities._entity), 0)

        # Entities will not be 'transitioned' until the tick where they're
        # actually added or removed.
        added = self.entities._get_transitions(component.StateLifeCycle.ADDED)
        removed = self.entities._get_transitions(component.StateLifeCycle.REMOVED)
        self.assertFalse(added)
        self.assertFalse(removed)

    def test_request_add(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        eid = self.entities.create(CompOne(), CompTwo())
        self.assertNotEqual(eid, INVALID_ENTITY_ID)

        # Entity should only have the components we asked for.
        entity = self.entities._entity_add[eid]
        self.assertEqual(entity,
                         {CompOne, CompTwo})

        # Now we add a third
        self.entities.add(eid, CompThree())

        # And the Entity should now have that as well.
        entity = self.entities._entity_add[eid]
        self.assertEqual(entity,
                        {CompOne, CompTwo, CompThree})

    def test_request_remove(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        eid = 1
        self.assertNotEqual(eid, INVALID_ENTITY_ID)

        # ask for this eid to remove a component
        self.entities.remove(eid, CompThree)

        entity = self.entities._entity_rm[eid]
        self.assertEqual(entity,
                        {CompThree})

        # ask for this eid to remove more
        self.entities.remove(eid, CompOne)

        entity = self.entities._entity_rm[eid]
        self.assertEqual(entity,
                         {CompOne, CompThree})

    def test_full_create(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        eid = self.entities.create(CompOne(), CompTwo())
        self.assertNotEqual(eid, INVALID_ENTITY_ID)

        # Entities will not be 'transitioned' until the tick where they're
        # actually added or removed.
        added = self.entities._get_transitions(component.StateLifeCycle.ADDED)
        self.assertFalse(added)

        # Tick past update_life to get new entity pushed into alive pool.
        self.entities.update_life(0, None, None)

        self.assertTrue(added)
        self.assertTrue(eid in added)
        entity = self.entities.get(eid)
        self.assertTrue(entity)
        # correct component set
        self.assertEqual(entity,
                         {CompOne, CompTwo})
        # wrong component set
        self.assertNotEqual(entity,
                            {CompOne, CompThree})

    def test_full_delete(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        # create so we can delete...
        eid = self.entities.create(CompOne(), CompTwo())
        self.assertNotEqual(eid, INVALID_ENTITY_ID)
        self.entities.update_life(0, None, None)
        entity = self.entities.get(eid)
        self.assertTrue(entity)
        self.assertEqual(entity,
                         {CompOne, CompTwo})

        # Now (ask for) delete!
        self.entities.delete(eid)

        # Now (actually do) delete!
        self.entities.update_death(0, None, None)
        entity = self.entities.get(eid)
        self.assertFalse(entity)
        self.assertIsNone(entity)

        removed = self.entities._get_transitions(component.StateLifeCycle.REMOVED)
        self.assertTrue(removed)
        self.assertTrue(eid in removed)

    def test_full_add(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        eid = self.entities.create(CompOne(), CompTwo())
        self.assertNotEqual(eid, INVALID_ENTITY_ID)

        # Entities will not be 'transitioned' until the tick where they're
        # actually added or removed.
        added = self.entities._get_transitions(component.StateLifeCycle.ADDED)
        self.assertFalse(added)

        # Tick past update_life to get new entity pushed into alive pool.
        self.entities.update_life(0, None, None)

        self.assertTrue(added)
        self.assertTrue(eid in added)
        entity = self.entities.get(eid)
        self.assertTrue(entity)
        self.assertEqual(entity,
                         {CompOne, CompTwo})

        # Alright.... now we can test adding a component.
        self.entities.add(eid, CompThree())

        # And the Entity should now have that queued up...
        adding = self.entities._entity_add[eid]
        self.assertEqual(adding,
                        {CompThree})
        # ...and entity should be unchanged as of yet.
        self.assertEqual(entity,
                         {CompOne, CompTwo})

        # Tick past update_life to get new component on entity.
        self.entities.update_life(0, None, None)

        self.assertTrue(added)
        self.assertTrue(eid in added)
        # Handle on entity should still be valid.
        # entity = self.entities.get(eid)
        self.assertTrue(entity)
        self.assertEqual(entity,
                         {CompOne, CompTwo, CompThree})

    def test_full_remove(self):
        self.assertEqual(self.entities._new_entity_id,
                         INVALID_ENTITY_ID)

        # Get an entity so we can rm a component...
        eid = self.entities.create(CompOne(), CompTwo())
        self.assertNotEqual(eid, INVALID_ENTITY_ID)
        self.entities.update_life(0, None, None)

        entity = self.entities.get(eid)
        self.assertTrue(entity)
        self.assertEqual(entity,
                         {CompOne, CompTwo})

        # Alright.... now we can test removing a component.
        self.entities.remove(eid, CompTwo())

        # And the Entity should now have that queued up...
        removing = self.entities._entity_rm[eid]
        self.assertEqual(removing,
                         {CompTwo})

        # Tick past update_life to get new entity pushed into alive pool.
        self.entities.update_death(0, None, None)

        removed = self.entities._get_transitions(component.StateLifeCycle.REMOVED)
        self.assertTrue(removed)
        self.assertTrue(eid in removed)

        # Handle on entity should still be valid.
        # entity = self.entities.get(eid)
        self.assertTrue(entity)
        self.assertEqual(entity,
                         {CompOne})
