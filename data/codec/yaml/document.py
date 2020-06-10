# coding: utf-8

'''
Veredi YAML Document Types.

The Power Of '--- !a-document-incoming'
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from . import base

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# YAML Doc Types
# -----------------------------------------------------------------------------

# ---
# Metadata
# ---

class DocMetadata(base.VerediYamlDocument):
    yaml_tag = '!metadata'


# ---
# Config
# ---

class DocConfiguration(base.VerediYamlDocument):
    yaml_tag = '!configuration'


# ---
# Other Doc Types
# ---

# See more specific files, e.g. component.py.
