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
from . import template
# from veredi.data.format.yaml import yaml


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Player, File, YAML
# -----------------------------------------------------------------------------

class Test_TemplateRepo_FileYaml(unittest.TestCase):

    def setUp(self):
        self.name_system = "d20"
        self.name_entity = "player"
        self.name_template = "base"

    def tearDown(self):
        self.name_system = None
        self.name_entity = None
        self.name_template = None

    # --------------------------------------------------------------------------
    # Simple Cases
    # --------------------------------------------------------------------------

    def test_load(self):
        repo = template.TemplateFileTree() # using defaults
        data = repo.load_by_name(self.name_system,
                                 self.name_entity,
                                 self.name_template)

        # Did we get anything?
        self.assertTrue(data)

        # Does it contain the data we think it should?
        self.assertEqual('veredi.templates', data['template']['source'])
        self.assertEqual(self.name_system,   data['template']['system'])
        self.assertEqual(self.name_entity,   data['template']['entity'])
        self.assertEqual(self.name_template + '.template', data['template']['name'])


# --------------------------------Unit Testing----------------------------------
# --                      Main Command Line Entry Point                       --
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main()
