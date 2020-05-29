# coding: utf-8

'''
Tests for the DataSystem class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from veredi.zest import zmake

from ..ecs.event import EventManager
from ..ecs.component import (ComponentManager,
                             ComponentEvent,
                             ComponentLifeEvent)

from .system import DataSystem
from .event import DecodedEvent, DataSavedEvent

from veredi.rules.d20 import health


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_DataSystem(unittest.TestCase):
    '''
    Test our DataSystem with HealthComponent class against some health data.
    '''

    def setUp(self):
        self.config            = zmake.config()
        self.event_manager     = EventManager(self.config)
        self.component_manager = ComponentManager(self.config,
                                                  self.event_manager)
        self.system            = DataSystem(1)

    def tearDown(self):
        self.config            = None
        self.event_manager     = None
        self.component_manager = None
        self.system            = None

    def test_init(self):
        self.assertTrue(self.config)
        self.assertTrue(self.event_manager)
        self.assertTrue(self.component_manager)
        self.assertTrue(self.system)

#     def test_tick(self):
#         self.assertTrue(self.sys.last_tick, const.SystemTick.DESTRUCTION)
#
#         self.sys.update_pre(1.0, None, None)
#         self.assertTrue(self.sys.last_tick, const.SystemTick.PRE)
#
#         self.sys.update(1.0, None, None)
#         self.assertTrue(self.sys.last_tick, const.SystemTick.STANDARD)
#
#         health = self.sys.update_post(1.0, None, None)
#         self.assertTrue(self.sys.last_tick, const.SystemTick.POST)
#         self.assertTrue(health, VerediHealth.HEALTHY)
