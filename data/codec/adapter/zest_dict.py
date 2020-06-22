# coding: utf-8

'''
Tests for the DataDict and KeyGroup classes.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from .dict import DataDict, KeyGroupMarker


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_DataDict(unittest.TestCase):
    '''
    Test that fancy sorta-dictionary.
    '''

    def setUp(self):
        self.debugging = False

        self.raw_data = {
            'running': {
                'class': True,
                'ranks': 3,
            },
            'paying attention': {
                'class': False,
                'ranks': 0,
            },
            KeyGroupMarker('knowledge'): {
                'weird stuff': {
                    'class': True,
                    'ranks': 17,
                },
                'etc': {
                    'class': False,
                    'ranks': 1,
                },
            },
            KeyGroupMarker('profession'): {
                'weirdologist': {
                    'class': True,
                    'ranks': 16,
                },
            },
        }

        self.expected_map = {
            'running': {
                'class': True,
                'ranks': 3,
            },
            'paying attention': {
                'class': False,
                'ranks': 0,
            },
        }

        self.expected_groups = {
            'knowledge': {
                'weird stuff': {
                    'class': True,
                    'ranks': 17,
                },
                'etc': {
                    'class': False,
                    'ranks': 1,
                },
            },

            'profession': {
                'weirdologist': {
                    'class': True,
                    'ranks': 16,
                },
            },
        }

    def tearDown(self):
        self.debugging       = False
        self.raw_data        = None
        self.expected_map    = None
        self.expected_groups = None

    def create_data_dict(self):
        return DataDict(self.raw_data)

    def test_init(self):
        data = self.create_data_dict()
        self.assertTrue(data)

    def test_contains(self):
        data = self.create_data_dict()
        self.assertTrue(data)

        self.assertTrue('running' in data)
        self.assertTrue('paying attention' in data)
        self.assertTrue('knowledge (weird stuff)' in data)
        self.assertTrue('profession (weirdologist)' in data)

        self.assertFalse('walking' in data)
        self.assertFalse('profession (unemployed)' in data)

    def test_get(self):
        data = self.create_data_dict()
        self.assertTrue(data)

        self.assertTrue(data['running'],
                        self.expected_map['running'])
        self.assertTrue(data['paying attention'],
                        self.expected_map['paying attention'])
        self.assertTrue(data['knowledge (weird stuff)'],
                        self.expected_groups['knowledge']['weird stuff'])
        self.assertTrue(data['profession (weirdologist)'],
                        self.expected_groups['profession']['weirdologist'])


#     def test_skill_req(self):
#         self.set_up_subs()
#         entity = self.create_entity()
#         component = self.load(entity)
#
#         request = self.skill_request(entity, "Acrobatics")
#         self.trigger_events(request)
#
#         result = self.events[0]
#         self.assertIsInstance(result, SkillResult)
#         self.assertEqual(result.skill.lower(), request.skill.lower())
#         # request and result should be both for our entity
#         self.assertEqual(result.id, request.id)
#         self.assertEqual(result.id, entity.id)
#
#         # Skill Guy should have Nine Acrobatics.
#         self.assertEqual(result.amount, 9)
#         self.assertTrue(False)
#
# #         with log.LoggingManager.on_or_off(self.debugging):
# #             self.make_it_so(skill_request)
