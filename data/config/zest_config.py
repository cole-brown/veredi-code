# coding: utf-8

'''
Unit tests for:
  veredi/entity/d20/player.py
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
import unittest
import os

# Veredi
from veredi.logger import log
from ..repository.manager import RepositoryManager
from ..repository._old_stuff import player
from . import config


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Stuff for a Player Entity
# -----------------------------------------------------------------------------

# class Test_Configuration(unittest.TestCase):
#
#     def setUp(self):
#         self.data_root = test_data.abs_path('data', 'repository',
#                                             'file', 'yaml',
#                                             'test.entity.player.yaml')
#         self.name_user = "us1!{er"
#         self.name_player = "Jeff the Girl"
#         self.name_campaign = "some-forgotten-campaign"
#
#         self.repo = player_repo.PlayerFileTree(self.data_root)
#         self.data = self.repo._load_for_unit_tests(self.data_root,
#                                                    user=self.name_user,
#                                                    campaign=self.name_campaign,
#                                                    player=self.name_player,
#                                                    repository='unit test hacks')
#
#     def tearDown(self):
#         self.data_root = None
#         self.name_user = None
#         self.name_player = None
#         self.name_campaign = None
#         self.data = None
#
#     # --------------------------------------------------------------------------
#     # Simple Cases
#     # --------------------------------------------------------------------------
#
#     def test_config(self):
#         conf = config.Configuration()
#         self.assertTrue(conf)
#         self.assertIsInstance(conf.repository, RepositoryManager)
#         self.assertIsInstance(conf.repository.player, player.PlayerRepository)
#         self.assertIsInstance(conf.repository.player, player.PlayerFileTree)
#
#         self.assertEqual(conf.repository.player.root,
#                          os.path.abspath("test/owner/repository/player/"))



# --------------------------------Unit Testing----------------------------------
# --                      Main Command Line Entry Point                       --
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    # log.set_level(log.Level.DEBUG)
    unittest.main()
