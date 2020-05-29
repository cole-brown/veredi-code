# coding: utf-8

'''
Tests for the generic System class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from veredi.base.const import VerediHealth

from . import system
from .. import const
from . import component

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Mockups
# -----------------------------------------------------------------------------

class CompOne(component.Component):
    pass


class CompTwo(component.Component):
    pass


class SysJeff(system.System):
    last_tick = system.SystemTick.DESTRUCTION

    def __init__(self, system_id, *args, **kwargs):
        super().__init__(self, system_id, *args, **kwargs)
        self._ticks = (const.SystemTick.PRE
                       | const.SystemTick.STANDARD
                       | const.SystemTick.POST)

    def priority(self):
        return const.SystemPriority.MEDIUM + 13

    def required(self):
        return {CompOne, CompTwo}

    def update_pre(self,
                   time,
                   sys_entities,
                   sys_time):
        '''
        Pre-update. For any systems that need to squeeze in something just
        before actual tick.
        '''
        last_tick = const.SystemTick.PRE
        return VerediHealth.HEALTHY

    def update(self,
               time,
               sys_entities,
               sys_time):
        '''
        Normal/Standard upate. Basically everything should happen here.
        '''
        last_tick = const.SystemTick.STANDARD
        return VerediHealth.FATAL

    def update_post(self,
                    time,
                    sys_entities,
                    sys_time):
        '''
        Post-update. For any systems that need to squeeze in something just
        after actual tick.
        '''
        last_tick = const.SystemTick.POST
        return VerediHealth.FATAL


class SysJill(system.System):
     def priority(self):
        return const.SystemPriority.HIGH


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_System(unittest.TestCase):

    def setUp(self):
        self.sys = SysJeff(1)

    def tearDown(self):
        self.sys = None

    def test_init(self):
        self.assertTrue(self.sys)

    def test_priority(self):
        self.assertEqual(self.sys.priority(), const.SystemPriority.MEDIUM + 13)

        sys2 = SysJill(2)

        self.assertEqual(sys2.priority(), const.SystemPriority.HIGH)

        self.assertTrue(sys2.priority() < self.sys.priority())
        systems = [self.sys, sys2]
        systems.sort(key=system.System.sort_key)
        self.assertEqual(systems,
                         [sys2, self.sys])

    def test_required(self):
        required = self.sys.required()
        self.assertTrue(CompOne in required)
        self.assertTrue(CompTwo in required)

    def test_tick(self):
        self.assertTrue(self.sys.last_tick, const.SystemTick.DESTRUCTION)

        self.sys.update_pre(1.0, None, None)
        self.assertTrue(self.sys.last_tick, const.SystemTick.PRE)

        self.sys.update(1.0, None, None)
        self.assertTrue(self.sys.last_tick, const.SystemTick.STANDARD)

        health = self.sys.update_post(1.0, None, None)
        self.assertTrue(self.sys.last_tick, const.SystemTick.POST)
        self.assertTrue(health, VerediHealth.HEALTHY)