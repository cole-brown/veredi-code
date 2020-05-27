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
from ..codec.base import CodecKeys, CodecDocuments

from veredi.zest import zest

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Stuff for a Player Entity
# -----------------------------------------------------------------------------

class Test_Configuration(unittest.TestCase):

    def setUp(self):
        self.path = zest.config('default.yaml')
        self.config = config.Configuration(self.path)

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
        self.assertEqual(self.config.get(CodecDocuments.METADATA,
                                         'record-type'),
                         'veredi.config')
        self.assertEqual(self.config.get(CodecDocuments.METADATA,
                                         'version'),
                         date(2020, 5, 26))
        self.assertEqual(self.config.get(CodecDocuments.METADATA,
                                         'author'),
                         'Cole Brown')

    def test_config_configdata(self):
        self.assertTrue(self.config._config)
        self.assertEqual(self.config.get(CodecDocuments.CONFIG,
                                         'doc-type'),
                         'configuration')
        self.assertEqual(self.config.get(CodecDocuments.CONFIG,
                                         'game', 'repository'),
                         'veredi.repository.file-tree')
        self.assertEqual(self.config.get(CodecDocuments.CONFIG,
                                         'game', 'codec'),
                         'veredi.codec.yaml')
        self.assertEqual(self.config.get(CodecDocuments.CONFIG,
                                         'game', 'directory'),
                         'test/game/repository/file-tree')



# --------------------------------Unit Testing----------------------------------
# --                      Main Command Line Entry Point                       --
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    # log.set_level(log.Level.DEBUG)
    unittest.main()
