# coding: utf-8

'''
Tests for the SerdesSystem class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from io import StringIO

from veredi.zest.base.system import ZestSystem
from veredi.base.context     import UnitTestContext

from .system                 import SerdesSystem
from ..event                 import (DeserializedEvent, DataSaveRequest,
                                     DecodedEvent, EncodedEvent)


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

class Test_SerdesSystem(ZestSystem):

    def set_up(self):
        super().set_up()
        self.serdes         = SerdesSystem(None, 1, self.manager)

    def tear_down(self):
        super().tear_down()
        self.serdes         = None

    def sub_decoded(self):
        self.manager.event.subscribe(DecodedEvent, self.event_decoded)

    def set_up_subs(self):
        self.sub_decoded()
        self.serdes.subscribe(self.manager.event)

    def event_decoded(self, event):
        self.events.append(event)

    def test_init(self):
        self.assertTrue(self.serdes)
        self.assertTrue(self.manager.event)

    def test_subscribe(self):
        self.assertFalse(self.manager.event._subscriptions)
        self.serdes.subscribe(self.manager.event)
        self.assertTrue(self.manager.event._subscriptions)

        self.assertEqual(self.manager.event,
                         self.serdes._manager.event)

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
            self.manager.event.notify(event, True)
            # SerdesSystem will reply with its own event (not immediately
            # published?)... publish it for it.
            self.manager.event.publish()
            self.assertTrue(self.events)

            # Test what we got back.
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


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.game.data.serdes.zest_system

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
