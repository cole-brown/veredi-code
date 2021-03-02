# coding: utf-8

'''
Custom YAML Formatter for:
  - Logging
  - Serialization/Deserialiazition (Serdes).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, Type, NewType, Callable, Mapping


import yaml
from collections import OrderedDict
import enum


# Logging needs this stuff for YAML formatted logs, so do not log from here.
# from veredi.logs               import log


# -----------------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------------

YamlRepresenter = NewType('YamlRepresenter',
                          Callable[[yaml.Dumper, object], yaml.Node])
'''
Callback signature for registering new representer functions for YAML
serialization.
'''


YamlConstructor = NewType('YamlConstructor',
                          Callable[[yaml.Node], Any])
'''
Callback signature for registering new constructor functions for YAML
deserialization.
'''


# -----------------------------------------------------------------------------
# YAML Large String Dumpers
# -----------------------------------------------------------------------------

class FoldedString(str):
    '''
    Class just marks this string to be dumped in 'folded' YAML string format.
    '''
    pass


class LiteralString(str):
    '''
    Class just marks this string to be dumped in 'literal' YAML string format.
    '''
    pass


def folded_string_representer(dumper: yaml.Dumper,
                              data:   str) -> yaml.ScalarNode:
    '''
    Register FoldedString as the correct style of literal.
    '''
    return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='>')


def literal_string_representer(dumper: yaml.Dumper,
                               data:   str) -> yaml.ScalarNode:
    '''
    Register FoldedString as the correct style of literal.
    '''
    return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='|')


def ordered_dict_representer(dumper: yaml.Dumper,
                             data:   Mapping) -> yaml.MappingNode:
    '''
    Register OrderedDict in order to be able to dump it.
    '''
    return dumper.represent_mapping(u'tag:yaml.org,2002:map',
                                    data.items(),
                                    flow_style=False)  # block flow style


# -----------------------------------------------------------------------------
# YAML Enum Value Dumpers
# -----------------------------------------------------------------------------

def enum_int_representer(dumper: yaml.Dumper,
                         data:   enum.Enum) -> yaml.ScalarNode:
    '''
    Register some sort of enum as being serialized by int value.
    '''
    value = data.value
    if not isinstance(value, int):
        # Hm... can't log... don't want to print...
        # Just represent this as best we can?
        value = int(value)
    return dumper.represent_scalar(u'tag:yaml.org,2002:int',
                                   value)


def enum_string_value_representer(dumper: yaml.Dumper,
                                  data:   enum.Enum) -> yaml.ScalarNode:
    '''
    Register some sort of enum as being serialized by str value.
    '''
    value = data.value
    if not isinstance(value, str):
        # Hm... can't log... don't want to print...
        # Just represent this as best we can?
        value = str(value)
    return dumper.represent_scalar(u'tag:yaml.org,2002:str',
                                   value)

def enum_to_string_representer(dumper: yaml.Dumper,
                               data:   enum.Enum) -> yaml.ScalarNode:
    '''
    Register some sort of enum as being serialized by `str()`.
    '''
    value = str(data)
    return dumper.represent_scalar(u'tag:yaml.org,2002:str',
                                   value)


def enum_representer(enum_value: enum.Enum) -> YamlRepresenter:
    '''
    Get the correct representer function for the enum's value type.

    NOTE: Does not support multi-type enums like, oh, say... String value enums
    with an 'IGNORE = None' value in them.

    If we don't have a representer for that specific kind of value, raises an
    error.
    '''
    value = enum_value.value

    if isinstance(value, int):
        return enum_int_representer

    if isinstance(value, str):
        return enum_string_value_representer

    raise TypeError(f"No representer for {enum_value} with value "
                    f"type {type(value)}.",
                    enum_value,
                    value)


# -----------------------------------------------------------------------------
# Register representers with YAML.
# -----------------------------------------------------------------------------

def represent(klass: Type, function: YamlRepresenter) -> None:
    '''
    Add a representer to YAML.
    '''
    yaml.add_representer(klass,
                         function,
                         Dumper=yaml.SafeDumper)


def representers() -> None:
    '''
    Add additional, common, basic representers needed to YAML.
    '''
    represent(FoldedString,
              folded_string_representer)
    represent(LiteralString,
              literal_string_representer)
    represent(OrderedDict,
              ordered_dict_representer)


# -----------------------------------------------------------------------------
# Register constructors with YAML.
# -----------------------------------------------------------------------------

def construct(tag: str, function: YamlConstructor) -> None:
    '''
    Add a constructor to YAML.
    '''
    yaml.add_constructor(tag,
                         function,
                         Loader=yaml.SafeLoader)


def constructors() -> None:
    '''
    Add additional, common, basic constructors needed to YAML.
    '''
    # None right now.
    pass


# -----------------------------------------------------------------------------
# Automatically set up when imported.
# -----------------------------------------------------------------------------

representers()
constructors()
