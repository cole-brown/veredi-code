# coding: utf-8

'''
Tests for the generic System class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from datetime import datetime, timezone
import decimal
import unittest

from . import time
from . import exceptions

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_Time(unittest.TestCase):

    def setUp(self):
        self.time = time.TimeManager()
        self.midnight_utc = datetime.now(timezone.utc).replace(hour=0,
                                                               minute=0,
                                                               second=0,
                                                               microsecond=0)

    def tearDown(self):
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
