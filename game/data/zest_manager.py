# coding: utf-8

'''
Tests for the DataManager class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from io import StringIO


from veredi.zest.base.ecs               import ZestEcs
from veredi.zest                           import zload
from veredi.base.context                   import UnitTestContext
from veredi.logger                         import log

from veredi.data.context                   import (DataLoadContext,
                                                   # DataSaveContext,
                                                   DataGameContext)
from veredi.data.exceptions import LoadError

from ..ecs.base.identity                   import ComponentId
from .component                            import DataComponent
from veredi.rules.d20.pf2.health.component import HealthComponent

from .manager                              import DataManager

# ---
# Data Events
# ---
from .event import (
    # Should be all of them, but call them each out.

    # Requests from Game
    DataLoadRequest,
    DataSaveRequest,

    # Final result
    DataLoadedEvent,
    DataSavedEvent,

    # Interim events for Serdes
    _DeserializedEvent,
    _SerializedEvent,

    # Interim events for Repository
    _LoadedEvent,
    _SavedEvent
)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

test_data_serdes = '''
--- !component

meta:
  registry: veredi.rules.d20.pf2.health.component

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

    hit-points: 21

  unconscious:
    hit-points: 0

  death:
    hit-points: 0

  resistance:
'''
'''
Serialized YAML test data for serdes tests.
'''

test_data_actual = [
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
'''
Similar to test_data_serdes, but in python form.
'''


# -----------------------------------------------------------------------------
# Base Test Class
# -----------------------------------------------------------------------------

class BaseTest_DataManager(ZestEcs):
    '''
    Test our DataManager with HealthComponent class against some health data.
    '''

    # ------------------------------
    # Set-Up & Tear-Down
    # ------------------------------

    def set_up(self):
        super().set_up()
        self._all_events_external = False
        self.path = self.manager.data._repository.root

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
                                         require_engine=False)

    def tear_down(self):
        super().tear_down()
        self.path   = None

    def set_all_events_external(self, all_events_external: bool) -> None:
        self._all_events_external = all_events_external
        self.manager.data._ut_all_events_external = self._all_events_external

    # ------------------------------
    # Helpers
    # ------------------------------

    def context_load(self, type):
        ctx = DataLoadContext('unit-testing',
                              type,
                              'test-campaign')
        path = self.path / 'game' / 'test-campaign'

        if type == DataGameContext.DataType.PLAYER:
            ctx.sub['user'] = 'u/jeff'
            ctx.sub['player'] = 'Sir Jeffsmith'
            # hand-craft the expected escaped/safed path
            path = path / 'players' / 'u_jeff' / 'sir_jeffsmith.yaml'

        elif type == DataGameContext.DataType.MONSTER:
            ctx.sub['family'] = 'dragon'
            ctx.sub['monster'] = 'aluminum dragon'
            # hand-craft the expected escaped/safed path
            path = path / 'monsters' / 'dragon' / 'aluminum_dragon.yaml'

        elif type == DataGameContext.DataType.NPC:
            ctx.sub['family'] = 'Townville'
            ctx.sub['npc'] = 'Sword Merchant'
            # hand-craft the expected escaped/safed path
            path = path / 'npcs' / 'townville' / 'sword_merchant.yaml'

        elif type == DataGameContext.DataType.ITEM:
            ctx.sub['category'] = 'weapon'
            ctx.sub['item'] = 'Sword, Ok'
            # hand-craft the expected escaped/safed path
            path = path / 'items' / 'weapon' / 'sword__ok.yaml'

        else:
            raise LoadError(
                f"No DataGameContext.DataType to ID conversion for: {type}",
                None,
                ctx)

        return ctx, path

    # ------------------------------
    # Events
    # ------------------------------

    def _sub_data_loaded(self) -> None:
        '''
        Automatically called in set_up_events() currently, but we don't want
        any data events automatically subscribed to. So change to a no-op.
        '''
        pass

    def sub_events(self):
        raise NotImplementedError(f"{self.__class__.__name__} must "
                                  "implement sub_events().")


# -----------------------------------------------------------------------------
# Repo Test Class
# -----------------------------------------------------------------------------

class Test_DataManager_Repo(BaseTest_DataManager):
    '''
    Test our DataManager with HealthComponent class against some health data.
    '''

    # ------------------------------
    # Events
    # ------------------------------

    def sub_events(self):
        self.manager.event.subscribe(_LoadedEvent,
                                     self._eventsub_generic_append)

    # ------------------------------
    # Tests
    # ------------------------------

    def test_init(self):
        self.assertTrue(self.manager.event)
        self.assertTrue(self.manager.data)
        self.assertTrue(self.manager.data._repository)

    def test_subscribe(self):
        self.assertFalse(self.manager.event._subscriptions)
        self.manager.data.subscribe(self.manager.event)
        self.assertTrue(self.manager.event._subscriptions)

    def test_load(self):
        self.set_all_events_external(True)
        self.set_up_events(clear_self=True, clear_manager=True)

        load_ctx, load_path = self.context_load(
            DataGameContext.DataType.PLAYER)
        load_ctx.sub['user'] = 'u/jeff'
        load_ctx.sub['player'] = 'Sir Jeffsmith'

        event = DataLoadRequest(
            42,
            load_ctx.type,
            load_ctx)
        self.assertFalse(self.events)
        self.trigger_events(event)

        self.assertEqual(len(self.events), 1)
        self.assertIsInstance(self.events[0], _LoadedEvent)

        # read file directly, assert contents are same.
        with load_path.open(mode='r') as file_stream:
            self.assertIsNotNone(file_stream)

            file_data = file_stream.read(None)
            repo_data = self.events[0].data(seek_to=0)
            self.assertIsNotNone(file_data)
            self.assertIsNotNone(repo_data)

            self.assertEqual(repo_data, file_data)


# -----------------------------------------------------------------------------
# Serdes Test Class
# -----------------------------------------------------------------------------

class BaseTest_DataManager_Serdes(BaseTest_DataManager):
    '''
    Test our DataManager with HealthComponent class against some health data.
    '''

    # ------------------------------
    # Events
    # ------------------------------

    def sub_events(self):
        self.manager.event.subscribe(_DeserializedEvent,
                                     self._eventsub_generic_append)

    # ------------------------------
    # Tests
    # ------------------------------

    def test_init(self):
        self.assertTrue(self.manager.data)
        self.assertTrue(self.manager.event)

    def test_subscribe(self):
        self.assertFalse(self.manager.event._subscriptions)
        self.set_up_events(clear_self=True, clear_manager=True)
        self.assertTrue(self.manager.event._subscriptions)

    def test_deserialize(self):
        self.set_all_events_external(True)
        self.set_up_events(clear_self=True, clear_manager=True)

        with StringIO(test_data_serdes) as stream:
            self.assertTrue(stream)

            event = _LoadedEvent(
                42,
                0xDEADBEEF,
                UnitTestContext(
                    self.__class__.__name__,
                    'test_event_load',
                    {'unit-testing': "string 'test-data' in zest_manager.py"}),
                data=stream)
            self.assertTrue(event)
            self.manager.event.notify(event, True)
            # SerdesManager will reply with its own event (not immediately
            # published?)... publish it for it.
            self.manager.event.publish()
            self.assertTrue(self.events)

            # Test what we got back.
            received = self.events[0]
            self.assertIsNotNone(received)
            self.assertEqual(type(received), _DeserializedEvent)
            self.assertIsInstance(received.data, list)
            self.assertEqual(len(received.data), 1)
            component = received.data[0]

            meta = component.get('meta', {})
            self.assertTrue(meta)
            self.assertEqual(meta['registry'],
                             'veredi.rules.d20.pf2.health.component')

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


# -----------------------------------------------------------------------------
# DataManager Test Class
# -----------------------------------------------------------------------------

class Test_DataManager_ToGame(BaseTest_DataManager):
    '''
    Test our DataManager with HealthComponent class against some health data.
    '''

    # ------------------------------
    # Events
    # ------------------------------

    def sub_events(self):
        self.manager.event.subscribe(DataLoadedEvent,
                                     self._eventsub_generic_append)

    # ------------------------------
    # Tests
    # ------------------------------

    def test_init(self):
        self.assertTrue(self.manager.event)
        self.assertTrue(self.manager.component)
        self.assertTrue(self.manager.data)

    def test_event_loaded(self):
        '''
        _DeserializedEvent -> DataLoadedEvent
        '''
        self.set_all_events_external(True)
        self.set_up_events(clear_self=True, clear_manager=True)

        ctx = UnitTestContext(
            self.__class__.__name__,
            'test_event_loaded',
            {'unit-testing': "Manually created _DeserializedEvent."})
        ctx.pull(self.context)
        decode_event = _DeserializedEvent(
            42,
            0xDEADBEEF,
            ctx,
            data=test_data_actual)

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

        data_source = test_data_actual[1]
        # Make sure we are checking our correct part of data.
        self.assertIn('health', data_source)

        data_processed = component.persistent
        self.assertEqual(data_source, data_processed)


# -----------------------------------------------------------------------------
# Repo Test Class
# -----------------------------------------------------------------------------

class Test_DataManager_Actual(BaseTest_DataManager):
    '''
    Test our DataManager with HealthComponent class against some health data.
    '''

    # ------------------------------
    # Events
    # ------------------------------

    def sub_events(self):
        self.manager.event.subscribe(DataLoadedEvent,
                                     self._eventsub_generic_append)

    # ------------------------------
    # Tests
    # ------------------------------

    def test_init(self):
        self.assertTrue(self.manager.event)
        self.assertTrue(self.manager.data)

    def test_load(self):
        self.set_up_events(clear_self=True, clear_manager=True)

        # Make a DataLoadRequest for repo to load something.
        load_ctx, load_path = self.context_load(
            DataGameContext.DataType.PLAYER)
        load_ctx.sub['user'] = 'u/jeff'
        load_ctx.sub['player'] = 'Sir Jeffsmith'

        event = DataLoadRequest(
            42,
            load_ctx.type,
            load_ctx)
        self.assertFalse(self.events)
        self.trigger_events(event)

        # Expect a DataLoadedEvent with output from deserializing.
        self.assertEqual(len(self.events), 1)
        self.assertIsInstance(self.events[0], DataLoadedEvent)

        event = self.events[0]
        cid = event.component_id
        self.assertNotEqual(cid, ComponentId.INVALID)
        component = self.manager.component.get(cid)
        self.assertIsInstance(component, DataComponent)

        self.assertIsInstance(component, HealthComponent)

        # Vague checks for sanity of expected vs actual.
        data_expected = test_data_actual[1]
        self.assertIn('health', data_expected)
        data_actual = component.persistent
        self.assertIn('health', data_actual)

        # A single more specific check.
        health_expected = data_expected['health']
        health_actual = data_actual['health']
        self.assertEqual(health_expected['current']['permanent'],
                         health_actual['current']['permanent'])


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.game.data.zest_manager

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
