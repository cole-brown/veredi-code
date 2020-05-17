# coding: utf-8

'''
Tests for engine.py (The Game Itself).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from . import engine

from .ecs.entity import EntityManager
from .ecs.component import ComponentManager
from .ecs.time import TimeManager
from .ecs.system import System
from .ecs.const import SystemTick, SystemPriority, SystemHealth

from veredi.entity.component import (ComponentId,
                                     INVALID_COMPONENT_ID,
                                     Component,
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


class SysTest(System):
    def __init__(self):
        super().__init__()
        self.ents_seen = {
            SystemTick.TIME:     set(),
            SystemTick.LIFE:     set(),
            SystemTick.PRE:      set(),
            SystemTick.STANDARD: set(),
            SystemTick.POST:     set(),
            SystemTick.DEATH:    set(),
        }

    def _look_at_entities(self, tick, sys_entities):
        for entity in sys_entities.each_with(self.required()):
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
                    time,
                    sys_entities,
                    sys_time):
        self._look_at_entities(SystemTick.TIME, sys_entities)
        return SystemHealth.HEALTHY

    def update_life(self,
                    time,
                    sys_entities,
                    sys_time):
        self._look_at_entities(SystemTick.LIFE, sys_entities)
        return SystemHealth.HEALTHY

    def update_pre(self,
                    time,
                    sys_entities,
                    sys_time):
        self._look_at_entities(SystemTick.PRE, sys_entities)
        return SystemHealth.HEALTHY

    def update(self,
                    time,
                    sys_entities,
                    sys_time):
        self._look_at_entities(SystemTick.STANDARD, sys_entities)
        return SystemHealth.HEALTHY

    def update_post(self,
                    time,
                    sys_entities,
                    sys_time):
        self._look_at_entities(SystemTick.POST, sys_entities)
        return SystemHealth.HEALTHY

    def update_death(self,
                    time,
                    sys_entities,
                    sys_time):
        self._look_at_entities(SystemTick.DEATH, sys_entities)
        return SystemHealth.HEALTHY


class SysJeff(SysTest):
    def __init__(self):
        super().__init__()
        self._ticks = (SystemTick.PRE
                       | SystemTick.STANDARD
                       | SystemTick.POST)

    def priority(self):
        return SystemPriority.MEDIUM + 13

    def required(self):
        return {CompOne, CompTwo}


class SysJill(SysTest):
    def __init__(self):
        super().__init__()
        self._ticks = SystemTick.STANDARD

    def priority(self):
        return SystemPriority.HIGH

    def required(self):
        return {CompOne}


class SysNoTick(SysTest):
    def __init__(self):
        super().__init__()
        self._ticks = None

    def priority(self):
        return SystemPriority.LOW


class SysNoReq(SysTest):
    def __init__(self):
        super().__init__()
        self._ticks = None

    def required(self):
        return None


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_Engine(unittest.TestCase):

    def setUp(self):
        self.components = ComponentManager()
        self.entities = EntityManager(self.components)
        self.time = TimeManager()
        self.engine = engine.Engine(None, None, None,
                                    self.time, self.entities,
                                    engine.EngineDebug.UNIT_TESTS)

    def tearDown(self):
        self.entities = None
        self.time = None
        self.engine = None

    def create_entities(self):
        comps_1_2_x = set([CompOne(0), CompTwo(1)])
        comps_1_x_x = set([CompOne(2)])
        comps_1_2_3 = set([CompOne(3), CompTwo(4), CompThree(5)])
        comps_x_2_3 = set([            CompTwo(6), CompThree(7)])

        self.ent_1_2_x = self.entities.create(1, comps_1_2_x)
        self.ent_1_x_x = self.entities.create(2, comps_1_x_x)
        self.ent_1_2_3 = self.entities.create(1, comps_1_2_3)
        self.ent_x_2_3 = self.entities.create(3, comps_x_2_3)

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
        self.assertTrue(self.entities)
        self.assertTrue(self.time)
        self.assertTrue(self.engine)

    def test_set_up(self):
        jeff = SysJeff()
        jill = SysJill()
        self.engine.register(jeff)
        self.engine.register(jill)

        # Nothing in schedule yet.
        self.assertFalse(self.engine._sys_schedule)
        # But they're ready...
        self.assertTrue(self.engine._sys_registration)

        self.engine.set_up()

        # Now registered systems should be scheduled by priority.
        self.assertFalse(self.engine._sys_registration)
        self.assertTrue(self.engine._sys_schedule)
        self.assertEqual(self.engine._sys_schedule,
                         [jill, jeff])

    def test_no_sys_tick(self):
        # raise exceptions if things go wrong
        self.engine.DEBUG_TICK = True
        self.engine.tick()

    def test_tickless_sys(self):
        # Register, set up, and run it... and assert, uhh... no exceptions.
        noop = SysNoTick()
        self.engine.register(noop)
        self.engine.set_up()
        self.engine.tick()
        # guess we can check this too...
        self.assertEqual(noop.test_saw_total(), 0)

        # Once more with entities.
        self.create_entities()
        self.engine.tick()
        self.assertEqual(noop.test_saw_total(), 0)

    def test_reqless_sys(self):
        # Register, set up, and run it... and assert, uhh... no exceptions.
        chill_sys = SysNoReq()
        self.engine.register(chill_sys)
        self.engine.set_up()
        self.engine.tick()
        # guess we can check this too...
        self.assertEqual(chill_sys.test_saw_total(), 0)

        # Once more with entities.
        self.create_entities()
        self.engine.tick()
        self.assertEqual(chill_sys.test_saw_total(), 0)


    def test_multi_sys_see_ents(self):
        # Register, set up, and run 'em.
        no_req = SysNoReq()
        no_tick = SysNoTick()
        jeff = SysJeff()
        jill = SysJill()
        self.engine.register(no_req, no_tick, jeff)
        self.engine.register(jill)
        self.engine.set_up()
        self.engine.tick()
        # guess we can check this too...
        self.assertEqual(no_req.test_saw_total(), 0)
        self.assertEqual(no_tick.test_saw_total(), 0)
        self.assertEqual(jeff.test_saw_total(), 0)
        self.assertEqual(jill.test_saw_total(), 0)

        # Once more with entities.
        self.create_entities()
        self.engine.tick()
        self.assertEqual(no_req.test_saw_total(), 0)
        self.assertEqual(no_tick.test_saw_total(), 0)
        # Jeff wants:
        #   - CompOne && CompTwo
        #   - PRE, STANDARD, POST
        # We have two ents that fit the bill so we should see 6
        # (2 ents * 3 tick phases).
        self.assertEqual(jeff.test_saw_total(), 2 * 3)
        # Jill wants:
        #   - CompOne
        #   - STANDARD
        # We have three ents that fit the bill so we should see 3
        # (3 ents * 1 tick phase).
        self.assertEqual(jill.test_saw_total(), 3 * 1)

        # Now make sure they saw the correct ents on the correct ticks...
        # ---
        # System of Jeff
        # ---
        tick = SystemTick.TIME
        expected_ids = set()
        self.assertEqual(self.saw_ents(jeff, tick, self.ent_ids),
                         expected_ids)
        tick = SystemTick.LIFE
        self.assertEqual(self.saw_ents(jeff, tick, self.ent_ids),
                         expected_ids)

        tick = SystemTick.PRE
        expected_ids = {self.ent_1_2_x, self.ent_1_2_3}
        self.assertEqual(self.saw_ents(jeff, tick, self.ent_ids),
                         expected_ids)
        tick = SystemTick.STANDARD
        self.assertEqual(self.saw_ents(jeff, tick, self.ent_ids),
                         expected_ids)
        tick = SystemTick.POST
        self.assertEqual(self.saw_ents(jeff, tick, self.ent_ids),
                         expected_ids)

        tick = SystemTick.DEATH
        expected_ids = set()
        self.assertEqual(self.saw_ents(jeff, tick, self.ent_ids),
                         expected_ids)

        # ---
        # System of Jill
        # ---
        tick = SystemTick.TIME
        expected_ids = set()
        self.assertEqual(self.saw_ents(jill, tick, self.ent_ids),
                         expected_ids)
        tick = SystemTick.LIFE
        self.assertEqual(self.saw_ents(jill, tick, self.ent_ids),
                         expected_ids)
        tick = SystemTick.PRE
        self.assertEqual(self.saw_ents(jill, tick, self.ent_ids),
                         expected_ids)

        tick = SystemTick.STANDARD
        expected_ids = {self.ent_1_x_x, self.ent_1_2_x, self.ent_1_2_3}
        self.assertEqual(self.saw_ents(jill, tick, self.ent_ids),
                         expected_ids)

        tick = SystemTick.POST
        expected_ids = set()
        self.assertEqual(self.saw_ents(jill, tick, self.ent_ids),
                         expected_ids)
        tick = SystemTick.DEATH
        self.assertEqual(self.saw_ents(jill, tick, self.ent_ids),
                         expected_ids)



    # TODO: Test that a system barfing exceptions all over the place doesn't
    # kill the engine.
