# coding: utf-8

'''
Unit tests for:
  veredi/entity/d20/player.py
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest
from datetime import date

from veredi.logger import log

from . import hierarchy

from veredi.data.repository.file import FileTreeRepository

from veredi.zest import zpath, zmake


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Stuff for a Player Entity
# -----------------------------------------------------------------------------

class Test_Configuration(unittest.TestCase):

    def setUp(self):
        self.debug = False
        self.path = zpath.config('test-target.yaml')
        self.config = zmake.config(zpath.TestType.UNIT, self.path, None, None)

    def tearDown(self):
        self.debug = False
        self.path = None
        self.config = None

    def test_init(self):
        self.assertIsNotNone(self.path)
        self.assertIsNotNone(self.config)

    def test_config_metadata(self):
        self.assertTrue(self.config._config)
        with log.LoggingManager.full_blast():
            self.assertEqual(
                self.config.get_by_doc(
                    hierarchy.Document.METADATA,
                    'record-type'),
                'veredi.config')
            self.assertEqual(
                self.config.get_by_doc(
                    hierarchy.Document.METADATA,
                    'version'),
                date(2020, 5, 26))
            self.assertEqual(
                self.config.get_by_doc(
                    hierarchy.Document.METADATA,
                    'author'),
                'Cole Brown')

    def test_config_configdata(self):
        self.assertTrue(self.config._config)
        self.assertEqual(self.config.get('doc-type'),
                         'configuration')
        self.assertEqual(
            self.config.get_by_doc(
                hierarchy.Document.CONFIG,
                'data',
                'game',
                'repository',
                'type'),
            'veredi.repository.file-tree')
        self.assertEqual(self.config.get('data',
                                         'game',
                                         'repository',
                                         'type'),
                         'veredi.repository.file-tree')
        self.assertEqual(self.config.get_data('game',
                                              'repository',
                                              'type'),
                         'veredi.repository.file-tree')
        self.assertEqual(self.config.get('data',
                                         'game',
                                         'repository',
                                         'directory'),
                         'test-target-repo/file-tree')
        self.assertEqual(self.config.get_data('game',
                                              'repository',
                                              'directory'),
                         'test-target-repo/file-tree')
        self.assertEqual(self.config.get('data',
                                         'game',
                                         'codec'),
                         'veredi.codec.yaml')
        self.assertEqual(self.config.get_data('game',
                                              'codec'),
                         'veredi.codec.yaml')

    def test_config_make_repo(self):
        debug = False

        self.assertTrue(self.config._config)

        with log.LoggingManager.on_or_off(debug):
            repo = self.config.make(None,
                                    'data',
                                    'game',
                                    'repository',
                                    'type')

        self.assertTrue(repo)
        self.assertIsInstance(repo, FileTreeRepository)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    # log.set_level(log.Level.DEBUG)
    unittest.main()
