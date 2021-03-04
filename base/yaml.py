# coding: utf-8

'''
Custom YAML Formatter for:
  - Logging
  - Serialization/Deserialiazition (Serdes).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (Optional, Union, Any, Type, NewType,
                    Callable, TextIO, Mapping)


import yaml
from collections import OrderedDict, UserString
import enum

# Yaml's Error type to propogate up to our import level.
from yaml import YAMLError

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


class ScalarStyle(enum.Enum):
    '''
    An enum class to represent the scalars' style options YAML has:

    # YAML Example:
    plain: This string is a plain scalar.
    quoted-single: 'SINGLE QUOTES!'
    quoted-double: "Double quotes."
    literal: |
      This indents the string but
      preserves whatever it is exactly.
    folded: >
      This folds the string up into multiple lines for serialzation, and
      unfolds it on deserialization.
    '''
    DEFAULT = None
    '''Let YAML decide.'''

    PLAIN = '_'
    '''Use plain scalars.'''

    QUOTED_SINGLE = "'"
    '''Use single-quoted scalars.'''

    QUOTED_DOUBLE = '"'
    '''Use double-quoted scalars.'''

    LITERAL = '|'
    '''Use literal scalars which will preserve all formatting.'''

    FOLDED = '>'
    '''Use folded scalars which will fold long scalars across multiple lines.'''


class SequenceStyle(enum.Enum):
    '''
    An enum class to represent the sequences' style options YAML has:

    # YAML Example:
    Block style: !!seq
    - Mercury   # Rotates - no light/dark sides.
    - Venus     # Deadliest. Aptly named.
    - Earth     # Mostly dirt.
    - Mars      # Seems empty.
    - Jupiter   # The king.
    - Saturn    # Pretty.
    - Uranus    # Where the sun hardly shines.
    - Neptune   # Boring. No rings.
    - Pluto     # You call this a planet?
    Flow style: !!seq [ Mercury, Venus, Earth, Mars,      # Rocks
                        Jupiter, Saturn, Uranus, Neptune, # Gas
                        Pluto ]                           # Overrated
    '''
    DEFAULT = None
    '''Let YAML decide.'''

    BLOCK = False
    '''Use block style for sequences.'''

    FLOW = True
    '''Use flow style for sequences.'''


# -----------------------------------------------------------------------------
# YAML Large String Dumpers
# -----------------------------------------------------------------------------

class FoldedString(UserString):
    '''
    Class just marks this string to be dumped in 'folded' YAML string format.
    '''

    def __init__(self, value: str) -> None:
        super().__init__(value.strip())


class LiteralString(UserString):
    '''
    Class just marks this string to be dumped in 'literal' YAML string format.
    '''

    def __init__(self, value: str) -> None:
        super().__init__(value.strip())


def folded_string_representer(dumper: yaml.Dumper,
                              data:   Union[FoldedString, str]
                              ) -> yaml.ScalarNode:
    '''
    Register FoldedString as the correct style of literal.
    '''
    return dumper.represent_scalar(u'tag:yaml.org,2002:str',
                                   str(data),
                                   style='>')


def literal_string_representer(dumper: yaml.Dumper,
                               data:   Union[LiteralString, str]
                               ) -> yaml.ScalarNode:
    '''
    Register FoldedString as the correct style of literal.
    '''
    return dumper.represent_scalar(u'tag:yaml.org,2002:str',
                                   str(data),
                                   style='|')


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
# Dump/Load with some default args.
# -----------------------------------------------------------------------------

def safe_dump(data:             Any,
              stream:           TextIO,
              default_scalar:   ScalarStyle   = ScalarStyle.DEFAULT,
              default_sequence: SequenceStyle = SequenceStyle.DEFAULT,
              indent:           Optional[int] = None,
              width:            Optional[int] = None) -> None:
    '''
    Call `yaml.safe_dump()` with these args and/or some defaults.

    If `indent` is None, uses yaml default.

    If `width` is None, uses yaml default (which is sort of
    'no width restriction').
    '''
    yaml.safe_dump(data,
                   stream=stream,
                   default_style=default_scalar.value,
                   default_flow_style=default_sequence.value,
                   indent=indent,
                   width=width,
                   # Just using yaml defaults right now [2021-03-03].
                   encoding=None,  # utf-8 in Python 3
                   explicit_start=None,
                   explicit_end=None,
                   version=None,
                   tags=None,
                   canonical=None,
                   allow_unicode=None,
                   line_break=None)


def safe_dump_all(data:             Any,
                  stream:           TextIO,
                  default_scalar:   ScalarStyle   = ScalarStyle.DEFAULT,
                  default_sequence: SequenceStyle = SequenceStyle.DEFAULT,
                  indent:           Optional[int] = None,
                  width:            Optional[int] = None) -> None:
    '''
    Call `yaml.safe_dump_all()` with these args and/or some defaults.

    If `indent` is None, uses yaml default.

    If `width` is None, uses yaml default (which is sort of
    'no width restriction').
    '''
    yaml.safe_dump_all(data,
                       stream=stream,
                       default_style=default_scalar.value,
                       default_flow_style=default_sequence.value,
                       indent=indent,
                       width=width,
                       # Just using yaml defaults right now [2021-03-03].
                       encoding=None,  # utf-8 in Python 3
                       explicit_start=None,
                       explicit_end=None,
                       version=None,
                       tags=None,
                       canonical=None,
                       allow_unicode=None,
                       line_break=None)


def safe_load(stream: TextIO) -> Any:
    '''
    Call `yaml.safe_load()` with the stream of data and returns the parsed
    Python object.
    '''
    data = yaml.safe_load(stream)
    return data


def safe_load_all(stream: TextIO) -> Any:
    '''
    Call `yaml.safe_load_all()` with the stream of data and returns the parsed
    Python object.
    '''
    data = yaml.safe_load_all(stream)
    return data


# -----------------------------------------------------------------------------
# Automatically set up when imported.
# -----------------------------------------------------------------------------

representers()
constructors()
