# coding: utf-8

'''
Tests for the FileTreeRepository.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest
import os
import pathlib

from veredi.logger import log

from veredi.data.config.config import ConfigDocument, ConfigKey
from veredi.data.config.context import ConfigContext
from veredi.data.context import (DataGameContext,
                                 DataLoadContext,
                                 DataSaveContext)
from .file import FileTreeRepository, to_human_readable
from veredi.zest import zpath
from veredi.zest import zmake

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_FileTreeRepo(unittest.TestCase):

    def setUp(self):
        self.debug = False
        self.path = zpath.repository_file_tree()
        self.config = zmake.config()
        self.context = ConfigContext(self.path,
                                     self.config)

        # Finish set-up. Inject stuff repo needs to init proper.
        self.context.ut_inject(path=self.path)
        self.config.ut_inject(self.path,
                              ConfigDocument.CONFIG,
                              ConfigKey.GAME,
                              ConfigKey.REPO,
                              ConfigKey.DIR)

        # §-TODO-§ [2020-06-01]: Register these, have config read dotted and get
        # from registry.
        self.config.ut_inject('veredi.sanitize.human.path-safe',
                              ConfigDocument.CONFIG,
                              ConfigKey.GAME,
                              ConfigKey.REPO,
                              ConfigKey.SANITIZE)

        # Should be enough info to make our repo now.
        self.repo = FileTreeRepository(self.context)

    def tearDown(self):
        self.debug = False
        self.repo = None
        self.path = None

    def context_load(self, type):
        ctx = None
        with log.LoggingManager.on_or_off(self.debug):
            ctx = self.context.spawn(DataLoadContext,
                                     'unit-testing', None,
                                     type,
                                     'test-campaign')
        path = self.path / 'test-campaign'
        if type == DataGameContext.Type.PLAYER:
            ctx.sub['user'] = 'u/jeff'
            ctx.sub['player'] = 'Sir Jeffsmith'
            # hand-craft the expected escaped/safed path
            path = path / 'players' / 'u_jeff' / 'sir_jeffsmith.yaml'
        elif type == DataGameContext.Type.MONSTER:
            ctx.sub['family'] = 'dragon'
            ctx.sub['monster'] = 'aluminum dragon'
            # hand-craft the expected escaped/safed path
            path = path / 'monsters' / 'dragon' / 'aluminum_dragon.yaml'
        elif type == DataGameContext.Type.NPC:
            ctx.sub['family'] = 'Townville'
            ctx.sub['npc'] = 'Sword Merchant'
            # hand-craft the expected escaped/safed path
            path = path / 'npcs' / 'townville' / 'sword_merchant.yaml'
        elif type == DataGameContext.Type.ITEM:
            ctx.sub['category'] = 'weapon'
            ctx.sub['item'] = 'Sword, Ok'
            # hand-craft the expected escaped/safed path
            path = path / 'items' / 'weapon' / 'sword__ok.yaml'
        else:
            raise exceptions.LoadError(
                f"No DataGameContext.Type to ID conversion for: {type}",
                None,
                self.context.pull(context))

        return ctx, path

    def test_init(self):
        self.assertTrue(self.repo)
        self.assertTrue(self.path)
        self.assertTrue(os.path.isdir(self.path))

    def do_load_test(self, load_type):
        with log.LoggingManager.on_or_off(self.debug):
            context, path = self.context_load(load_type)
        self.assertTrue(path.parent.exists())

        loaded_stream = self.repo.load(context)
        self.assertIsNotNone(loaded_stream)

        # read file directly, assert contents are same.
        with path.open(mode='r') as file_stream:
            self.assertIsNotNone(file_stream)

            file_data = file_stream.read(None)
            repo_data = loaded_stream.read(None)
            self.assertIsNotNone(file_data)
            self.assertIsNotNone(repo_data)
            self.assertEqual(repo_data, file_data)

    def test_load_player(self):
        self.do_load_test(DataGameContext.Type.PLAYER)

    def test_load_monster(self):
        self.do_load_test(DataGameContext.Type.MONSTER)

    def test_load_npc(self):
        self.do_load_test(DataGameContext.Type.NPC)

    def test_load_item(self):
        self.do_load_test(DataGameContext.Type.ITEM)
