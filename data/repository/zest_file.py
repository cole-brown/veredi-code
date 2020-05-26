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

from veredi.base.context import (VerediContext,
                                 DataContext,
                                 DataLoadContext,
                                 DataSaveContext)
from .file import FileTreeRepository
from .zest_data import zest

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_FileTreeRepo(unittest.TestCase):

    def setUp(self):
        self.path = zest.data_path('file-tree')
        self.repo = FileTreeRepository(self.path)

    def tearDown(self):
        self.repo = None
        self.path = None

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
        self.assertTrue(self.repo)
        self.assertTrue(self.path)
        self.assertTrue(os.path.isdir(self.path))

    def do_load_test(self, load_type):
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
        self.do_load_test(DataContext.Type.PLAYER)

    def test_load_monster(self):
        self.do_load_test(DataContext.Type.MONSTER)

    def test_load_npc(self):
        self.do_load_test(DataContext.Type.NPC)

    def test_load_item(self):
        self.do_load_test(DataContext.Type.ITEM)
