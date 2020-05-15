# coding: utf-8

'''
Test that event manager.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from . import game
from veredi.entity.component import (ComponentId,
                                     INVALID_COMPONENT_ID,
                                     Component)
from veredi.entity.entity import (EntityId,
                                  INVALID_ENTITY_ID,
                                  Entity)
from .event import EventManager
from .system import System

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Mockups
# -----------------------------------------------------------------------------

class CompOne(Component):
    pass


class CompTwo(CompOne):
    pass


class CompThree(Component):
    pass


class SysTest(System):
    pass
    # def __init__(self):
    #     super().__init__()
    #     self.ents_seen = {
    #         SystemTick.TIME:     set(),
    #         SystemTick.LIFE:     set(),
    #         SystemTick.PRE:      set(),
    #         SystemTick.STANDARD: set(),
    #         SystemTick.POST:     set(),
    #         SystemTick.DEATH:    set(),
    #     }


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_Events(unittest.TestCase):

    def setUp(self):
        self.events = EventManager()

    def tearDown(self):
        self.events = None

    def test_init(self):
        self.assertTrue(self.events)

#     def test_set_up(self):
#         jeff = SysJeff()
#         jill = SysJill()
#         self.game.register(jeff)
#         self.game.register(jill)
#
#         # Nothing in schedule yet.
#         self.assertFalse(self.game._sys_schedule)
#         # But they're ready...
#         self.assertTrue(self.game._sys_registration)
#
#         self.game.set_up()
#
#         # Now registered systems should be scheduled by priority.
#         self.assertFalse(self.game._sys_registration)
#         self.assertTrue(self.game._sys_schedule)
#         self.assertEqual(self.game._sys_schedule,
#                          [jill, jeff])
