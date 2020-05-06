# coding: utf-8

'''
YAML Format Reader / Writer
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import yaml

from .. import exceptions
from veredi.logger import log

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class YamlFormat:
    _EXTENSION = "yaml"

    # https://pyyaml.org/wiki/PyYAMLDocumentation

    # TODO: ABC's abstract method
    def ext(self):
        return self._EXTENSION

    def load(self, file_obj, error_context):
        '''Load and decodes data from a single data file.

        Raises:
          - exceptions.LoadError
            - wrapped yaml.YAMLDecodeError
          Maybes:
            - Other yaml/file errors?
        '''
        data = None
        try:
            data = yaml.safe_load(file_obj)
        except yaml.YAMLError as error:
            log.error('YAML failed while loading the file. {} {}',
                      error.__class__.__qualname__,
                      error_context)
            data = None
            raise exceptions.LoadError("Error loading yaml file:",
                                       error,
                                       error_context) from error
        return data


# ------------------------------------------------------------------------------
# YAML Tags
# ------------------------------------------------------------------------------

class FnHas(yaml.YAMLObject):
    yaml_loader = yaml.SafeLoader
    yaml_tag = '!veredi.has'

    def __init__(self, val):
        # print(FnHas.yaml_tag, "init", val)
        self.val = val

    @classmethod
    def from_yaml(cls, loader, node):
        # print(FnHas.yaml_tag, "from_yaml", str(cls), str(loader), str(node))
        return cls(node.value)


class FnAuto(yaml.YAMLObject):
    yaml_loader = yaml.SafeLoader
    yaml_tag = '!veredi.auto'

    def __init__(self, val):
        # print(FnAuto.yaml_tag, "init", val)
        self.val = val

    @classmethod
    def from_yaml(cls, loader, node):
        # print(FnAuto.yaml_tag, "from_yaml", str(cls), str(loader), str(node))
        return cls(node.value)


class FnTag(yaml.YAMLObject):
    yaml_loader = yaml.SafeLoader
    yaml_tag = '!veredi.tag'

    def __init__(self, val):
        # print(FnTag.yaml_tag, "init", val)
        self.val = val

    @classmethod
    def from_yaml(cls, loader, node):
        # print(FnTag.yaml_tag, "from_yaml", str(cls), str(loader), str(node))
        return cls(node.value)


class FnSum(yaml.YAMLObject):
    yaml_loader = yaml.SafeLoader
    yaml_tag = '!veredi.sum'

    def __init__(self, val):
        # print(FnSum.yaml_tag, "init", val)
        self.val = val

    @classmethod
    def from_yaml(cls, loader, node):
        # print(FnSum.yaml_tag, "from_yaml", str(cls), str(loader), str(node))
        return cls(node.value)


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
