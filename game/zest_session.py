# coding: utf-8

'''
A session of a game/campaign.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
import unittest

# Framework
from . import session
from veredi.entity import player as p_entity
from veredi.repository import player as p_repo

# Our Stuff


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Test_Session(unittest.TestCase):

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
        self.repo = None
        self.data = None

    def test_init():
        session = session.Session(self.name_campaign,
                                  [(self.name_user, self.name_player)],
                                  self.repo)
