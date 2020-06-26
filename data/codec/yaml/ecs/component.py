# coding: utf-8

'''
YAML library subclasses for encoding/decoding components.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from .. import base


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

class DocComponent(base.VerediYamlDocument):
    yaml_tag = '!component'


class DocComponentExample(base.VerediYamlDocument):
    yaml_tag = '!component.example'


class DocComponentTemplate(base.VerediYamlDocument):
    yaml_tag = '!component.template'


class DocComponentRequirements(base.VerediYamlDocument):
    yaml_tag = '!component.requirements'


# -----------------------------------------------------------------------------
# Template Objects
# -----------------------------------------------------------------------------

# ---
# Property
# ---

class PropertyPsuedo(base.VerediYamlTag):
    yaml_tag = '!veredi.psuedo-property'
