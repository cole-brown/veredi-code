# coding: utf-8

'''
Tests for engine.py (The Game Itself).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from . import engine

from .ecs.event import EventManager
from .ecs.entity import EntityManager
from .ecs.component import ComponentManager
from .ecs.time import TimeManager
from .ecs.system import SystemManager
from .ecs.const import SystemTick, SystemPriority, SystemHealth, DebugFlag

from .ecs.base.identity import (ComponentId,
                                EntityId,
                                SystemId)
from .ecs.base.component import (Component,
                                 ComponentLifeCycle)
from .ecs.base.entity import (Entity,
                              EntityLifeCycle)
from .ecs.base.system import (System,
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
        self._look_at_entities(SystemTick.TIME_MGR, entity_mgr)
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
        super().__init__(system_id, *args, x=None, y=None, **kwargs)
        self._ticks = SystemTick.STANDARD

    def priority(self):
        return SystemPriority.HIGH

    def required(self):
        return {CompOne}


class SysNoTick(SysTest):
    def __init__(self, system_id, *args, **kwargs):
        super().__init__(system_id, *args, **kwargs)
        self._ticks = None

    def priority(self):
        return SystemPriority.LOW


class SysNoReq(SysTest):
    def __init__(self, system_id, *args, **kwargs):
        super().__init__(system_id, *args, **kwargs)
        self._ticks = None

    def required(self):
        return None


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_Engine(unittest.TestCase):

    def setUp(self):
        self.event = EventManager()
        self.time = TimeManager()
        self.component = ComponentManager()
        self.entity = EntityManager(self.component)
        self.system = SystemManager(DebugFlag.UNIT_TESTS)
        self.engine = engine.Engine(None, None, None,
                                    self.event,
                                    self.time,
                                    self.component,
                                    self.entity,
                                    self.system,
                                    DebugFlag.UNIT_TESTS)

    def tearDown(self):
        self.event = None
        self.time = None
        self.component = None
        self.entity = None
        self.system = None
        self.engine = None

    def create_entities(self):
        comps_1_2_x = set([self.component.create(CompOne), self.component.create(CompTwo)])
        comps_1_x_x = set([self.component.create(CompOne)])
        comps_1_2_3 = set([self.component.create(CompOne), self.component.create(CompTwo), self.component.create(CompThree)])
        comps_x_2_3 = set([                                self.component.create(CompTwo), self.component.create(CompThree)])

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

    def create_systems(self, *args):
        sids = []
        for each in args:
            if isinstance(each, tuple):
                sids.append(self.system.create(each[0], *each[1:]))
            else:
                sids.append(self.system.create(each))

#        # Create stuff.
#        self.jeff_id = self.system.create(SysJeff)
#        self.jill_id = self.system.create(SysJill)

        return sids

    def saw_ents(self, sys, tick, ent_ids):
        seen_ids = set()
        for id in ent_ids:
            seen = sys.test_saw_entity(tick, id)
            # Must have seen each expected id for success.
            if seen:
                seen_ids.add(id)
        return seen_ids

    def test_init(self):
        self.assertTrue(self.event)
        self.assertTrue(self.time)
        self.assertTrue(self.component)
        self.assertTrue(self.entity)
        self.assertTrue(self.engine)

    def test_set_up(self):
        # Create stuff.
        self.create_entities()
        jeff_id, jill_id = self.create_systems(SysJeff, SysJill)

        # Tick should get it all created and alive and scheduled.
        self.engine.tick()

        self.assertTrue(len(self.component._component_by_id) > 0)
        for cid in self.component._component_by_id:
            comp = self.component.get(cid)
            self.assertIsNotNone(comp)
            self.assertEqual(comp.life_cycle, ComponentLifeCycle.ALIVE)

        self.assertTrue(len(self.entity._entity) > 0)
        for eid in self.entity._entity:
            ent = self.entity.get(eid)
            self.assertIsNotNone(ent)
            self.assertEqual(ent.life_cycle, EntityLifeCycle.ALIVE)

        self.assertTrue(len(self.system._system) > 0)
        for sid in self.system._system:
            sys = self.system.get(sid)
            self.assertIsNotNone(sys)
            self.assertEqual(sys.life_cycle, SystemLifeCycle.ALIVE)

        self.assertEqual(self.system._schedule,
                         [self.system.get(jill_id), self.system.get(jeff_id)])

    def test_empty_engine_tick(self):
        # Tick an empty engine.
        # Raise exceptions if things go wrong
        self.engine.tick()

    def test_tickless_sys(self):
        self.create_entities()
        # Register, set up, and run it... and assert, uhh... no exceptions.
        sids = self.create_systems(SysNoTick)
        self.engine.tick()
        # guess we can check this too...
        noop = self.system.get(sids[0])
        self.assertIsInstance(noop, SysNoTick)
        self.assertEqual(noop.test_saw_total(), 0)

        # Once more with entity.
        self.create_entities()
        self.engine.tick()
        self.assertEqual(noop.test_saw_total(), 0)

    def test_reqless_sys(self):
        # Register, set up, and run it... and assert, uhh... no exceptions.
        sids = self.create_systems(SysNoReq)
        chill_sys = self.system.get(sids[0])
        self.engine.tick()
        # guess we can check this too...
        self.assertEqual(chill_sys.test_saw_total(), 0)

        # Once more with entity.
        self.create_entities()
        self.engine.tick()
        self.assertEqual(chill_sys.test_saw_total(), 0)

    def test_multi_sys_see_ents(self):
        # Register, set up, and run 'em.
        sids = self.create_systems(SysNoReq,
                                   SysNoTick,
                                   SysJeff,
                                   SysJill)
        no_req = self.system.get(sids[0])
        no_tick = self.system.get(sids[1])
        jeff = self.system.get(sids[2])
        jill = self.system.get(sids[3])

        self.engine.tick()

        # guess we can check this too...
        self.assertEqual(no_req.test_saw_total(), 0)
        self.assertEqual(no_tick.test_saw_total(), 0)
        self.assertEqual(jeff.test_saw_total(), 0)
        self.assertEqual(jill.test_saw_total(), 0)

        # Once more with entity.
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
