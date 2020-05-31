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

from . import config
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
        self.path = zpath.config('test-target.yaml')
        self.config = zmake.config(zpath.TestType.UNIT, self.path, None, None)

    def tearDown(self):
        self.data_root = None
        self.name_user = None
        self.name_player = None
        self.name_campaign = None
        self.data = None

    def test_init(self):
        self.assertIsNotNone(self.path)
        self.assertIsNotNone(self.config)

    def test_config_metadata(self):
        self.assertTrue(self.config._config)
        with log.LoggingManager.full_blast():
            self.assertEqual(self.config.get(config.ConfigDocuments.METADATA,
                                             config.ConfigKeys.REC),
                             'veredi.config')
        self.assertEqual(self.config.get(config.ConfigDocuments.METADATA,
                                         config.ConfigKeys.VERSION),
                         date(2020, 5, 26))
        self.assertEqual(self.config.get(config.ConfigDocuments.METADATA,
                                         config.ConfigKeys.AUTHOR),
                         'Cole Brown')

    def test_config_configdata(self):
        self.assertTrue(self.config._config)
        self.assertEqual(self.config.get(config.ConfigDocuments.CONFIG,
                                         config.ConfigKeys.DOC),
                         'configuration')
        self.assertEqual(self.config.get(config.ConfigDocuments.CONFIG,
                                         config.ConfigKeys.GAME,
                                         config.ConfigKeys.REPO,
                                         config.ConfigKeys.TYPE),
                         'veredi.repository.file-tree')
        self.assertEqual(self.config.get(config.ConfigDocuments.CONFIG,
                                         config.ConfigKeys.GAME,
                                         config.ConfigKeys.REPO,
                                         config.ConfigKeys.DIR),
                         'test-target-repo/file-tree')
        self.assertEqual(self.config.get(config.ConfigDocuments.CONFIG,
                                         config.ConfigKeys.GAME,
                                         config.ConfigKeys.CODEC),
                         'veredi.codec.yaml')

    def test_config_make_repo(self):

        self.assertTrue(self.config._config)

        with log.LoggingManager.ignored():
            repo = self.config.make(None,
                                    config.ConfigKeys.GAME,
                                    config.ConfigKeys.REPO,
                                    config.ConfigKeys.TYPE)

        self.assertTrue(repo)
        self.assertIsInstance(repo, FileTreeRepository)



# --------------------------------Unit Testing----------------------------------
# --                      Main Command Line Entry Point                       --
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    # log.set_level(log.Level.DEBUG)
    unittest.main()
