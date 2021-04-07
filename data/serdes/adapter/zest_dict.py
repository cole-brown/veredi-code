# coding: utf-8

'''
Tests for the DataDict and KeyGroup classes.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.zest.base.unit import ZestBase
from veredi.zest.zpath     import TestType

from .dict import DataDict, KeyGroupMarker


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_DataDict(ZestBase):
    '''
    Test that fancy sorta-dictionary.
    '''

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = __file__

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    def set_up(self):
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

    def tear_down(self):
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


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.data.serdes.adapter.zest_dict

if __name__ == '__main__':
    import unittest
    unittest.main()
