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
from . import player
from veredi.repository import player as player_repo

# Our Stuff
from veredi.zester import test_data


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Stuff for a Player Entity
# -----------------------------------------------------------------------------

class Test_PlayerEntity(unittest.TestCase):

    def setUp(self):
        self.data_root = test_data.abs_path('data', 'repository',
                                            'file', 'yaml',
                                            'test.entity.player.yaml')
        self.name_user = "us1!{er"
        self.name_player = "Jeff the Girl"
        self.name_campaign = "some-forgotten-campaign"

        self.repo = player_repo.PlayerFileTree(self.data_root)
        self.data = self.repo._load_for_unit_tests(self.data_root,
                                                   user=self.name_user,
                                                   campaign=self.name_campaign,
                                                   player=self.name_player,
                                                   repository='unit test hacks')

    def tearDown(self):
        self.data_root = None
        self.name_user = None
        self.name_player = None
        self.name_campaign = None
        self.data = None

    # --------------------------------------------------------------------------
    # Simple Cases
    # --------------------------------------------------------------------------

    def test_load_data(self):
        # Did we get anything?
        self.assertTrue(self.data)

        # Does it contain the data we think it should?
        self.assertEqual(self.name_user,     self.data['user']['name'])
        self.assertEqual(self.name_campaign, self.data['campaign']['name'])
        self.assertEqual(self.name_player,   self.data['player']['name'])

        self.assertEqual(68341,
                         self.data['player']['level']['xp']['current'])
        self.assertEqual('(${this.score} - 10) // 2',
                         self.data['player']['ability']['charisma']['modifier'])
        self.assertEqual(None,
                         self.data['player']['defense']['immunity'])
        self.assertEqual(0,
                         self.data['player']['skill']['use-magic-device']['ranks'])
        self.assertEqual(False,
                         self.data['player']['skill']['use-magic-device']['class'])

    def test_init(self):
        # Did we get anything?
        self.assertTrue(self.data)

        # What about when we try to say this data is a player entity?
        entity = player.Player(self.data)
        self.assertTrue(entity)
        self.assertTrue(entity._data)
        self.assertTrue(entity._data_user)
        self.assertTrue(entity._data_campaign)

        self.assertEqual(68341,
                         entity._data['level']['xp']['current'])
        self.assertEqual('(${this.score} - 10) // 2',
                         entity._data['ability']['charisma']['modifier'])
        self.assertEqual(None,
                         entity._data['defense']['immunity'])
        self.assertEqual(0,
                         entity._data['skill']['use-magic-device']['ranks'])
        self.assertEqual(False,
                         entity._data['skill']['use-magic-device']['class'])




# TODO: test that more is loaded...
#     def test_load_more(self):
#         # Did we get anything?
#         self.assertTrue(self.data)
#
#         # Does it contain the data we think it should?
#         self.assertEqual(self.name_user,     self.data['user']['name'])
#         self.assertEqual(self.name_campaign, self.data['campaign']['name'])
#         self.assertEqual(self.name_player,   self.data['player']['name'])


# --------------------------------Unit Testing----------------------------------
# --                      Main Command Line Entry Point                       --
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main()
