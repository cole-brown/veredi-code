# coding: utf-8

'''
Test that event manager.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from veredi.zest import zmake

from .event import EventManager


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Mockups
# -----------------------------------------------------------------------------

class EventOne:
    id = 1

class EventTwo(EventOne):
    id = 2

class EventThree:
    id = 3


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_Events(unittest.TestCase):

    def setUp(self):
        self.config          = zmake.config()
        self.events          = EventManager(self.config)
        self.events_recvd    = {}
        self.handlers_called = {}

    def tearDown(self):
        self.config          = None
        self.events          = None
        self.events_recvd    = None
        self.handlers_called = None

    def event_handler_one(self, event):
        slot = self.events_recvd.setdefault(event.id, [])
        slot.append(event)
        self.handlers_called[1] = self.handlers_called.setdefault(1, 0) + 1

    def event_handler_two(self, event):
        slot = self.events_recvd.setdefault(event.id, [])
        slot.append(event)
        self.handlers_called[2] = self.handlers_called.setdefault(2, 0) + 1

    def event_handler_three(self, event):
        slot = self.events_recvd.setdefault(event.id, [])
        slot.append(event)
        self.handlers_called[3] = self.handlers_called.setdefault(3, 0) + 1

    def subscribe(self):
        self.events.subscribe(EventOne, self.event_handler_one)
        self.events.subscribe(EventTwo, self.event_handler_two)
        self.events.subscribe(EventThree, self.event_handler_three)

    def test_init(self):
        self.assertTrue(self.events)

    def test_subscribe(self):
        self.subscribe()
        self.assertEqual(len(self.events._subscriptions[EventOne]), 1)
        self.assertEqual(len(self.events._subscriptions[EventTwo]), 1)
        self.assertEqual(len(self.events._subscriptions[EventThree]), 1)

    def test_event_immediate(self):
        self.subscribe()

        event = EventOne()
        self.events.notify(event, True)
        self.assertEqual(self.events_recvd[event.id], [event])
        self.assertEqual(self.handlers_called[1], 1)

    def test_event_normal(self):
        self.subscribe()

        event = EventOne()
        self.events.notify(event)
        # Event should not be published yet.
        with self.assertRaises(KeyError) as context:
            self.events_recvd[event.id]
        with self.assertRaises(KeyError) as context:
            self.handlers_called[1]

        self.events.publish()
        # Now it should have gone out.
        self.assertEqual(self.events_recvd[event.id], [event])
        self.assertEqual(self.handlers_called[1], 1)

    def test_event_subclass(self):
        self.subscribe()

        event = EventTwo()
        self.events.notify(event)
        self.events.publish()

        # Now it should have gone out and triggered both
        # EventOne subs and EventTwo subs.

        # Since I'm lazy and all events just get appended to recvd, we'll
        # have a duplicate.
        self.assertEqual(self.events_recvd[event.id], [event, event])
        # Handlers 1 & 2 called once each (once per type we've registered)
        self.assertEqual(self.handlers_called[1], 1)
        self.assertEqual(self.handlers_called[2], 1)

    def test_several_events(self):
        self.subscribe()

        event1 = EventOne()
        event2 = EventTwo()
        event3 = EventThree()
        self.events.notify(event1)
        self.events.notify(event2)
        self.events.notify(event3)
        self.events.publish()

        # Since I'm lazy and all events just get appended to recvd, we'll have a
        # duplicate as EventTwo is a subclass of EventOne and triggers handlers
        # for both.
        self.assertEqual(self.events_recvd[event1.id],
                         [event1])
        self.assertEqual(self.events_recvd[event2.id],
                         [event2, event2])
        self.assertEqual(self.events_recvd[event3.id],
                         [event3])
        # Handlers called once per type we've registered.
        self.assertEqual(self.handlers_called[1], 2)
        self.assertEqual(self.handlers_called[2], 1)
        self.assertEqual(self.handlers_called[3], 1)
