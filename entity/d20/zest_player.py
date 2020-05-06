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
import enum

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

    def test_get_raw(self):
        # Did we get_raw anything?
        self.assertTrue(self.data)

        # What about when we try to say this data is a player entity?
        entity = player.Player(self.data)
        self.assertTrue(entity)
        self.assertTrue(entity._data)

        self.assertEqual(68341,
                         entity.get_raw('level', 'xp', 'current'))
        self.assertEqual('(${this.score} - 10) // 2',
                         entity.get_raw('ability', 'charisma', 'modifier'))

        # We don't have immunity, but this should at least not throw anything.
        class defense(enum.Enum):
            spell_resistance = ["defense", "spell-resistance"]
        self.assertEqual(["defense", "spell-resistance"],
                         defense.spell_resistance.value)
        self.assertEqual(1,
                         entity.get_raw(*defense.spell_resistance.value))
        self.assertEqual(1,
                         entity.get_raw(defense.spell_resistance))

        class armor_class(enum.Enum):
            base = "base"
            def hyphen(self, string):
                return string.replace('_', '-')
            @property
            def key(self):
                return [
                    self.hyphen("defense"),
                    self.hyphen(self.__class__.__name__),
                    self.hyphen(self.value)
                ]
        self.assertEqual(10,
                         entity.get_raw(armor_class.base))

    def test_get(self):
        # Did we get_raw anything?
        self.assertTrue(self.data)

        # What about when we try to say this data is a player entity?
        entity = player.Player(self.data)
        self.assertTrue(entity)
        self.assertTrue(entity._data)

        ctx = entity.get('level', 'xp', 'current')
        self.assertIsNotNone(ctx)
        self.assertEqual(68341,
                         ctx.value)
        self.assertEqual(['level', 'xp', 'current'],
                         ctx.keys)

        ctx = entity.get('ability', 'charisma', 'modifier')
        self.assertIsNotNone(ctx)
        self.assertEqual('(${this.score} - 10) // 2',
                         ctx.value)
        self.assertEqual(['ability', 'charisma', 'modifier'],
                         ctx.keys)

        # We don't have immunity, but this should at least not throw anything.
        class defense(enum.Enum):
            spell_resistance = ["defense", "spell-resistance"]
        ctx = entity.get(*defense.spell_resistance.value)
        self.assertIsNotNone(ctx)
        self.assertEqual(1,
                         ctx.value)
        self.assertEqual(["defense", "spell-resistance"],
                         ctx.keys)
        ctx = entity.get(defense.spell_resistance)
        self.assertIsNotNone(ctx)
        self.assertEqual(1,
                         ctx.value)
        self.assertEqual(["defense", "spell-resistance"],
                         ctx.keys)

        class armor_class(enum.Enum):
            base = "base"
            def hyphen(self, string):
                return string.replace('_', '-')
            @property
            def key(self):
                return [
                    self.hyphen("defense"),
                    self.hyphen(self.__class__.__name__),
                    self.hyphen(self.value)
                ]
        ctx = entity.get(armor_class.base)
        self.assertIsNotNone(ctx)
        self.assertEqual(10,
                         ctx.value)
        self.assertEqual(["defense", "armor-class", "base"],
                         ctx.keys)

# TODO: test.... recalc?..


# --------------------------------Unit Testing----------------------------------
# --                      Main Command Line Entry Point                       --
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main()
