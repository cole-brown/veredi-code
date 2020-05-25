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
        if type == DataContext.Type.PLAYER:
            ctx.sub['user'] = 'u/jeff'
            ctx.sub['player'] = 'Sir Jeffsmith'
        elif type == DataContext.Type.MONSTER:
            ctx.sub = ctx.subcontext
            ctx.sub['family'] = 'dragon'
            ctx.sub['monster'] = 'aluminum dragon'
        elif type == DataContext.Type.NPC:
            ctx.sub = ctx.subcontext
            ctx.sub['family'] = 'Townville'
            ctx.sub['player'] = 'Sword Merchant'
        elif type == DataContext.Type.ITEM:
            ctx.sub = ctx.subcontext
            ctx.sub['category'] = 'weapon'
            ctx.sub['item'] = 'Sword, Ok'
        else:
            raise exceptions.LoadError(
                f"No DataContext.Type to ID conversion for: {type}",
                None,
                self.context.merge(context))

        return ctx

    def test_init(self):
        self.assertTrue(self.repo)
        self.assertTrue(self.path)
        self.assertTrue(os.path.isdir(self.path))

    def test_load(self):
        context = self.context_load(DataContext.Type.PLAYER)

        loaded = self.repo.load(context)
        self.assertIsNotNone(loaded)

        # TODO: read file directly, assert contents are same.


#     def test_metadata(self):
#         loaded = None
#         with open(self.path, 'r') as f:
#             loaded = self.codec._load_all(f, self.context())
#
#         self.assertIsNotNone(loaded)
#         self.assertEqual(type(loaded[0]), DocMetadata)
#         metadata = loaded[0].decode()
#
#         self.assertEqual(metadata['doc-type'],
#                          'veredi.unit-test')
#         self.assertEqual(metadata['version'],
#                          datetime.date(2020, 5, 19))
#         self.assertEqual(metadata['source'],
#                          'veredi.unit-test')
#         self.assertEqual(metadata['author'],
#                          'Cole Brown')
#         self.assertEqual(metadata['date'],
#                          datetime.date(2020, 5, 22))
#         self.assertEqual(metadata['system'],
#                          'unit-test')
#         self.assertEqual(metadata['name'],
#                          'veredi.unit-test.component.health')
#         self.assertEqual(metadata['display-name'],
#                          'Veredi Unit-Testing Health Component')
#
