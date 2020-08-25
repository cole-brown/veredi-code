# coding: utf-8

'''
YAML library subclasses for encoding/decoding components.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from ..base import VerediYamlDocument, VerediYamlTag
from ... import tags


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Base yaml.YAMLObject?
# -----------------------------------------------------------------------------

# TODO [2020-05-21]: YAML something or other so we can barf out context
# in our errors? Or should we be throwing YAML errors instead of Veredi errors?


# -----------------------------------------------------------------------------
# Document Types
# -----------------------------------------------------------------------------

class DocComponent(VerediYamlDocument):
    _YAML_TAG_NAME = 'component'
    yaml_tag = tags.make(_YAML_TAG_NAME)


class DocComponentExample(VerediYamlDocument):
    _YAML_TAG_NAME = 'component.example'
    yaml_tag = tags.make(_YAML_TAG_NAME)


class DocComponentTemplate(VerediYamlDocument):
    _YAML_TAG_NAME = 'component.template'
    yaml_tag = tags.make(_YAML_TAG_NAME)


class DocComponentRequirements(VerediYamlDocument):
    _YAML_TAG_NAME = 'component.requirements'
    yaml_tag = tags.make(_YAML_TAG_NAME)


# -----------------------------------------------------------------------------
# Template Objects
# -----------------------------------------------------------------------------

# ---
# Property
# ---

class PropertyPsuedo(VerediYamlTag):
    _YAML_TAG_NAME = 'veredi.psuedo-property'
    yaml_tag = tags.make(_YAML_TAG_NAME)
