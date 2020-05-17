# coding: utf-8

'''
Tests for the generic System class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from . import system
from veredi.entity import component

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
    last_tick = system.SystemTick.DEATH

    def __init__(self):
        super().__init__()
        self._ticks = (system.SystemTick.PRE
                       | system.SystemTick.STANDARD
                       | system.SystemTick.POST)

    def priority(self):
        return system.SystemPriority.MEDIUM + 13

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
        last_tick = system.SystemTick.PRE
        return system.SystemHealth.HEALTHY

    def update(self,
               time,
               sys_entities,
               sys_time):
        '''
        Normal/Standard upate. Basically everything should happen here.
        '''
        last_tick = system.SystemTick.STANDARD
        return system.SystemHealth.FATAL

    def update_post(self,
                    time,
                    sys_entities,
                    sys_time):
        '''
        Post-update. For any systems that need to squeeze in something just
        after actual tick.
        '''
        last_tick = system.SystemTick.POST
        return system.SystemHealth.FATAL


class SysJill(system.System):
     def priority(self):
        return system.SystemPriority.HIGH


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_System(unittest.TestCase):

    def setUp(self):
        self.sys = SysJeff()

    def tearDown(self):
        self.sys = None

    def test_init(self):
        self.assertTrue(self.sys)

    def test_priority(self):
        self.assertEqual(self.sys.priority(), system.SystemPriority.MEDIUM + 13)

        sys2 = SysJill()

        self.assertEqual(sys2.priority(), system.SystemPriority.HIGH)

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
        self.assertTrue(self.sys.last_tick, system.SystemTick.DEATH)

        self.sys.update_pre(1.0, None, None)
        self.assertTrue(self.sys.last_tick, system.SystemTick.PRE)

        self.sys.update(1.0, None, None)
        self.assertTrue(self.sys.last_tick, system.SystemTick.STANDARD)

        health = self.sys.update_post(1.0, None, None)
        self.assertTrue(self.sys.last_tick, system.SystemTick.POST)
        self.assertTrue(health, system.SystemHealth.HEALTHY)
