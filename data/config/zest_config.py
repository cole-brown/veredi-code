# coding: utf-8

'''
Unit tests for:
  veredi/entity/d20/player.py
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from datetime import date

from veredi.zest.base.unit       import ZestBase
from veredi.zest                 import zpath, zmake
from veredi.logger               import log

from .                           import hierarchy
from veredi.data.repository.file import FileTreeRepository


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Stuff for a Player Entity
# -----------------------------------------------------------------------------

class Test_Configuration(ZestBase):

    def set_up(self):
        self.path = zpath.config('test-target.yaml')
        self.config = zmake.config(zpath.TestType.UNIT,
                                   config_path=self.path,
                                   config_repo=None,
                                   config_codec=None)

    def tearDown(self):
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
                'repository',
                'type'),
            'veredi.repository.file-tree')
        self.assertEqual(self.config.get('data',
                                         'repository',
                                         'type'),
                         'veredi.repository.file-tree')
        self.assertEqual(self.config.get_data('repository',
                                              'type'),
                         'veredi.repository.file-tree')
        self.assertEqual(self.config.get('data',
                                         'repository',
                                         'directory'),
                         'test-target-repo/file-tree')
        self.assertEqual(self.config.get_data('repository',
                                              'directory'),
                         'test-target-repo/file-tree')
        self.assertEqual(self.config.get('data',
                                         'codec'),
                         'veredi.codec.yaml')
        self.assertEqual(self.config.get_data('codec'),
                         'veredi.codec.yaml')

    def test_config_make_repo(self):
        debugging = False

        self.assertTrue(self.config._config)

        with log.LoggingManager.on_or_off(debugging):
            repo = self.config.make(None,
                                    'data',
                                    'repository',
                                    'type')

        self.assertTrue(repo)
        self.assertIsInstance(repo, FileTreeRepository)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.data.config.zest_config

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
