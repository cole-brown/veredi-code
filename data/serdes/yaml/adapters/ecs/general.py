# coding: utf-8

'''
YAML library subclasses for encoding/decoding components.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import yaml

from veredi.data.codec.adapter.group import KeyGroupMarker, UserDefinedMarker


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO [2020-08-23]: Change to using register & tags!


# -----------------------------------------------------------------------------
# Grouping
# -----------------------------------------------------------------------------

# ------------------------------
# YAML Construction Notes / Examples
# ------------------------------

# Our Usual Thing:
# class EntryGroup(VerediYamlTag):
#     '''
#     A list of elements with something in common has been grouped up. E.g.:
#       - Knowledge skills.
#     '''
#     yaml_tag = '!grouped'

# Untested but should work?
# class EntryGroup(base.VerediYamlTag):
#     '''
#     A list of elements with something in common has been grouped up. E.g.:
#       - Knowledge skills.
#     '''
#
#     yaml_tag = '!grouped'
#
#    def __init__(self, value):
#        print(self.__class__.__name__, "__init__", value)
#
#    @classmethod
#    def from_yaml(cls, loader, node):
#     instance = EntryGroup.__new__(EntryGroup)
#     yield instance
#     state = loader.construct_scalar(node)
#     instance.__init__(state)


# This way works too:
# class EntryGroup:
#     '''
#     A list of elements with something in common has been grouped up. E.g.:
#       - Knowledge skills.
#     '''
#     yaml_tag = '!grouped'
#
#     def __init__(self, state):
#         print("grouped entry state:", state)


# But I think this is the best way for getting to an Adapter ASAP:
#
# def grouped_constructor(loader, node):
#     instance = EntryGroup.__new__(EntryGroup)
#     yield instance
#     state = loader.construct_scalar(node)
#     instance.__init__(state)
#
# yaml.add_constructor(EntryGroup.yaml_tag,
#                      grouped_constructor,
#                      Loader=yaml.SafeLoader)


# ------------------------------
# '!grouped'
# ------------------------------

# Constructor for our KeyGroupMarker adapter class.
def grouped_constructor(loader, node):
    '''
    Single pass constructor for this tag since it's easy and also it needs to
    know its name for it to hash.
    '''
    instance = KeyGroupMarker.__new__(KeyGroupMarker)
    name = loader.construct_scalar(node)
    instance.__init__(name)
    return instance


yaml.add_constructor('!grouped',
                     grouped_constructor,
                     Loader=yaml.SafeLoader)


# ------------------------------
# '!user.defined'
# ------------------------------

# Constructor for our UserDefinedMarker adapter class.
def user_defined_constructor(loader, node):
    '''
    Single pass constructor for this tag since it's easy and also it needs to
    know its name for it to hash.
    '''
    instance = UserDefinedMarker.__new__(UserDefinedMarker)
    name = loader.construct_scalar(node)
    instance.__init__(name)
    return instance


yaml.add_constructor('!user.defined',
                     user_defined_constructor,
                     Loader=yaml.SafeLoader)
