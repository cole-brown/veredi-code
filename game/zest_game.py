# coding: utf-8

'''
Tests for game.py (The Game Itself).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from . import game
from .entity import SystemLifeCycle
from .time import Time
from veredi.entity import component
from veredi.entity.component import (EntityId,
                                     INVALID_ENTITY_ID,
                                     Component)
from veredi.entity.entity import Entity
from .system import System, SystemTick, SystemPriority, SystemHealth


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

class Test_Game(unittest.TestCase):

    def setUp(self):
        self.entities = SystemLifeCycle()
        self.time = Time()
        self.game = game.Game(None, None, None,
                               self.time, self.entities,
                              game.GameDebug.UNIT_TESTS)

    def tearDown(self):
        self.entities = None
        self.time = None
        self.game = None

    def create_entities(self):
        comps_1_2_x = set([CompOne(), CompTwo()])
        comps_1_x_x = set([CompOne()])
        comps_1_2_3 = set([CompOne(), CompTwo(), CompThree()])
        comps_x_2_3 = set([           CompTwo(), CompThree()])

        self.ent_1_2_x = self.entities.create(comps_1_2_x)
        self.ent_1_x_x = self.entities.create(comps_1_x_x)
        self.ent_1_2_3 = self.entities.create(comps_1_2_3)
        self.ent_x_2_3 = self.entities.create(comps_x_2_3)

        self.ent_ids = {
            self.ent_1_2_x,
            self.ent_1_x_x,
            self.ent_1_2_3,
            self.ent_x_2_3,
        }

    def create_systems(self, *systems):
        for each in systems:
            self.game.register(each)
        self.game.set_up()

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
        self.assertTrue(self.game)

    def test_set_up(self):
        jeff = SysJeff()
        jill = SysJill()
        self.game.register(jeff)
        self.game.register(jill)

        # Nothing in schedule yet.
        self.assertFalse(self.game._sys_schedule)
        # But they're ready...
        self.assertTrue(self.game._sys_registration)

        self.game.set_up()

        # Now registered systems should be scheduled by priority.
        self.assertFalse(self.game._sys_registration)
        self.assertTrue(self.game._sys_schedule)
        self.assertEqual(self.game._sys_schedule,
                         [jill, jeff])

    def test_no_sys_tick(self):
        # raise exceptions if things go wrong
        self.game.DEBUG_TICK = True
        self.game.tick()

    def test_tickless_sys(self):
        # Register, set up, and run it... and assert, uhh... no exceptions.
        noop = SysNoTick()
        self.game.register(noop)
        self.game.set_up()
        self.game.tick()
        # guess we can check this too...
        self.assertEqual(noop.test_saw_total(), 0)

        # Once more with entities.
        self.create_entities()
        self.game.tick()
        self.assertEqual(noop.test_saw_total(), 0)

    def test_reqless_sys(self):
        # Register, set up, and run it... and assert, uhh... no exceptions.
        chill_sys = SysNoReq()
        self.game.register(chill_sys)
        self.game.set_up()
        self.game.tick()
        # guess we can check this too...
        self.assertEqual(chill_sys.test_saw_total(), 0)

        # Once more with entities.
        self.create_entities()
        self.game.tick()
        self.assertEqual(chill_sys.test_saw_total(), 0)


    def test_multi_sys_see_ents(self):
        # Register, set up, and run 'em.
        no_req = SysNoReq()
        no_tick = SysNoTick()
        jeff = SysJeff()
        jill = SysJill()
        self.game.register(no_req, no_tick, jeff)
        self.game.register(jill)
        self.game.set_up()
        self.game.tick()
        # guess we can check this too...
        self.assertEqual(no_req.test_saw_total(), 0)
        self.assertEqual(no_tick.test_saw_total(), 0)
        self.assertEqual(jeff.test_saw_total(), 0)
        self.assertEqual(jill.test_saw_total(), 0)

        # Once more with entities.
        self.create_entities()
        self.game.tick()
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
    # kill the game.
