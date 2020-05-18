# coding: utf-8

'''
Tests for SystemManager.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from .system import SystemManager

from .component import ComponentManager
from .entity import EntityManager
from .time import TimeManager

from .const import SystemTick, SystemPriority, SystemHealth, DebugFlag

from .base.identity import (ComponentId,
                            EntityId,
                            SystemId)
from .base.component import (Component,
                             ComponentError)
from .base.entity import Entity
from .base.system import (System,
                          SystemLifeCycle)


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


class SysTest(System):
    def __init__(self, system_id, *args, **kwargs):
        super().__init__(system_id, *args, **kwargs)
        self.ents_seen = {
            SystemTick.TIME:     set(),
            SystemTick.LIFE:     set(),
            SystemTick.PRE:      set(),
            SystemTick.STANDARD: set(),
            SystemTick.POST:     set(),
            SystemTick.DEATH:    set(),
        }

    def _look_at_entities(self, tick, entity_mgr):
        for entity in entity_mgr.each_with(self.required()):
            self.ents_seen[tick].add(entity.id)

    def test_saw_total(self):
        return (len(self.ents_seen[SystemTick.TIME])
                + len(self.ents_seen[SystemTick.LIFE])
                + len(self.ents_seen[SystemTick.PRE])
                + len(self.ents_seen[SystemTick.STANDARD])
                + len(self.ents_seen[SystemTick.POST])
                + len(self.ents_seen[SystemTick.DEATH]))

    def test_saw_entity(self, tick, id):
        return id in self.ents_seen[tick]

    def test_clear_seen(self):
        for each in self.ents_seen:
            each.clear()

    def update_time(self,
                    time_mgr,
                    component_mgr,
                    entity_mgr):
        self._look_at_entities(SystemTick.TIME, entity_mgr)
        return SystemHealth.HEALTHY

    def update_life(self,
                    time_mgr,
                    component_mgr,
                    entity_mgr):
        self._look_at_entities(SystemTick.LIFE, entity_mgr)
        return SystemHealth.HEALTHY

    def update_pre(self,
                    time_mgr,
                    component_mgr,
                    entity_mgr):
        self._look_at_entities(SystemTick.PRE, entity_mgr)
        return SystemHealth.HEALTHY

    def update(self,
                    time_mgr,
                    component_mgr,
                    entity_mgr):
        self._look_at_entities(SystemTick.STANDARD, entity_mgr)
        return SystemHealth.HEALTHY

    def update_post(self,
                    time_mgr,
                    component_mgr,
                    entity_mgr):
        self._look_at_entities(SystemTick.POST, entity_mgr)
        return SystemHealth.HEALTHY

    def update_death(self,
                    time_mgr,
                    component_mgr,
                    entity_mgr):
        self._look_at_entities(SystemTick.DEATH, entity_mgr)
        return SystemHealth.HEALTHY


class SysJeff(SysTest):
    def __init__(self, system_id, *args, **kwargs):
        super().__init__(system_id, *args, **kwargs)
        self._ticks = (SystemTick.PRE
                       | SystemTick.STANDARD
                       | SystemTick.POST)

    def priority(self):
        return SystemPriority.MEDIUM + 13

    def required(self):
        return {CompOne, CompTwo}


class SysJill(SysTest):
    def __init__(self, system_id, *args, x=None, y=None, **kwargs):
        super().__init__(system_id, *args, **kwargs)
        self._ticks = SystemTick.STANDARD
        self.x = x
        self.y = y

    def priority(self):
        return SystemPriority.HIGH

    def required(self):
        return {CompOne}


class SysThree(SysTest):
    def priority(self):
        return SystemPriority.LOW + 1


class SysFour(SysTest):
    pass


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_SystemManager(unittest.TestCase):

    def setUp(self):
        self.component = ComponentManager()
        self.entity = EntityManager(self.component)
        self.time = TimeManager()
        self.system = SystemManager(DebugFlag.UNIT_TESTS)

    def tearDown(self):
        self.component = None
        self.entity = None
        self.time = None
        self.system = None

    def create_entities(self):
        comps_1_2_x = set([CompOne(0), CompTwo(1)])
        comps_1_x_x = set([CompOne(2)])
        comps_1_2_3 = set([CompOne(3), CompTwo(4), CompThree(5)])
        comps_x_2_3 = set([            CompTwo(6), CompThree(7)])

        self.ent_1_2_x = self.entity.create(1, comps_1_2_x)
        self.ent_1_x_x = self.entity.create(2, comps_1_x_x)
        self.ent_1_2_3 = self.entity.create(1, comps_1_2_3)
        self.ent_x_2_3 = self.entity.create(3, comps_x_2_3)

        self.ent_ids = {
            self.ent_1_2_x,
            self.ent_1_x_x,
            self.ent_1_2_3,
            self.ent_x_2_3,
        }

    def saw_ents(self, sys, tick, ent_ids):
        seen_ids = set()
        for id in ent_ids:
            seen = sys.test_saw_entity(tick, id)
            # Must have seen each expected id for success.
            if seen:
                seen_ids.add(id)
        return seen_ids

    def test_init(self):
        self.assertTrue(self.component)
        self.assertTrue(self.entity)
        self.assertTrue(self.time)
        self.assertTrue(self.system)

    def test_create(self):
        self.assertEqual(self.system._system_id.peek(),
                         SystemId.INVALID)

        sid = self.system.create(SysJeff)
        self.assertNotEqual(sid, SystemId.INVALID)

        self.assertEqual(len(self.system._system_create), 1)
        self.assertEqual(len(self.system._system_destroy), 0)
        self.assertEqual(len(self.system._system), 1)

        # TODO EVENT HERE?

        # System should exist and be in CREATING state now...
        system = self.system.get(sid)
        self.assertIsNotNone(system)
        self.assertIsInstance(system,
                              System)
        self.assertEqual(system.id, sid)
        self.assertEqual(system.life_cycle,
                         SystemLifeCycle.CREATING)

    def test_create_args(self):
        self.assertEqual(self.system._system_id.peek(),
                         SystemId.INVALID)

        sid = self.system.create(SysJill, x=1, y=2)
        self.assertNotEqual(sid, SystemId.INVALID)

        # System should exist and have its args assigned.
        system = self.system.get(sid)
        self.assertIsNotNone(system)
        self.assertIsInstance(system,
                              SysJill)
        self.assertEqual(system.life_cycle,
                         SystemLifeCycle.CREATING)
        self.assertEqual(system.x, 1)
        self.assertEqual(system.y, 2)

    def test_destroy(self):
        self.assertEqual(self.system._system_id.peek(),
                         SystemId.INVALID)

        sid = 1
        self.system.destroy(sid)
        # System doesn't exist, so nothing happened.
        self.assertEqual(len(self.system._system_create), 0)
        self.assertEqual(len(self.system._system_destroy), 0)

        sid = self.system.create(SysJeff)
        # Now we should have a create...
        self.assertNotEqual(sid, SystemId.INVALID)
        self.assertEqual(len(self.system._system_create), 1)
        # ...a destroy...
        self.system.destroy(sid)
        self.assertEqual(len(self.system._system_destroy), 1)
        # ...and a DESTROYING state.
        system = self.system.get(sid)
        self.assertIsNotNone(system)
        self.assertIsInstance(system,
                              SysJeff)
        self.assertEqual(system.life_cycle,
                         SystemLifeCycle.DESTROYING)

        # TODO EVENT HERE?

    def test_creation(self):
        sid = self.system.create(SysJeff)
        self.assertNotEqual(sid, SystemId.INVALID)

        # System should exist and be in CREATING state now...
        system = self.system.get(sid)
        self.assertIsNotNone(system)
        self.assertEqual(system.id, sid)
        self.assertEqual(system.life_cycle,
                         SystemLifeCycle.CREATING)

        # Tick past creation to get new system finished.
        self.system.creation(None)

        # System should still exist and be in ALIVE state now.
        self.assertIsNotNone(system)
        self.assertIsInstance(system,
                              SysJeff)
        self.assertEqual(system.id, sid)
        self.assertEqual(system.life_cycle,
                         SystemLifeCycle.ALIVE)

        # TODO EVENT HERE?

    def test_destruction(self):
        sid = self.system.create(SysJeff)
        self.assertNotEqual(sid, SystemId.INVALID)

        # System should exist and be in CREATING state now...
        system = self.system.get(sid)
        self.assertIsNotNone(system)
        self.assertEqual(system.id, sid)
        self.assertEqual(system.life_cycle,
                         SystemLifeCycle.CREATING)

        # Now (ask for) destroy!
        self.system.destroy(sid)

        # Tick past destruction to get poor new system DEAD.
        self.system.destruction(None)

        # System should not exist as far as SystemManager cares,
        # and be in DEAD state now.
        self.assertIsNone(self.system.get(sid))
        self.assertIsNotNone(system)
        self.assertIsInstance(system,
                              SysJeff)
        self.assertEqual(system.id, sid)
        self.assertEqual(system.life_cycle,
                         SystemLifeCycle.DEAD)

        # TODO EVENT HERE?

    def test_scheduling(self):
        sid = self.system.create(SysFour)
        self.assertNotEqual(sid, SystemId.INVALID)

        sid = self.system.create(SysJeff)
        self.assertNotEqual(sid, SystemId.INVALID)

        sid = self.system.create(SysThree)
        self.assertNotEqual(sid, SystemId.INVALID)

        sid = self.system.create(SysJeff)
        self.assertNotEqual(sid, SystemId.INVALID)
