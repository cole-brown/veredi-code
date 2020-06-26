# coding: utf-8

'''
Tests for the CodecSystem class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest
from io import StringIO

from veredi.zest import zmake, zontext
from veredi.base.context import UnitTestContext

from .system import CodecSystem
from ..event import (DeserializedEvent, DataSaveRequest,
                     DecodedEvent, EncodedEvent)
from ...ecs.event import EventManager


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Mockups
# -----------------------------------------------------------------------------

test_data = '''
--- !component

meta:
  registry: veredi.unit-test.health

health:
  # Tracks current hit point amounts.
  current:
    hit-points: ${sum(${health.current.*})}
    permanent: 35
    temporary: 11

  # Tracks maximums from e.g. leveling, monster templates, etc.
  maximum:
    class:
      - angry-unschooled-fighter: 1
        hit-points: 12
      - angry-unschooled-fighter: 2
        hit-points: 9
'''


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_CodecSystem(unittest.TestCase):

    def setUp(self):
        self.debugging = False
        self.config        = zmake.config()
        self.event_manager = EventManager(self.config)
        self.manager       = zmake.meeting(configuration=self.config,
                                           event_manager=self.event_manager)
        self.codec         = CodecSystem(None, 1, self.manager)
        self.events        = []

    def tearDown(self):
        self.debugging     = False
        self.codec         = None
        self.config        = None
        self.event_manager = None
        self.events        = None

    def sub_decoded(self):
        self.event_manager.subscribe(DecodedEvent, self.event_decoded)

    def set_up_subs(self):
        self.sub_decoded()
        self.codec.subscribe(self.event_manager)

    def event_decoded(self, event):
        self.events.append(event)

    def test_init(self):
        self.assertTrue(self.codec)
        self.assertTrue(self.event_manager)

    def test_subscribe(self):
        self.assertFalse(self.event_manager._subscriptions)
        self.codec.subscribe(self.event_manager)
        self.assertTrue(self.event_manager._subscriptions)

        self.assertEqual(self.event_manager,
                         self.codec._manager.event)

    def test_event_deserialize(self):
        self.set_up_subs()

        with StringIO(test_data) as stream:
            self.assertTrue(stream)

            event = DeserializedEvent(
                42,
                0xDEADBEEF,
                UnitTestContext(
                    self.__class__.__name__,
                    'test_event_deserialize',
                    {'unit-testing': "string 'test-data' in zest_system.py"}),
                data=stream)
            self.assertTrue(event)
            self.event_manager.notify(event, True)
            # CodecSystem will reply with its own event (not immediately
            # published?)... publish it for it.
            self.event_manager.publish()
            self.assertTrue(self.events)

            # §-TODO-§ [2020-05-22]: test what we got back!
            received = self.events[0]
            self.assertIsNotNone(received)
            self.assertEqual(type(received), DecodedEvent)
            self.assertIsInstance(received.data, list)
            self.assertEqual(len(received.data), 1)
            component = received.data[0]

            meta = component.get('meta', {})
            self.assertTrue(meta)
            self.assertEqual(meta['registry'],
                             'veredi.unit-test.health')

            health = component.get('health', {})
            self.assertTrue(health)
            current = health.get('current', {})
            self.assertTrue(current)
            self.assertEqual(current['hit-points'],
                             '${sum(${health.current.*})}')
            self.assertEqual(current['permanent'], 35)
            self.assertEqual(current['temporary'], 11)

            maximum = health.get('maximum', {})
            self.assertTrue(maximum)
            klass = maximum.get('class', {})
            self.assertTrue(klass)
            self.assertIsInstance(klass, list)
            self.assertEqual(klass[0]['angry-unschooled-fighter'], 1)
            self.assertEqual(klass[0]['hit-points'], 12)
            self.assertEqual(klass[1]['angry-unschooled-fighter'], 2)
            self.assertEqual(klass[1]['hit-points'], 9)
