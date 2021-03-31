# coding: utf-8

'''
Tests for SystemManager.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.zest.base.unit import ZestBase
from veredi.zest           import zmake

from veredi.base.const     import VerediHealth
from veredi.base.context   import UnitTestContext
from veredi.debug.const    import DebugFlag
from veredi.data           import background

from .event                import EventManager
from .time                 import TimeManager
from .component            import ComponentManager
from .entity               import EntityManager
from .system               import (SystemManager,
                                   SystemEvent,
                                   SystemLifeEvent)

from .const                import SystemTick, SystemPriority

from .base.identity        import SystemId
from .base.component       import MockComponent
from .base.system          import System, SystemLifeCycle


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Mockups
# -----------------------------------------------------------------------------

class CompOne(MockComponent):
    pass


class CompTwo(MockComponent):
    pass


class CompThree(MockComponent):
    pass


class SysTest(System):

    @classmethod
    def dotted(klass: 'SysTest') -> str:
        return 'veredi.system.test'

    def _conifgure(self, context):
        self.ents_seen = {
            SystemTick.TIME:        set(),
            SystemTick.CREATION:    set(),
            SystemTick.PRE:         set(),
            SystemTick.STANDARD:    set(),
            SystemTick.POST:        set(),
            SystemTick.DESTRUCTION: set(),
        }

    def _look_at_entities(self, tick):
        for entity in self._wanted_entities(tick):
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

    def _update_time(self) -> VerediHealth:
        self._look_at_entities(SystemTick.TIME)
        return VerediHealth.HEALTHY

    def _update_creation(self) -> VerediHealth:
        self._look_at_entities(SystemTick.CREATION)
        return VerediHealth.HEALTHY

    def _update_pre(self) -> VerediHealth:
        self._look_at_entities(SystemTick.PRE)
        return VerediHealth.HEALTHY

    def _update(self) -> VerediHealth:
        self._look_at_entities(SystemTick.STANDARD)
        return VerediHealth.HEALTHY

    def _update_post(self) -> VerediHealth:
        self._look_at_entities(SystemTick.POST)
        return VerediHealth.HEALTHY

    def _update_destruction(self) -> VerediHealth:
        self._look_at_entities(SystemTick.DESTRUCTION)
        return VerediHealth.HEALTHY


class SysJeff(SysTest):
    def _configure(self,
                   context):
        self._ticks = (SystemTick.PRE
                       | SystemTick.STANDARD
                       | SystemTick.POST)

    def priority(self):
        return SystemPriority.MEDIUM + 13

    def required(self):
        return {CompOne, CompTwo}


class SysJill(SysTest):

    def _configure(self,
                   context):
        self.x = context.sub['system']['x']
        self.y = context.sub['system']['y']

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

class Test_SystemManager(ZestBase):

    def set_up(self):
        self.event_mgr = None
        self.finish_set_up()

    def finish_set_up(self):
        self.time_mgr   = TimeManager()
        self.comp_mgr   = ComponentManager(self.config,
                                           self.event_mgr,
                                           self.debug_flags)
        self.entity_mgr = EntityManager(self.config,
                                        self.event_mgr,
                                        self.comp_mgr,
                                        self.debug_flags)
        self.system_mgr = SystemManager(self.event_mgr,
                                        self.debug_flags)

        self.events_recv = {}

    def tear_down(self):
        self.config      = None
        self.time_mgr    = None
        self.event_mgr   = None
        self.comp_mgr    = None
        self.entity_mgr  = None
        self.system_mgr  = None
        self.events_recv = None

    def register_events(self):
        self.event_mgr.subscribe(SystemEvent, self.event_comp_recv)
        self.event_mgr.subscribe(SystemLifeEvent, self.event_comp_recv)

    def clear_events(self):
        self.events_recv.clear()
        if self.event_mgr:
            self.event_mgr._events.clear()

    def event_comp_recv(self, event):
        if not self.events_recv:
            self.events_recv = {}
        self.events_recv.setdefault(type(event), []).append(event)

    def do_events(self):
        '''
        We're "doing events" if the SystemManager being tested knows about an
        EventManager.
        '''
        return bool(self.system_mgr._event)

    def create_entities(self):
        comps_1_2_x = set([CompOne(0), CompTwo(1)])
        comps_1_x_x = set([CompOne(2)])
        comps_1_2_3 = set([CompOne(3), CompTwo(4), CompThree(5)])
        comps_x_2_3 = set([            CompTwo(6), CompThree(7)])

        self.ent_1_2_x = self.entity_mgr.create(1, comps_1_2_x)
        self.ent_1_x_x = self.entity_mgr.create(2, comps_1_x_x)
        self.ent_1_2_3 = self.entity_mgr.create(1, comps_1_2_3)
        self.ent_x_2_3 = self.entity_mgr.create(3, comps_x_2_3)

        self.ent_ids = {
            self.ent_1_2_x,
            self.ent_1_x_x,
            self.ent_1_2_3,
            self.ent_x_2_3,
        }

    def create_system(self, sys_type, **kwargs):
        context = UnitTestContext(
            __file__,
            self,
            'create_system',
            data=({}
                  if not kwargs else
                  {'system': kwargs}))

        sid = self.system_mgr.create(sys_type,
                                     context)
        return sid

    def saw_ents(self, sys, tick, ent_ids):
        seen_ids = set()
        for id in ent_ids:
            seen = sys.test_saw_entity(tick, id)
            # Must have seen each expected id for success.
            if seen:
                seen_ids.add(id)
        return seen_ids

    def test_init(self):
        self.assertTrue(self.comp_mgr)
        self.assertTrue(self.entity_mgr)
        self.assertTrue(self.time_mgr)
        self.assertTrue(self.system_mgr)

    def test_create(self):
        self.assertEqual(self.system_mgr._system_id.peek(),
                         SystemId.INVALID.value)

        sid = self.create_system(SysJeff)
        self.assertNotEqual(sid, SystemId.INVALID)

        self.assertEqual(len(self.system_mgr._system_create), 1)
        self.assertEqual(len(self.system_mgr._system_destroy), 0)
        self.assertEqual(len(self.system_mgr._system), 1)

        if self.do_events():
            # We should not have event yet (not published), but the
            # EventManager should have (they were created/queued).
            num_events = 0
            for ev_type in (self.events_recv or ()):
                num_events += len(self.events_recv[ev_type])
            self.assertEqual(num_events, 0)
            self.assertTrue(self.event_mgr.has_queued)

            # Publish in order to get our events.
            self.event_mgr.publish()
            num_events = 0
            for ev_type in (self.events_recv or ()):
                num_events += len(self.events_recv[ev_type])
            self.assertEqual(num_events, 1)

            # Verify it.
            event = self.events_recv[SystemLifeEvent][0]
            self.assertIsNotNone(event)
            self.assertEqual(event.id, sid)
            self.assertEqual(event.type, SystemLifeCycle.CREATING)
            self.assertIsNone(event.context)

        # System should exist and be in CREATING state now...
        system = self.system_mgr.get(sid)
        self.assertIsNotNone(system)
        self.assertIsInstance(system,
                              System)
        self.assertEqual(system.id, sid)
        self.assertEqual(system.life_cycle,
                         SystemLifeCycle.CREATING)

    def test_create_args(self):
        self.assertEqual(self.system_mgr._system_id.peek(),
                         SystemId.INVALID.value)

        sid = self.create_system(SysJill, x=1, y=2)
        self.assertNotEqual(sid, SystemId.INVALID)

        # System should exist and have its args assigned.
        system = self.system_mgr.get(sid)
        self.assertIsNotNone(system)
        self.assertIsInstance(system,
                              SysJill)
        self.assertEqual(system.life_cycle,
                         SystemLifeCycle.CREATING)
        self.assertEqual(system.x, 1)
        self.assertEqual(system.y, 2)

    def test_destroy(self):
        self.assertEqual(self.system_mgr._system_id.peek(),
                         SystemId.INVALID.value)

        sid = 1
        self.system_mgr.destroy(sid)
        # System doesn't exist, so nothing happened.
        self.assertEqual(len(self.system_mgr._system_create), 0)
        self.assertEqual(len(self.system_mgr._system_destroy), 0)

        sid = self.create_system(SysJeff)
        # Now we should have a create...
        self.assertNotEqual(sid, SystemId.INVALID)
        self.assertEqual(len(self.system_mgr._system_create), 1)
        self.clear_events()  # don't care about create event
        # ...a destroy...
        self.system_mgr.destroy(sid)
        self.assertEqual(len(self.system_mgr._system_destroy), 1)
        # ...and a DESTROYING state.
        system = self.system_mgr.get(sid)
        self.assertIsNotNone(system)
        self.assertIsInstance(system,
                              SysJeff)
        self.assertEqual(system.life_cycle,
                         SystemLifeCycle.DESTROYING)

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

            event = self.events_recv[SystemLifeEvent][0]
            self.assertIsNotNone(event)
            self.assertEqual(event.id, sid)
            self.assertEqual(event.type, SystemLifeCycle.DESTROYING)
            self.assertIsNone(event.context)

    def test_creation(self):
        sid = self.create_system(SysJeff)
        self.assertNotEqual(sid, SystemId.INVALID)

        # System should exist and be in CREATING state now...
        system = self.system_mgr.get(sid)
        self.assertIsNotNone(system)
        self.assertEqual(system.id, sid)
        self.assertEqual(system.life_cycle,
                         SystemLifeCycle.CREATING)
        self.clear_events()  # don't care about create event

        # Tick past creation to get new system finished.
        self.system_mgr.creation(None)

        # System should still exist and be in ALIVE state now.
        self.assertIsNotNone(system)
        self.assertIsInstance(system,
                              SysJeff)
        self.assertEqual(system.id, sid)
        self.assertEqual(system.life_cycle,
                         SystemLifeCycle.ALIVE)

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

            event = self.events_recv[SystemLifeEvent][0]
            self.assertIsNotNone(event)
            self.assertEqual(event.id, sid)
            self.assertEqual(event.type, SystemLifeCycle.ALIVE)
            self.assertIsNone(event.context)

    def test_destruction(self):
        sid = self.create_system(SysJeff)
        self.assertNotEqual(sid, SystemId.INVALID)

        # System should exist and be in CREATING state now...
        system = self.system_mgr.get(sid)
        self.assertIsNotNone(system)
        self.assertEqual(system.id, sid)
        self.assertEqual(system.life_cycle,
                         SystemLifeCycle.CREATING)

        # Now (ask for) destroy!
        self.system_mgr.destroy(sid)
        self.clear_events()  # don't care about create/destroy event

        # Tick past destruction to get poor new system DEAD.
        self.system_mgr.destruction(None)

        # System should not exist as far as SystemManager cares,
        # and be in DEAD state now.
        self.assertFalse(self.system_mgr.get(sid))
        self.assertIsNotNone(system)
        self.assertIsInstance(system,
                              SysJeff)
        self.assertEqual(system.id, sid)
        self.assertEqual(system.life_cycle,
                         SystemLifeCycle.DEAD)

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

            event = self.events_recv[SystemLifeEvent][0]
            self.assertIsNotNone(event)
            self.assertEqual(event.id, sid)
            self.assertEqual(event.type, SystemLifeCycle.DEAD)
            self.assertIsNone(event.context)

    def test_scheduling(self):
        sid = self.create_system(SysFour)
        self.assertNotEqual(sid, SystemId.INVALID)

        sid = self.create_system(SysJeff)
        self.assertNotEqual(sid, SystemId.INVALID)

        sid = self.create_system(SysThree)
        self.assertNotEqual(sid, SystemId.INVALID)

        sid = self.create_system(SysJill, x=1, y=2)
        self.assertNotEqual(sid, SystemId.INVALID)

        # TODO [2020-06-01]: Did I... Forget to finish this?


class Test_SystemManager_Events(Test_SystemManager):
    def set_up(self):
        # Add EventManager so that tests in parent class will
        # generate/check events.
        self.event_mgr = EventManager(self.config, self.debug_flags)
        self.finish_set_up()
        self.register_events()


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.game.ecs.zest_system

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
