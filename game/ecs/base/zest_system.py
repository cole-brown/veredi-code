# coding: utf-8

'''
Tests for the generic System class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Tuple, Literal


from veredi.zest.base.unit import ZestBase
from veredi.zest.zpath     import TestType

from veredi.base.const import VerediHealth

from .  import system
from .. import const
from .  import component

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Mockups
# -----------------------------------------------------------------------------

class CompOne(component.MockComponent):
    pass


class CompTwo(component.MockComponent):
    pass


class SysJeff(system.MockSystem):
    last_tick = system.SystemTick.DESTRUCTION

    def _configure(self,
                   context):
        self._ticks = (system.SystemTick.PRE
                       | system.SystemTick.STANDARD
                       | system.SystemTick.POST)

    def priority(self):
        return const.SystemPriority.MEDIUM + 13

    def required(self):
        return {CompOne, CompTwo}

    def _update_pre(self) -> VerediHealth:
        '''
        Pre-update. For any systems that need to squeeze in something just
        before actual tick.
        '''
        self.last_tick = const.SystemTick.PRE
        return VerediHealth.HEALTHY

    def _update(self) -> VerediHealth:
        '''
        Normal/Standard upate. Basically everything should happen here.
        '''
        self.last_tick = const.SystemTick.STANDARD
        return VerediHealth.FATAL

    def _update_post(self) -> VerediHealth:
        '''
        Post-update. For any systems that need to squeeze in something just
        after actual tick.
        '''
        self.last_tick = const.SystemTick.POST
        return VerediHealth.FATAL


class SysJill(system.MockSystem):

    def priority(self):
        return const.SystemPriority.HIGH


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_System(ZestBase):

    def pre_set_up(self,
                   # Ignored params:
                   filename:  Literal[None]  = None,
                   extra:     Literal[Tuple] = (),
                   test_type: Literal[None]  = None) -> None:
        super().pre_set_up(filename=__file__)

    def set_up(self):
        self.sys = SysJeff(None, 1, None)

    def tear_down(self):
        self.sys = None

    def test_init(self):
        self.assertTrue(self.sys)

    def test_priority(self):
        self.assertEqual(self.sys.priority(), const.SystemPriority.MEDIUM + 13)

        sys2 = SysJill(None, 2, None)

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

        self.sys._update_pre()
        self.assertTrue(self.sys.last_tick, const.SystemTick.PRE)

        self.sys._update()
        self.assertTrue(self.sys.last_tick, const.SystemTick.STANDARD)

        health = self.sys._update_post()
        self.assertTrue(self.sys.last_tick, const.SystemTick.POST)
        self.assertTrue(health, VerediHealth.HEALTHY)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.game.ecs.base.zest_system

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
