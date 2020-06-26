# coding: utf-8

'''
YAML library subclasses for encoding/decoding system data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import yaml

from .. import base
from ...adapter import meta


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Document Types
# -----------------------------------------------------------------------------

# class DocComponent(base.VerediYamlDocument):
#     yaml_tag = '!system'


class DocSystemDefinition(base.VerediYamlDocument):
    yaml_tag = '!system.definition'


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
