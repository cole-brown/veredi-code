# coding: utf-8

'''
Tests for the generic System class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from datetime import datetime, timezone


from veredi.logs           import log

from veredi.zest.base.unit import ZestBase
from veredi.base.context   import UnitTestContext

from veredi.base.strings   import label
from veredi                import time

from .time                 import TimeManager
from ..time.tick.round     import TickRounds


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_Time(ZestBase):

    def set_up(self):
        self.round_amount = 6
        self.round_duration = time.duration(f'{self.round_amount} seconds')
        context = UnitTestContext(
            __file__,
            self,
            'set_up',
            data={
                TickRounds.dotted(): {
                    'seconds-per-round': self.round_duration,
                    'current-round':     0,
                },
                TimeManager.dotted(): {
                    # Fill this in once we make it.
                    'tick': None,
                },
            })
        self.tick = TickRounds(context)
        context.sub_get(TimeManager.dotted())['tick'] = self.tick
        self.time = TimeManager()
        self.time.finalize_init(None,  # We want to test without a DataManager.
                                _unit_test=context)
        self.midnight_utc = datetime.now(timezone.utc).replace(hour=0,
                                                               minute=0,
                                                               second=0,
                                                               microsecond=0)

    def tear_down(self):
        self.time = None

    def test_init(self):
        self.assertTrue(self.time)
        self.assertEqual(self.time.tick.current_seconds, 0)
        self.assertEqual(self.time.clock.time_stamp,
                         self.midnight_utc.timestamp())

    def test_tick(self):
        # Always should start at negative count.
        self.assertLess(self.time.tick.count, 0)

        # We told it to start at round zero, so seconds should be zero too.
        start = 0
        self.assertEqual(start,
                         self.time.tick.current_seconds)
        # Nothing's happening, so exact and current are the same.
        self.assertEqual(self.time.tick.exact_seconds,
                         self.time.tick.current_seconds)

        # Do some delta ticks.
        curr_deltas = self.time.delta()
        self.assertEqual(curr_deltas, 0)
        self.assertEqual(self.time.tick.count, curr_deltas)
        curr_deltas = self.time.delta()
        self.assertEqual(curr_deltas, 1)
        self.assertEqual(self.time.tick.count, curr_deltas)
        curr_deltas = self.time.delta()
        self.assertEqual(curr_deltas, 2)
        self.assertEqual(self.time.tick.count, curr_deltas)

        # Seconds should still be zero since we haven't gotten into a round or
        # turn or anything.
        self.assertEqual(0,
                         self.time.tick.current_seconds)
        self.assertEqual(self.time.tick.exact_seconds,
                         self.time.tick.current_seconds)

        # Fast forward time a bit...
        now = 999
        # We want something that doesn't divide cleanly, so make sure it has a
        # remainder.
        self.assertGreater((now % self.round_amount), 0)
        # Set time.
        self.time.tick.current_seconds = now
        # Current seconds should not be what you set it to - it maths out to a
        # multiple of the round time.
        self.assertNotEqual(now,
                            self.time.tick.current_seconds)
        self.assertEqual((now // self.round_amount) * self.round_amount,
                         self.time.tick.current_seconds)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.game.ecs.zest_time

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
