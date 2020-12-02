# coding: utf-8

'''
Tests for the DataSystem class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.zest.base.system import ZestSystem
from veredi.zest import zload
from veredi.base.context import UnitTestContext
from veredi.logger import log

from ..ecs.event import EventManager
from ..ecs.base.identity import ComponentId
from ..ecs.component import ComponentManager

from .system import DataSystem
from .event import _DeserializedEvent, DataLoadedEvent

from .component import DataComponent
from veredi.rules.d20.pf2.health.component import HealthComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# Similar to game.data.serdes.zest_system's test_data, but in python form.
test_data = [
    {
        'doc-type': 'metadata',
        'author': f"{__file__} and its authors",
    },

    {
        # Gotta add this on since it's injected by serdes when decoding.
        'doc-type': 'component',

        'meta': {
            'registry': 'veredi.rules.d20.pf2.health.component',
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

class Test_DataSystem(ZestSystem):
    '''
    Test our DataSystem with HealthComponent class against some health data.
    '''

    def set_up(self):
        super().set_up()
        self.system = self.manager.system.get(DataSystem)

    def _set_up_ecs(self):
        '''
        Calls zload.set_up to create Meeting of EcsManagers, and a context from
        a config file.
        '''
        (self.manager, _,
         self.context, _) = zload.set_up(self.__class__.__name__,
                                         '_set_up_ecs',
                                         self.debugging,
                                         debug_flags=self.debug_flags,
                                         require_engine=False,
                                         desired_systems=[DataSystem])

    def test_init(self):
        self.assertTrue(self.manager.event)
        self.assertTrue(self.manager.component)
        self.assertTrue(self.system)

    def test_event_loaded(self):
        self.set_up_events(clear_self=True, clear_manager=True)

        ctx = UnitTestContext(
            self.__class__.__name__,
            'test_event_deserialize',
            {'unit-testing': "Manually created _DeserializedEvent."})
        ctx.pull(self.context)
        decode_event = _DeserializedEvent(
            42,
            0xDEADBEEF,
            ctx,
            data=test_data)

        self.assertTrue(decode_event)
        self.assertFalse(self.events)
        with log.LoggingManager.on_or_off(self.debugging):
            self.trigger_events(decode_event)

        self.assertEqual(len(self.events), 1)
        self.assertIsInstance(self.events[0], DataLoadedEvent)

        event = self.events[0]
        cid = event.component_id
        self.assertNotEqual(cid, ComponentId.INVALID)
        component = self.manager.component.get(cid)
        self.assertIsInstance(component, DataComponent)

        self.assertIsInstance(component, HealthComponent)

        data_source = test_data[1]
        # Make sure we are checking our correct part of data.
        self.assertIn('health', data_source)

        data_processed = component.persistent
        self.assertEqual(data_source, data_processed)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.game.data.zest_system

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
