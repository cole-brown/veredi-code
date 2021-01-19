# coding: utf-8

'''
Tests for the generic System class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from datetime import datetime, timezone

from veredi.zest.base.unit import ZestBase
from . import time

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_Time(ZestBase):

    def set_up(self):
        self.time = time.TimeManager()
        self.midnight_utc = datetime.now(timezone.utc).replace(hour=0,
                                                               minute=0,
                                                               second=0,
                                                               microsecond=0)

    def tear_down(self):
        self.time = None

    def test_init(self):
        self.assertTrue(self.time)
        self.assertEqual(self.time.tick.seconds, 0)
        self.assertEqual(self.time.clock.time_stamp,
                         self.midnight_utc.timestamp())

    def test_tick(self):
        start = self.time.seconds
        self.assertEqual(start,
                         self.time.tick.seconds)

        now = self.time.step()
        self.assertEqual(start + now,
                         self.time.tick.seconds)
        self.assertEqual(start + now,
                         self.time.seconds)

        now = 999
        self.time.seconds = now
        self.assertEqual(now,
                         self.time.tick.seconds)
        self.assertEqual(now,
                         self.time.seconds)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.game.ecs.zest_time

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
