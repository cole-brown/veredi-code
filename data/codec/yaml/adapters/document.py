# coding: utf-8

'''
Veredi YAML Document Types.

The Power Of '--- !a-document-incoming'
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from . import base
from .. import registry


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
    _YAML_TAG_NAME = 'metadata'


registry.register(DocMetadata._YAML_TAG_NAME,
                  DocMetadata,
                  None, None)


# ---
# Config
# ---

class DocConfiguration(base.VerediYamlDocument):
    _YAML_TAG_NAME = 'configuration'


registry.register(DocConfiguration._YAML_TAG_NAME,
                  DocConfiguration,
                  None, None)


# ---
# Other Doc Types
# ---

# See more specific files, e.g. component.py.
