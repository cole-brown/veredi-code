# coding: utf-8

'''
Base classes for Veredi YAML formatted files.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import yaml

from veredi.logger import log
from veredi.logger import pretty
from veredi.data.config.registry import register
from veredi.data import exceptions

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# YAML Doc Types
# ------------------------------------------------------------------------------

class VerediYamlDocument(yaml.YAMLObject):
    yaml_loader = yaml.SafeLoader
    # Set in subclasses!
    # yaml_tag = '!metadata'

    @classmethod
    def from_yaml(cls, loader, node):
        return loader.construct_yaml_object(node, cls)

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
        print(cls.yaml_tag, "from_yaml", str(cls), str(loader), str(node))
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
