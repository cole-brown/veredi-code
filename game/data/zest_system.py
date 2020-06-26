# coding: utf-8

'''
Tests for the DataSystem class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from veredi.zest import zmake, zontext
from veredi.base.context import UnitTestContext
from veredi.logger import log

from ..ecs.event import EventManager
from ..ecs.base.identity import ComponentId
from ..ecs.component import ComponentManager

from .system import DataSystem
from .event import DecodedEvent, DataLoadedEvent

from .component import DataComponent
from veredi.rules.d20 import health


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# Similar to game.data.codec.zest_system's test_data, but in python form.
test_data = [
    {
        'doc-type': 'metadata',
        'author': f"{__file__} and its authors",
    },

    {
        # Gotta add this on since it's injected by codec when decoding.
        'doc-type': 'component',

        'meta': {
            'registry': 'veredi.rules.d20.health.component',
        },

        'health': {
            # Tracks current hit point amounts.
            'current': {
                'hit-points': '${sum(${health.current.*})}',
                'permanent': 35,
                'temporary': 11,
            },

            # Tracks maximums from e.g. leveling, monster templates, etc.
            'maximum': {
                'class': [
                    {
                        'angry-unschooled-fighter': 1,
                        'hit-points': 12,
                    },
                    {
                        'angry-unschooled-fighter': 2,
                        'hit-points': 9,
                    },
                ],
                'hit-points': 21,
            },
            'unconscious': {'hit-points': 0},
            'death': {'hit-points': 0},
            'resistance': {},
        }
    },
]


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_DataSystem(unittest.TestCase):
    '''
    Test our DataSystem with HealthComponent class against some health data.
    '''

    def setUp(self):
        self.debugging         = False
        self.config            = zmake.config()
        self.context           = zontext.test(self.__class__.__name__,
                                              'setUp')
        self.event_manager     = EventManager(self.config)
        self.component_manager = ComponentManager(self.config,
                                                  self.event_manager)

        self.manager          = zmake.meeting(
            configuration=self.config,
            event_manager=self.event_manager,
            component_manager=self.component_manager)

        self.system            = DataSystem(self.context,
                                            1,
                                            self.manager)
        self.events            = []

    def tearDown(self):
        self.debugging         = False
        self.config            = None
        self.context           = None
        self.event_manager     = None
        self.component_manager = None
        self.system            = None
        self.events            = None

    def sub_loaded(self):
        self.event_manager.subscribe(DataLoadedEvent, self.event_decoded)

    def set_up_subs(self):
        self.sub_loaded()
        self.system.subscribe(self.event_manager)

    def event_decoded(self, event):
        self.events.append(event)

    def make_it_so(self, event):
        '''
        Notifies the event for immediate action.
        Which /should/ cause something to process it and queue up an event.
        So we publish() in order to get that one sent out.
        '''
        self.event_manager.notify(event, True)
        self.event_manager.publish()
        self.assertTrue(self.events)

    def test_init(self):
        self.assertTrue(self.config)
        self.assertTrue(self.event_manager)
        self.assertTrue(self.component_manager)
        self.assertTrue(self.system)

    def test_event_loaded(self):
        self.set_up_subs()

        ctx = UnitTestContext(
            self.__class__.__name__,
            'test_event_deserialize',
            {'unit-testing': "Manually created DecodedEvent."})
        ctx.pull(self.context)
        decode_event = DecodedEvent(
            42,
            0xDEADBEEF,
            ctx,
            data=test_data)

        self.assertTrue(decode_event)
        self.assertFalse(self.events)
        with log.LoggingManager.on_or_off(self.debugging):
            self.make_it_so(decode_event)

        self.assertEqual(len(self.events), 1)
        self.assertIsInstance(self.events[0], DataLoadedEvent)

        event = self.events[0]
        cid = event.component_id
        self.assertNotEqual(cid, ComponentId.INVALID)
        component = self.component_manager.get(cid)
        self.assertIsInstance(component, DataComponent)

        self.assertIsInstance(component, health.HealthComponent)

        data_source = test_data[1]
        # Make sure we are checking our correct part of data.
        self.assertIn('health', data_source)

        data_processed = component.persistent
        self.assertEqual(data_source, data_processed)
