# coding: utf-8

'''
Tests for the RepositorySystem class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest
from io import StringIO

from veredi.base.context import (UnitTestContext,
                                 DataLoadContext,
                                 DataSaveContext,
                                 DataContext)
from .system import RepositorySystem
from ..event import (SerializedEvent, DeserializedEvent,
                     EncodedEvent, DataLoadRequest)
from ...ecs.event import EventManager

from veredi.zest import zest


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Mockups
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_RepoSystem(unittest.TestCase):

    def setUp(self):
        self.path = zest.repository_file_tree()
        self.repo = RepositorySystem(1, repository_base=self.path)
        self.event_manager = EventManager()
        self.events = []

    def tearDown(self):
        self.path = None
        self.repo = None
        self.event_manager = None
        self.events = None

    def sub_deserialized(self):
        self.event_manager.subscribe(DeserializedEvent, self.event_deserialized)

    def set_up_subs(self):
        self.sub_deserialized()
        self.repo.subscribe(self.event_manager)

    def event_deserialized(self, event):
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

    def context_load(self, type):
        ctx = DataLoadContext('unit-testing', type, 'test-campaign')
        path = self.path / 'test-campaign'
        if type == DataContext.Type.PLAYER:
            ctx.sub['user'] = 'u/jeff'
            ctx.sub['player'] = 'Sir Jeffsmith'
            # hand-craft the expected escaped/safed path
            path = path / 'players' / 'u_jeff' / 'sir_jeffsmith.yaml'
        elif type == DataContext.Type.MONSTER:
            ctx.sub['family'] = 'dragon'
            ctx.sub['monster'] = 'aluminum dragon'
            # hand-craft the expected escaped/safed path
            path = path / 'monsters' / 'dragon' / 'aluminum_dragon.yaml'
        elif type == DataContext.Type.NPC:
            ctx.sub['family'] = 'Townville'
            ctx.sub['npc'] = 'Sword Merchant'
            # hand-craft the expected escaped/safed path
            path = path / 'npcs' / 'townville' / 'sword_merchant.yaml'
        elif type == DataContext.Type.ITEM:
            ctx.sub['category'] = 'weapon'
            ctx.sub['item'] = 'Sword, Ok'
            # hand-craft the expected escaped/safed path
            path = path / 'items' / 'weapon' / 'sword__ok.yaml'
        else:
            raise exceptions.LoadError(
                f"No DataContext.Type to ID conversion for: {type}",
                None,
                self.context.merge(context))

        return ctx, path

    def test_init(self):
        self.assertTrue(self.event_manager)
        self.assertTrue(self.repo)
        self.assertTrue(self.repo._repository)

    def test_subscribe(self):
        self.assertFalse(self.event_manager._subscriptions)
        self.repo.subscribe(self.event_manager)
        self.assertTrue(self.event_manager._subscriptions)

        self.assertEqual(self.event_manager,
                         self.repo._event_manager)

    def test_event_load_req(self):
        self.set_up_subs()

        load_ctx, load_path = self.context_load(DataContext.Type.PLAYER)
        load_ctx.sub['user'] = 'u/jeff'
        load_ctx.sub['player'] = 'Sir Jeffsmith'

        event = DataLoadRequest(
            42,
            load_ctx.type,
            load_ctx)
        self.assertFalse(self.events)
        self.make_it_so(event)

        self.assertEqual(len(self.events), 1)
        self.assertIsInstance(self.events[0], DeserializedEvent)

        loaded_stream = self.events[0].data
        self.assertIsNotNone(loaded_stream)

        # read file directly, assert contents are same.
        with load_path.open(mode='r') as file_stream:
            self.assertIsNotNone(file_stream)

            file_data = file_stream.read(None)
            repo_data = loaded_stream.read(None)
            self.assertIsNotNone(file_data)
            self.assertIsNotNone(repo_data)
            self.assertEqual(repo_data, file_data)
