# coding: utf-8

'''
Tests for the RepositorySystem class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.zest.base.system import ZestSystem
from veredi.zest             import zmake, zpath
from veredi.data.context     import (DataLoadContext,
                                     DataSaveContext,
                                     DataGameContext)
from .system                 import RepositorySystem
from ..event                 import (_SavedEvent, _LoadedEvent,
                                     _SerializedEvent, DataLoadRequest)
from ...ecs.event            import EventManager
from veredi.data.exceptions  import LoadError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Mockups
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_RepoSystem(ZestSystem):

    def set_up(self):
        super().set_up()
        self.init_self_system(RepositorySystem)
        # self.system = RepositorySystem(None, 1, self.manager)
        self.path = self.system._repository.root

    def _set_up_ecs(self):
        '''
        Overriding this to get the config we want and roll on into the manager
        that ZestEcs._set_up_ecs() normally makes.
        '''
        self.config = zmake.config(
            repo_dotted='veredi.repository.file-tree',
            repo_path=zpath.repository_file_tree(),
            repo_clean='veredi.sanitize.human.path-safe'
        )

        self.manager = zmake.meeting(
            configuration=self.config,
            event_manager=EventManager(self.config, self.debug_flags))

    def tear_down(self):
        super().tear_down()
        self.config = None
        self.path   = None

    def sub_events(self):
        self.manager.event.subscribe(_LoadedEvent,
                                     self.event_deserialized)

    def set_up_events(self):
        self._sub_events_systems()
        self.sub_events()

    def event_deserialized(self, event):
        self.events.append(event)

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

    def test_init(self):
        self.assertTrue(self.manager.event)
        self.assertTrue(self.system)
        self.assertTrue(self.system._repository)

    def test_subscribe(self):
        self.assertFalse(self.manager.event._subscriptions)
        self.system.subscribe(self.manager.event)
        self.assertTrue(self.manager.event._subscriptions)

        self.assertEqual(self.manager.event,
                         self.system._manager.event)

    def test_event_load_req(self):
        self.set_up_events()
        self.clear_events(clear_manager=True)

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


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.game.data.repository.zest_system

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
