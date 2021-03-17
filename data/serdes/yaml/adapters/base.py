# coding: utf-8

'''
Base classes for Veredi YAML formatted files.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, Type, MutableMapping
import yaml

from veredi.base.strings          import pretty
from veredi.data.config.hierarchy import Hierarchy
from ..                           import tags
from ..                           import registry


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# YAML Doc Types
# -----------------------------------------------------------------------------

class VerediYamlDocument(yaml.YAMLObject):
    # ---
    # Set These in Subclasses!
    # ---
    _YAML_TAG_NAME = 'document'
    yaml_tag = tags.make(_YAML_TAG_NAME)

    # ---
    # YAMLObject's class vars:
    # ---
    yaml_loader = yaml.SafeLoader

    @classmethod
    def from_yaml(cls: Type['VerediYamlDocument'],
                  loader: yaml.SafeLoader,
                  node: yaml.Node):
        return loader.construct_yaml_object(node, cls)

    # ---
    # Decoding
    # ---

    def _inject_doc_type(self, target: MutableMapping[str, Any]) -> None:
        '''
        Returns a (key, value) tuple for putting in a dictionary
        or something somewhere.
        '''
        target[Hierarchy.VKEY_DOC_TYPE] = self.yaml_tag[1:]

    def deserialize(self):
        '''
        YAML objects & stuff to plain old data structure.

        Return value should have doc_type injected.
        '''
        # Default to giving our __dict__ out - it may be plain old data
        # structures, depending on the document.
        self._inject_doc_type(self.__dict__)
        return self.__dict__

    # ---
    # Strings and Things
    # ---

    def to_pretty(self):
        return f"{self.__class__.__name__}:\n{pretty.to_str(self.__dict__, 2)}"

    def __str__(self):
        return f"{self.__class__.__name__}:\n{self.__dict__}"


registry.register(VerediYamlDocument._YAML_TAG_NAME,
                  VerediYamlDocument,
                  None, None)


# -----------------------------------------------------------------------------
# YAML Object?
# -----------------------------------------------------------------------------

class VerediYamlObject(yaml.YAMLObject):
    # Set in subclasses!
    _YAML_TAG_NAME = 'document'
    yaml_tag = tags.make(_YAML_TAG_NAME)

    # YAMLObject's class vars:
    yaml_loader = yaml.SafeLoader

    # ---
    # Set These in Subclasses!
    # ---
    # yaml_tag = '!veredi.example'

    def __init__(self, value):
        pass

    @classmethod
    def from_yaml(cls, loader, node):
        # print(cls.yaml_tag, "from_yaml", str(cls), str(loader), str(node))
        return cls(node.value)

    def deserialize(self):
        '''
        YAML objects & stuff to plain old data structure.
        '''
        return self.__dict__


# -----------------------------------------------------------------------------
# YAML... Tag?
# -----------------------------------------------------------------------------

class VerediYamlTag(VerediYamlObject):
    # ---
    # Set These in Subclasses!
    # ---
    # _YAML_TAG_NAME = ''
    # yaml_tag = tags.make(_YAML_TAG_NAME)

    # ---
    # YAMLObject's class vars:
    # ---
    yaml_loader = yaml.SafeLoader

    def __init__(self, value):
        self.tag = value

    @classmethod
    def from_yaml(cls, loader, node):
        # print(cls.yaml_tag, "from_yaml", str(cls), str(loader), str(node))
        return cls(node.value)

    def __str__(self):
        return f"{self.__class__.__name__}: {self.tag}"

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.tag}>"


# -----------------------------------------------------------------------------
# Requirements Objects
# -----------------------------------------------------------------------------

class VerediYamlRequirement(VerediYamlTag):
    # ---
    # Set These in Subclasses!
    # ---
    # _YAML_TAG_NAME = ''
    # yaml_tag = tags.make(_YAML_TAG_NAME)

    # ---
    # YAMLObject's class vars:
    # ---
    yaml_loader = yaml.SafeLoader

    def __init__(self, value):
        super().__init__(value)

        # Normalize our tag's value.
        self.normalize()

    def valid(self, check):
        '''
        Return Truthy if the `check` value is valid for this
        field's requirements.
        '''
        raise NotImplementedError(
            f"{self.__class__.__name__}.valid() not implemented.")

    def normalize(self):
        '''
        Normalize the representation of this Component Requirement.

        This function should get the initial value from self.tag, and save its
        normalized result there as well.
        '''
        raise NotImplementedError(
            f"{self.__class__.__name__}.normalize() not implemented.")
