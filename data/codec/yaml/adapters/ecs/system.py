# coding: utf-8

'''
YAML library subclasses for encoding/decoding system data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import yaml

from .. import registry
from ..base import VerediYamlDocument
from ....adapter import meta


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO [2020-08-23]: Change to using register & tags!


# -----------------------------------------------------------------------------
# Document Types
# -----------------------------------------------------------------------------

# class DocComponent(VerediYamlDocument):
#     _YAML_TAG_NAME = 'system'


class DocSystemDefinition(VerediYamlDocument):
    _YAML_TAG_NAME = 'system.definition'


registry.register(VerediYamlDocument._YAML_TAG_NAME,
                  VerediYamlDocument,
                  None, None)


# -----------------------------------------------------------------------------
# Tags
# -----------------------------------------------------------------------------

# ------------------------------
# '!meta'
# ------------------------------

# Constructor for our MetaMarker adapter class.
def tag_meta_constructor(loader, node):
    '''
    Single pass constructor for this tag since it's easy and also it needs to
    know its name for it to hash.
    '''
    # yaml_tag = '!meta'

    instance = meta.MetaMarker.__new__(meta.MetaMarker)
    name = loader.construct_scalar(node)
    try:
        instance.__init__(name)
    except ValueError as error:
        raise yaml.YAMLError(
            f"!meta tag node '{node}' failed parsing.") from error

    return instance


yaml.add_constructor('!meta',
                     tag_meta_constructor,
                     Loader=yaml.SafeLoader)
