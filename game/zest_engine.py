# coding: utf-8

'''
Tests for engine.py (The Game Itself).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.zest.base.engine import ZestEngine
from veredi.base.const   import VerediHealth
from veredi.debug.const  import DebugFlag

from .                   import engine

from .ecs.const          import SystemTick, SystemPriority

from .ecs.base.component import (Component,
                                 ComponentLifeCycle)
from .ecs.base.entity    import EntityLifeCycle
from .ecs.base.system    import (System,
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

    def _configure(self,
                   context):
        self.ents_seen = {
            SystemTick.TIME:        set(),
            SystemTick.CREATION:    set(),
            SystemTick.PRE:         set(),
            SystemTick.STANDARD:    set(),
            SystemTick.POST:        set(),
            SystemTick.DESTRUCTION: set(),
        }

    def _look_at_entities(self, tick, time_mgr, comp_mgr, entity_mgr):
        for entity in self._wanted_entities(tick,
                                            time_mgr, comp_mgr, entity_mgr):
            self.ents_seen[tick].add(entity.id)

    def test_saw_total(self):
        return (len(self.ents_seen[SystemTick.TIME])
                + len(self.ents_seen[SystemTick.CREATION])
                + len(self.ents_seen[SystemTick.PRE])
                + len(self.ents_seen[SystemTick.STANDARD])
                + len(self.ents_seen[SystemTick.POST])
                + len(self.ents_seen[SystemTick.DESTRUCTION]))

    def test_saw_entity(self, tick, id):
        return id in self.ents_seen[tick]

    def test_clear_seen(self):
        for each in self.ents_seen:
            each.clear()

    def _update_time(self,
                     time_mgr,
                     component_mgr,
                     entity_mgr):
        self._look_at_entities(SystemTick.TIME_MGR,
                               time_mgr, component_mgr, entity_mgr)
        return VerediHealth.HEALTHY

    def _update_creation(self,
                         time_mgr,
                         component_mgr,
                         entity_mgr):
        self._look_at_entities(SystemTick.CREATION,
                               time_mgr, component_mgr, entity_mgr)
        return VerediHealth.HEALTHY

    def _update_pre(self,
                    time_mgr,
                    component_mgr,
                    entity_mgr):
        self._look_at_entities(SystemTick.PRE,
                               time_mgr, component_mgr, entity_mgr)
        return VerediHealth.HEALTHY

    def _update(self,
                time_mgr,
                component_mgr,
                entity_mgr):
        self._look_at_entities(SystemTick.STANDARD,
                               time_mgr, component_mgr, entity_mgr)
        return VerediHealth.HEALTHY

    def _update_post(self,
                     time_mgr,
                     component_mgr,
                     entity_mgr):
        self._look_at_entities(SystemTick.POST,
                               time_mgr, component_mgr, entity_mgr)
        return VerediHealth.HEALTHY

    def _update_destruction(self,
                            time_mgr,
                            component_mgr,
                            entity_mgr):
        self._look_at_entities(SystemTick.DESTRUCTION,
                               time_mgr, component_mgr, entity_mgr)
        return VerediHealth.HEALTHY


class SysJeff(SysTest):
    def _configure(self,
                   context):
        super()._configure(context)
        self._ticks = (SystemTick.PRE
                       | SystemTick.STANDARD
                       | SystemTick.POST)

    @property
    def dotted(self):
        return 'veredi.game.zest_engine.SysJeff'

    def priority(self):
        return SystemPriority.MEDIUM + 13

    def required(self):
        return {CompOne, CompTwo}


class SysJill(SysTest):
    def _configure(self,
                   context):
        super()._configure(context)
        self._ticks = SystemTick.STANDARD
        sub = context.sub
        if 'system' in sub:
            self.x = sub['system']['x']
            self.y = sub['system']['y']
        else:
            self.x = None
            self.y = None

    @property
    def dotted(self):
        return 'veredi.game.zest_engine.SysJill'

    def priority(self):
        return SystemPriority.HIGH

    def required(self):
        return {CompOne}


class SysNoTick(SysTest):
    def _configure(self,
                   context):
        super()._configure(context)
        self._ticks = None

    @property
    def dotted(self):
        return 'veredi.game.zest_engine.SysNoTick'

    def priority(self):
        return SystemPriority.LOW


class SysNoReq(SysTest):
    def _configure(self,
                   context):
        super()._configure(context)
        self._ticks = None

    @property
    def dotted(self):
        return 'veredi.game.zest_engine.SysNoReq'

    def required(self):
        return None


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_Engine(ZestEngine):

    def set_up(self):
        self.debug_flags = DebugFlag.GAME_ALL
        super().set_up()

    def create_entities(self):
        def mkcmp(comp):
            # Can only create by Component Type, this way (sans context).
            return self.manager.component.create(comp, None)

        comps_1_2_x = set([mkcmp(CompOne), mkcmp(CompTwo)])
        comps_1_x_x = set([mkcmp(CompOne)])
        comps_1_2_3 = set([mkcmp(CompOne), mkcmp(CompTwo), mkcmp(CompThree)])
        comps_x_2_3 = set([                mkcmp(CompTwo), mkcmp(CompThree)])

        sub = self.context.sub

        sub.setdefault('entity', {})['components'] = comps_1_2_x
        self.ent_1_2_x = self.manager.entity.create(1, self.context)

        sub['entity']['components'] = comps_1_x_x
        self.ent_1_x_x = self.manager.entity.create(2, self.context)
        sub['entity']['components'] = comps_1_2_3
        self.ent_1_2_3 = self.manager.entity.create(1, self.context)
        sub['entity']['components'] = comps_x_2_3
        self.ent_x_2_3 = self.manager.entity.create(3, self.context)

        sub.pop('entity')

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
        self.assertTrue(self.manager.event)
        self.assertTrue(self.manager.time)
        self.assertTrue(self.manager.component)
        self.assertTrue(self.manager.entity)
        self.assertTrue(self.engine)

    def test_ticks_start(self):
        self.assertEqual(self.engine.life_cycle, SystemTick.INVALID)
        self.assertEqual(self.engine.tick, SystemTick.INVALID)

        run = {
            # ---
            # Life-Cycle
            # ---
            # Max ticks in start life-cycle.
            SystemTick.TICKS_START: 10,

            # ---
            # Ticks
            # ---
            # Max ticks for each tick in TICKS_START.
            SystemTick.GENESIS:      5,
            SystemTick.INTRA_SYSTEM: 5,
        }

        # - - - - - - - - - - - - - - -
        # Run the entire test!!!
        # - - - - - - - - - - - - - - -
        # This is simple because we want engine_run() to be capable of the
        # entire start life-cycle.
        ran = self.engine_run(SystemTick.TICKS_START,
                              run)

        max_life = run[SystemTick.TICKS_START]
        self.assertLess(ran[SystemTick.TICKS_START],     max_life)
        self.assertGreater(ran[SystemTick.GENESIS],      0)
        self.assertGreater(ran[SystemTick.INTRA_SYSTEM], 0)

    def test_ticks_end(self):
        # Engine shouldn't've started yet...
        self.assertEqual(self.engine.life_cycle, SystemTick.INVALID)
        self.assertEqual(self.engine.tick, SystemTick.INVALID)

        # Start it so we can stop it.
        self.engine_life_start()

        # Stop it so we can test it.
        self.engine.stop()

        run = {
            # ---
            # Life-Cycle
            # ---
            # Max ticks in end life-cycle.
            SystemTick.TICKS_END: 20,

            # ---
            # Ticks
            # ---
            # Max ticks for each tick in TICKS_END.
            SystemTick.APOPTOSIS:  5,
            SystemTick.APOCALYPSE: 5,
            SystemTick.THE_END:    1,
            SystemTick.FUNERAL:    1,
        }

        # - - - - - - - - - - - - - - -
        # Run the entire test!!!
        # - - - - - - - - - - - - - - -
        # This is simple because we want engine_run() to be capable of the
        # entire end life-cycle.
        ran = self.engine_run(SystemTick.TICKS_END,
                              run)

        max_life = run[SystemTick.TICKS_END]
        self.assertLess(ran[SystemTick.TICKS_END],     max_life)
        self.assertGreater(ran[SystemTick.APOPTOSIS],  0)
        self.assertGreater(ran[SystemTick.APOCALYPSE], 0)
        self.assertEqual(ran[SystemTick.THE_END],      1)
        self.assertEqual(ran[SystemTick.FUNERAL],      1)

        self.assertNotIn(SystemTick.FUNERAL | SystemTick.THE_END, ran)

    def test_ticks_run(self):
        # Engine shouldn't've started yet...
        self.assertEqual(self.engine.life_cycle, SystemTick.INVALID)
        self.assertEqual(self.engine.tick, SystemTick.INVALID)

        # Start it so we can run it.
        self.engine_life_start()

        run = {
            # ---
            # Life-Cycle
            # ---
            # Run 2 to make sure it cycles properly.
            SystemTick.TICKS_RUN: 2,

            # ---
            # Ticks
            # ---
            # These are ignored since a 'running' tick is one cycle through all
            # of these in order.
            #
            # SystemTick.TIME:     1,
            # SystemTick.CREATION: 1,
            # SystemTick.PRE:      1,
            # SystemTick.STANDARD: 1,
            # SystemTick.POST:     1,
        }

        # - - - - - - - - - - - - - - -
        # Run the entire test!!!
        # - - - - - - - - - - - - - - -
        # This is simple because we want engine_run() to be capable of the
        # entire running life-cycle.
        ran = self.engine_run(SystemTick.TICKS_RUN,
                              run)

        expected = run[SystemTick.TICKS_RUN]
        self.assertEqual(ran[SystemTick.TICKS_RUN], expected)
        self.assertEqual(ran[SystemTick.TIME],      expected)
        self.assertEqual(ran[SystemTick.CREATION],  expected)
        self.assertEqual(ran[SystemTick.PRE],       expected)
        self.assertEqual(ran[SystemTick.STANDARD],  expected)
        self.assertEqual(ran[SystemTick.POST],      expected)

    def test_a_full_life(self):
        # Engine shouldn't've started yet...
        self.assertEqual(self.engine.life_cycle, SystemTick.INVALID)
        self.assertEqual(self.engine.tick, SystemTick.INVALID)

        # Start, run, end via base class.
        # It should do what we've just tested in test_ticks_<cycle>().
        self.engine_life_start()

        tick_amounts = {
            # Max ticks of standard game loop.
            SystemTick.TICKS_RUN: 10,
        }
        self.engine_run(SystemTick.TICKS_RUN,
                        tick_amounts)

        self.engine_life_end()

    def test_set_up(self):
        # Push our systems into the engine before we start it so they go
        # through a normal engine TICKS_START.
        jeff_id, jill_id = self.init_many_systems(SysJeff, SysJill)

        # Get engine started.
        self.engine_life_start()

        self.assertTrue(len(self.manager.system._system) > 0)
        for sid in self.manager.system._system._data0:
            sys = self.manager.system.get(sid)
            self.assertIsNotNone(sys)
            self.assertEqual(sys.life_cycle, SystemLifeCycle.ALIVE)

        # Create stuff.
        self.create_entities()

        # Tick once for any systems to deal with entity's creation.
        self.engine_tick()

        self.assertTrue(len(self.manager.component._component_by_id) > 0)
        for cid in self.manager.component._component_by_id:
            comp = self.manager.component.get(cid)
            self.assertIsNotNone(comp)
            self.assertEqual(comp.life_cycle, ComponentLifeCycle.ALIVE)

        self.assertTrue(len(self.manager.entity._entity) > 0)
        for eid in self.manager.entity._entity:
            ent = self.manager.entity.get(eid)
            self.assertIsNotNone(ent)
            self.assertEqual(ent.life_cycle, EntityLifeCycle.ALIVE)

        # Filter out the required systems that were created. Just want to check
        # Jeff and Jill.
        j_and_j_schedule = [
            each
            for each in self.manager.system._schedule
            if isinstance(each, (SysJeff, SysJill))
        ]
        self.assertEqual(j_and_j_schedule,
                         [self.manager.system.get(jill_id),
                          self.manager.system.get(jeff_id)])

    def test_tickless_sys(self):
        # Push our systems into the engine before we start it so they go
        # through a normal engine TICKS_START.
        sids = self.init_many_systems(SysNoTick)

        # Get engine started.
        self.engine_life_start()

        self.create_entities()

        # Tick.
        self.engine_tick()

        # Shouldn't've been called.
        noop = self.manager.system.get(sids[0])
        self.assertIsInstance(noop, SysNoTick)
        self.assertEqual(noop.test_saw_total(), 0)

        # Once more with entity.
        self.create_entities()
        self.engine_tick()
        self.assertEqual(noop.test_saw_total(), 0)

    def test_reqless_sys(self):
        # Push our systems into the engine before we start it so they go
        # through a normal engine TICKS_START.
        sids = self.init_many_systems(SysNoReq)
        chill_sys = self.manager.system.get(sids[0])

        # Get engine started.
        self.engine_life_start()

        # Run a tick.
        self.engine_tick()
        # guess we can check this too...
        self.assertEqual(chill_sys.test_saw_total(), 0)

        # Once more with entity.
        self.create_entities()
        self.engine_tick()
        self.assertEqual(chill_sys.test_saw_total(), 0)

    def test_multi_sys_see_ents(self):
        # Register, set up, and run 'em.
        sids = self.init_many_systems(SysNoReq,
                                      SysNoTick,
                                      SysJeff,
                                      SysJill)
        no_req = self.manager.system.get(sids[0])
        no_tick = self.manager.system.get(sids[1])
        jeff = self.manager.system.get(sids[2])
        jill = self.manager.system.get(sids[3])

        # Get engine started.
        self.engine_life_start()

        # Run one tick.
        self.engine_tick()

        # Check that no entities were seen.
        self.assertEqual(no_req.test_saw_total(), 0)
        self.assertEqual(no_tick.test_saw_total(), 0)
        self.assertEqual(jeff.test_saw_total(), 0)
        self.assertEqual(jill.test_saw_total(), 0)

        # Once more with entities.
        self.create_entities()
        self.engine_tick()
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
        tick = SystemTick.CREATION
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

        tick = SystemTick.DESTRUCTION
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
        tick = SystemTick.CREATION
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
        tick = SystemTick.DESTRUCTION
        self.assertEqual(self.saw_ents(jill, tick, self.ent_ids),
                         expected_ids)

    # TODO: Test that a system barfing exceptions all over the place doesn't
    # kill the engine.


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.game.zest_engine

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
