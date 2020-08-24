# coding: utf-8

'''
YAML library subclasses for encoding/decoding components.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from ..base import VerediYamlDocument, VerediYamlTag


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


class DocComponentExample(VerediYamlDocument):
    _YAML_TAG_NAME = 'component.example'


class DocComponentTemplate(VerediYamlDocument):
    _YAML_TAG_NAME = 'component.template'


class DocComponentRequirements(VerediYamlDocument):
    _YAML_TAG_NAME = 'component.requirements'


# -----------------------------------------------------------------------------
# Template Objects
# -----------------------------------------------------------------------------

# ---
# Property
# ---

class PropertyPsuedo(VerediYamlTag):
    _YAML_TAG_NAME = 'veredi.psuedo-property'
