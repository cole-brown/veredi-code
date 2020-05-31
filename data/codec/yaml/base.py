# coding: utf-8

'''
Base classes for Veredi YAML formatted files.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Dict, MutableMapping, Type, Any
import yaml

from veredi.logger import log
from veredi.logger import pretty
from veredi.data.config.registry import register
from veredi.data import exceptions

from veredi.data.config.config import CodecKeys

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# YAML Doc Types
# ------------------------------------------------------------------------------

class VerediYamlDocument(yaml.YAMLObject):
    yaml_loader = yaml.SafeLoader
    # Set in subclasses!
    yaml_tag = '!document'

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
        target[CodecKeys.DOC_TYPE.value] = self.yaml_tag[1:]

    def decode(self):
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


# ------------------------------------------------------------------------------
# YAML Object?
# ------------------------------------------------------------------------------

class VerediYamlObject(yaml.YAMLObject):
    yaml_loader = yaml.SafeLoader

    # ---
    # Set This in Subclasses!
    # ---
    # yaml_tag = '!veredi.example'

    def __init__(self, value):
        pass

    @classmethod
    def from_yaml(cls, loader, node):
        # print(cls.yaml_tag, "from_yaml", str(cls), str(loader), str(node))
        return cls(node.value)


# ------------------------------------------------------------------------------
# YAML... Tag?
# ------------------------------------------------------------------------------

class VerediYamlTag(VerediYamlObject):
    # ---
    # Set This in Subclasses!
    # ---
    # yaml_tag = '!veredi.example'

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


# ------------------------------------------------------------------------------
# YAML... Tag?
# ------------------------------------------------------------------------------

# §-TODO-§ [2020-05-21]: Decided which to keep if these three remain the same:
# VerediYamlObject, VerediYamlTag, VerediYamlEntry
class VerediYamlEntry(VerediYamlObject):
    # ---
    # Set This in Subclasses!
    # ---
    # yaml_tag = '!veredi.example'

    def __init__(self, value):
        self.data = value

    @classmethod
    def from_yaml(cls, loader, node):
        # print(cls.yaml_tag, "from_yaml", str(cls), str(loader), str(node))
        return cls(node.value)

    def __str__(self):
        return f"{self.__class__.__name__}: {self.data}"

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.data}>"


# ------------------------------------------------------------------------------
# Requirements Objects
# ------------------------------------------------------------------------------

class VerediYamlRequirement(VerediYamlTag):
    # Set in subclasses!
    # yaml_tag = '!optional'

    def __init__(self, value):
        super().__init__(value)

        # Normalize our tag's value.
        self.normalize()

    def valid(self, check):
        '''
        Return Truthy if the `check` value is valid for this
        field's requirements.
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.valid() not implemented.")

    def normalize(self):
        '''
        Normalize the representation of this Component Requirement.

        This function should get the initial value from self.tag, and save its
        normalized result there as well.
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.normalize() not implemented.")
