# coding: utf-8

'''
YAML library subclasses for encoding/decoding system data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import yaml

from veredi.data.records.record import DocType

from ..base                     import VerediYamlDocument
from ...                        import tags
from ...                        import registry
from ....adapter                import meta

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Document Types
# -----------------------------------------------------------------------------

# ------------------------------
# Game
# ------------------------------

class DocGameDefinition(VerediYamlDocument):
    _YAML_TAG_NAME = DocType.definition.game.value
    yaml_tag = tags.make(_YAML_TAG_NAME)


registry.register(DocGameDefinition._YAML_TAG_NAME,
                  DocGameDefinition,
                  None, None)


class DocGameSaved(VerediYamlDocument):
    _YAML_TAG_NAME = DocType.saved.game.value
    yaml_tag = tags.make(_YAML_TAG_NAME)


registry.register(DocGameSaved._YAML_TAG_NAME,
                  DocGameSaved,
                  None, None)


# ------------------------------
# ECS
# ------------------------------

# class DocComponent(VerediYamlDocument):
#     _YAML_TAG_NAME = 'system'
#    yaml_tag = tags.make(_YAML_TAG_NAME)
#
# registry.register(DocComponent._YAML_TAG_NAME,
#                   DocComponent,
#                   None, None)


class DocSystemDefinition(VerediYamlDocument):
    _YAML_TAG_NAME = DocType.definition.system.value
    yaml_tag = tags.make(_YAML_TAG_NAME)


registry.register(DocSystemDefinition._YAML_TAG_NAME,
                  DocSystemDefinition,
                  None, None)


# -----------------------------------------------------------------------------
# Tags
# -----------------------------------------------------------------------------

# ------------------------------
# '!meta'
# ------------------------------

# TODO [2020-08-23]: Change to using register & tags!
_META_TAG_NAME = 'meta'
_META_YAML_TAG = tags.make(_META_TAG_NAME)


# Constructor for our MetaMarker adapter class.
def tag_meta_constructor(loader, node):
    '''
    Single pass constructor for this tag since it's easy and also it needs to
    know its name for it to hash.
    '''
    instance = meta.MetaMarker.__new__(meta.MetaMarker)
    name = loader.construct_scalar(node)
    try:
        instance.__init__(name)
    except ValueError as error:
        raise yaml.YAMLError(
            f"!meta tag node '{node}' failed parsing.") from error

    return instance


yaml.add_constructor(_META_YAML_TAG,
                     tag_meta_constructor,
                     Loader=yaml.SafeLoader)
