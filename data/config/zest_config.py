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
            self.assertEqual(self.config.get_by_doc(
                config.ConfigDocument.METADATA,
                config.ConfigKey.REC),
                             'veredi.config')
            self.assertEqual(self.config.get_by_doc(
                config.ConfigDocument.METADATA,
                config.ConfigKey.VERSION),
                             date(2020, 5, 26))
            self.assertEqual(self.config.get_by_doc(
                config.ConfigDocument.METADATA,
                config.ConfigKey.AUTHOR),
                             'Cole Brown')

    def test_config_configdata(self):
        self.assertTrue(self.config._config)
        self.assertEqual(self.config.get(config.ConfigKey.DOC),
                         'configuration')
        self.assertEqual(self.config.get_by_doc(
            config.ConfigDocument.CONFIG,
            config.ConfigKey.GAME,
            config.ConfigKey.REPO,
            config.ConfigKey.TYPE),
                         'veredi.repository.file-tree')
        self.assertEqual(self.config.get(config.ConfigKey.GAME,
                                         config.ConfigKey.REPO,
                                         config.ConfigKey.TYPE),
                         'veredi.repository.file-tree')
        self.assertEqual(self.config.get(config.ConfigKey.GAME,
                                         config.ConfigKey.REPO,
                                         config.ConfigKey.DIR),
                         'test-target-repo/file-tree')
        self.assertEqual(self.config.get(config.ConfigKey.GAME,
                                         config.ConfigKey.CODEC),
                         'veredi.codec.yaml')

    def test_config_make_repo(self):
        debug = False

        self.assertTrue(self.config._config)

        with log.LoggingManager.on_or_off(debug):
            repo = self.config.make(None,
                                    config.ConfigKey.GAME,
                                    config.ConfigKey.REPO,
                                    config.ConfigKey.TYPE)

        self.assertTrue(repo)
        self.assertIsInstance(repo, FileTreeRepository)



# --------------------------------Unit Testing----------------------------------
# --                      Main Command Line Entry Point                       --
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    # log.set_level(log.Level.DEBUG)
    unittest.main()
