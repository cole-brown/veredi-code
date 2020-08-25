# coding: utf-8

'''
Functions in YAML.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import yaml

from .. import tags
from .. import registry


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO [2020-08-23]: Ye Olde File. Do we still want to do these this way?

# TODO:
# Logical:
#   - and  - veredi.and [val0, ...valN]
#   - or   - veredi.or [val0, ...valN]
#   - not  - veredi.not val0
#   - if   - veredi.if [condition_name, value_if_true, value_if_false]
# Misc:
#   - auto
#   - has
#   - tag
# Math:
#   - sum
# String:
#   - join - veredi.join [ ":", [ a, b, c ] ]
#   - lower - veredi.lower
#     - lower case text
#   - upper - veredi.upper
#     - UPPER CASE TEXT
#   - title - veredi.title
#     - Title Case Text
#   - select / nth / index - veredi.index [3, [val0, ...valN]]
#   - split - veredi.split [delimiter, string]
#   - substitute - veredi.sub [ string, replacement_dict ]
#   - reference - ${value}, ${this.sibling-thing}


# -----------------------------------------------------------------------------
# YAML Tags
# -----------------------------------------------------------------------------

class FnHas(yaml.YAMLObject):
    # ---
    # registry / YAML tag
    # ---
    _YAML_TAG_NAME = 'veredi.has'
    yaml_tag = tags.make(_YAML_TAG_NAME)

    # ---
    # YAMLObject's class vars:
    # ---
    yaml_loader = yaml.SafeLoader

    def __init__(self, val):
        # print(FnHas.yaml_tag, "init", val)
        self.val = val

    @classmethod
    def from_yaml(cls, loader, node):
        # print(FnHas.yaml_tag, "from_yaml", str(cls), str(loader), str(node))
        return cls(node.value)


registry.register(FnHas._YAML_TAG_NAME,
                  FnHas,
                  None, None)


class FnAuto(yaml.YAMLObject):
    # ---
    # registry / YAML tag
    # ---
    _YAML_TAG_NAME = 'veredi.auto'
    yaml_tag = tags.make(_YAML_TAG_NAME)

    # ---
    # YAMLObject's class vars:
    # ---
    yaml_loader = yaml.SafeLoader

    def __init__(self, val):
        # print(FnAuto.yaml_tag, "init", val)
        self.val = val

    @classmethod
    def from_yaml(cls, loader, node):
        # print(FnAuto.yaml_tag, "from_yaml", str(cls), str(loader), str(node))
        return cls(node.value)


registry.register(FnAuto._YAML_TAG_NAME,
                  FnAuto,
                  None, None)


class FnTag(yaml.YAMLObject):
    # ---
    # registry / YAML tag
    # ---
    _YAML_TAG_NAME = 'veredi.tag'
    yaml_tag = tags.make(_YAML_TAG_NAME)

    # ---
    # YAMLObject's class vars:
    # ---
    yaml_loader = yaml.SafeLoader

    def __init__(self, val):
        # print(FnTag.yaml_tag, "init", val)
        self.val = val

    @classmethod
    def from_yaml(cls, loader, node):
        # print(FnTag.yaml_tag, "from_yaml", str(cls), str(loader), str(node))
        return cls(node.value)


registry.register(FnTag._YAML_TAG_NAME,
                  FnTag,
                  None, None)


class FnSum(yaml.YAMLObject):
    # ---
    # registry / YAML tag
    # ---
    _YAML_TAG_NAME = 'veredi.sum'
    yaml_tag = tags.make(_YAML_TAG_NAME)

    # ---
    # YAMLObject's class vars:
    # ---
    yaml_loader = yaml.SafeLoader

    def __init__(self, val):
        # print(FnSum.yaml_tag, "init", val)
        self.val = val

    @classmethod
    def from_yaml(cls, loader, node):
        # print(FnSum.yaml_tag, "from_yaml", str(cls), str(loader), str(node))
        return cls(node.value)


registry.register(FnSum._YAML_TAG_NAME,
                  FnSum,
                  None, None)
