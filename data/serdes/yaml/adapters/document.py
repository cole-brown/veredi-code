# coding: utf-8

'''
Veredi YAML Document Types.

The Power Of '--- !a-document-incoming'
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from . import base
from .. import tags
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
    yaml_tag = tags.make(_YAML_TAG_NAME)


registry.register(DocMetadata._YAML_TAG_NAME,
                  DocMetadata,
                  None, None)


# ---
# Config
# ---

class DocConfiguration(base.VerediYamlDocument):
    _YAML_TAG_NAME = 'configuration'
    yaml_tag = tags.make(_YAML_TAG_NAME)


registry.register(DocConfiguration._YAML_TAG_NAME,
                  DocConfiguration,
                  None, None)


# ---
# Other Doc Types
# ---

# See more specific files, e.g. component.py.
