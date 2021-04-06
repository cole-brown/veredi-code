# coding: utf-8

'''
Tests for the DataManager class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional


import enum
from io import StringIO


from veredi.zest.base.ecs                  import ZestEcs
from veredi.zest                           import zload
from veredi.base                           import paths
from veredi.base.context                   import UnitTestContext
from veredi.logs                           import log

from veredi.data.context                   import (DataAction,
                                                   DataLoadContext,
                                                   # DataSaveContext,
                                                   # DataGameContext)
                                                   )
from veredi.data.records                   import (DataType,
                                                   # DocType,
                                                   Definition,
                                                   Saved)

from ..ecs.base.identity                   import ComponentId
from .component                            import DataComponent
from veredi.rules.d20.pf2.game             import PF2Rank
from veredi.rules.d20.pf2.health.component import HealthComponent


# For registering
from veredi.data.repository.file.tree import FileTreeRepository


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

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    @enum.unique
    class TestLoad(enum.Enum):
        '''
        Enum for context_load().
        '''

        PLAYER  = [PF2Rank.Phylum.PLAYER,  ['u/jeff', 'Sir Jeffsmith']]
        MONSTER = [PF2Rank.Phylum.MONSTER, ['dragon', 'aluminum dragon']]
        NPC     = [PF2Rank.Phylum.NPC,     ['Townville', 'Sword Merchant']]
        ITEM    = [PF2Rank.Phylum.ITEM,    ['weapon', 'Sword, Ok']]

    # -------------------------------------------------------------------------
    # Set-Up
    # -------------------------------------------------------------------------

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
         self.context, _) = zload.set_up_ecs(__file__,
                                             self,
                                             '_set_up_ecs',
                                             self.debugging,
                                             debug_flags=self.debug_flags,
                                             require_engine=False,
                                             configuration=self.config)

    def set_all_events_external(self, all_events_external: bool) -> None:
        self._all_events_external = all_events_external
        self.manager.data._ut_all_events_external = self._all_events_external

    # -------------------------------------------------------------------------
    # Tear-Down
    # -------------------------------------------------------------------------

    def tear_down(self):
        super().tear_down()
        self._tear_down_ecs()
        self.path   = None

    def _tear_down_ecs(self):
        '''
        Calls zload.tear_down_ecs to have meeting/managers run any tear-down
        they happen to have.
        '''
        zload.tear_down_ecs(__file__,
                            self,
                            '_tear_down_ecs',
                            self.debugging,
                            self.manager,
                            engine=None)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def context_load(
            self,
            load: Optional['BaseTest_DataManager.TestLoad'] = None
    ) -> DataLoadContext:
        '''
        Create a DataLoadContext given `taxonomy` OR `by_enum`.
        '''
        # ------------------------------
        # Get values from `load` enum.
        # ------------------------------
        phylum = load.value[0]
        taxonomy = load.value[1]

        # ------------------------------
        # Create the context.
        # ------------------------------
        context = None
        with log.LoggingManager.on_or_off(self.debugging):
            taxon = self.manager.data.taxon(DataType.SAVED, phylum, *taxonomy)
            context = self.manager.data.context(self.dotted,
                                                DataAction.LOAD,
                                                taxon)

        return context

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def sub_events(self):
        self.manager.event.subscribe(_LoadedEvent,
                                     self._eventsub_generic_append)

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_init(self):
        self.assertTrue(self.manager.event)

        # ---
        # DataManager Asserts
        # ---
        data = self.manager.data
        self.assertTrue(data)
        self.assertTrue(data._repository)

        self.assertTrue(data._game)
        self.assertTrue(data._game.definition)
        self.assertIsInstance(data._game.definition, Definition)
        self.assertTrue(data._game.saved)
        self.assertIsInstance(data._game.saved, Saved)

    def test_subscribe(self):
        self.assertFalse(self.manager.event._subscriptions)
        self.manager.data.subscribe(self.manager.event)
        self.assertTrue(self.manager.event._subscriptions)

    def test_load(self):
        self.set_all_events_external(True)
        self.set_up_events(clear_self=True, clear_manager=True)

        # Create our load request.
        load_ctx = self.context_load(self.TestLoad.PLAYER)
        # Any old id and type...
        event = DataLoadRequest(
            42,
            43,
            load_ctx)
        self.assertFalse(self.events)

        # Shouldn't have repo context yet - haven't given it to repo yet.
        repo_ctx = load_ctx.repo_data
        self.assertFalse(repo_ctx)

        # Trigger the load...
        self.trigger_events(event)

        self.assertEqual(len(self.events), 1)
        self.assertIsInstance(self.events[0], _LoadedEvent)

        # And now the repo context should be there.
        repo_ctx = load_ctx.repo_data
        self.assertTrue(repo_ctx)
        self.assertIn('meta', repo_ctx)
        self.assertTrue(repo_ctx['meta'])
        self.assertIn('path', repo_ctx['meta'])
        self.assertTrue(repo_ctx['meta']['path'])
        self.assertIn('root', repo_ctx['meta']['path'])
        self.assertTrue(repo_ctx['meta']['path']['root'])
        # ...and it should have the load path it used in it.
        self.assertIn('paths', repo_ctx)
        self.assertTrue(repo_ctx['paths'])
        self.assertIsInstance(repo_ctx['paths'], list)
        self.assertEqual(len(repo_ctx['paths']), 1)
        load_path = paths.cast(repo_ctx['paths'][0])
        self.assertTrue(load_path)
        self.assertTrue(load_path.exists())

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

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def sub_events(self):
        self.manager.event.subscribe(_DeserializedEvent,
                                     self._eventsub_generic_append)

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

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
                    __file__,
                    self,
                    'test_deserialize',
                    data={
                        'unit-testing': "string 'test-data' in zest_manager.py"
                    }),
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
            self.assertIsInstance(received, _DeserializedEvent)
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

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def sub_events(self):
        self.manager.event.subscribe(DataLoadedEvent,
                                     self._eventsub_generic_append)

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

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
            __file__,
            self,
            'test_event_loaded',
            data={'unit-testing': "Manually created _DeserializedEvent."})
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

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def sub_events(self):
        self.manager.event.subscribe(DataLoadedEvent,
                                     self._eventsub_generic_append)

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_init(self):
        self.assertTrue(self.manager.event)
        self.assertTrue(self.manager.data)

    def test_load(self):
        self.set_up_events(clear_self=True, clear_manager=True)

        # Make a DataLoadRequest for repo to load something.
        load_ctx = self.context_load(self.TestLoad.PLAYER)
        # load_ctx.sub['user'] = 'u/jeff'
        # load_ctx.sub['player'] = 'Sir Jeffsmith'

        # Any old id and type...
        event = DataLoadRequest(
            42,
            43,
            load_ctx)
        self.assertFalse(self.events)
        # self._debug_on(DebugFlag.EVENTS,
        #                set_this_test=True,
        #                set_all_systems=True,
        #                set_all_managers=True,
        #                set_engine=False)  # No engine in this test suite.
        self.trigger_events(event)
        # self._debug_off(DebugFlag.EVENTS,
        #                 set_this_test=True,
        #                 set_all_systems=True,
        #                 set_all_managers=True,
        #                 set_engine=False)  # No engine in this test suite.

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
#   doc-veredi run game/data/zest_manager.py

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
