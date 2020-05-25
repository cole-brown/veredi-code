# coding: utf-8

'''
Veredi YAML Document Types.

The Power Of '--- !a-document-incoming'
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import yaml

from veredi.logger import log
from veredi.data.config.registry import register
from veredi.data import exceptions

from . import base

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# YAML Doc Types
# ------------------------------------------------------------------------------

# ---
# Metadata
# ---

class DocMetadata(base.VerediYamlDocument):
    yaml_tag = '!metadata'

    def decode(self):
        '''
        YAML objects & stuff to plain old data structure.
        '''
        return self.__dict__

# ---
# Repository
# ---

class DocRepository(base.VerediYamlDocument):
    yaml_tag = '!repository'

    def __str__(self):
        return (f"{self.__class__.__name__}:\n"
                f"  owner:    {self.owner if hasattr(self, 'owner') else 'no own'}\n"
                f"  campaign: {self.campaign if hasattr(self, 'campaign') else 'no camp'}\n"
                f"  session:  {self.session if hasattr(self, 'session') else 'no sess'}\n"
                f"  player:   {self.player if hasattr(self, 'player') else 'no plr'}\n")


# ---
# Component Doc Types
# ---

# See ./component.py
