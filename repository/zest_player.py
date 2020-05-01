# coding: utf-8

'''
Unit tests for:
  veredi/roll/d20/evaluator.py
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
import unittest
import os

# Veredi
from . import player

# Our Stuff
from veredi.zester import test_data


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------Player Repositories------------------------------
# --                 Test that we can read and write good...                  --
# ----------------------...and do other things good too.------------------------

# -----------------------------------------------------------------------------
# Player, File, JSON
# -----------------------------------------------------------------------------

class Test_PlayerRepo_FileJson(unittest.TestCase):

    def setUp(self):
        self.options = player.PathNameOption.HUMAN_SAFE
        self.data_root = test_data.abs_path('data', 'repository',
                                            'file', 'json', 'human')

        self.name_user = "us1!{er"
        self.name_player = "jeff"
        self.name_campaign = "some-forgotten-campaign"

    def tearDown(self):
        self.data_root = None
        self.name_user = None
        self.name_player = None
        self.name_campaign = None

    # --------------------------------------------------------------------------
    # Simple Cases
    # --------------------------------------------------------------------------

    def test_load(self):
        repo = player.PlayerRepository_FileJson(self.data_root, self.options)
        data = repo.load_by_name(self.name_user,
                                 self.name_campaign,
                                 self.name_player)

        # Did we get anything?
        self.assertTrue(data)

        # Does it contain the data we think it should?
        self.assertEqual(self.name_user,     data['user']['name'])
        self.assertEqual(self.name_campaign, data['campaign']['name'])
        self.assertEqual(self.name_player,   data['player']['name'])


# # -----------------------------------------------------------------------------
# # Player, File, YAML
# # -----------------------------------------------------------------------------
#
# class Test_PlayerRepo_FileYaml(unittest.TestCase):
#
#     def setUp(self):
#         self.options = player.PathNameOption.HUMAN_SAFE
#         self.data_root = test_data.abs_path('data', 'repository',
#                                             'file', 'yaml', 'human')
#
#         self.name_user = "us1!{er"
#         self.name_player = "jeff"
#         self.name_campaign = "some-forgotten-campaign"
#
#     def tearDown(self):
#         self.data_root = None
#         self.name_user = None
#         self.name_player = None
#         self.name_campaign = None
#
#     # --------------------------------------------------------------------------
#     # Simple Cases
#     # --------------------------------------------------------------------------
#
#     def test_load(self):
#         repo = player.PlayerRepository_FileYaml(self.data_root, self.options)
#         data = repo.load_by_name(self.name_user,
#                                  self.name_campaign,
#                                  self.name_player)
#
#         # Did we get anything?
#         self.assertTrue(data)
#
#         # Does it contain the data we think it should?
#         self.assertEqual(self.name_user,     data['user']['name'])
#         self.assertEqual(self.name_campaign, data['campaign']['name'])
#         self.assertEqual(self.name_player,   data['player']['name'])


# --------------------------------Unit Testing----------------------------------
# --                      Main Command Line Entry Point                       --
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main()
