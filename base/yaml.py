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
                    Callable, TextIO, Mapping, Dict)


import yaml
from collections import OrderedDict, UserString
import enum
import re

# Yaml's Error type to propogate up to our import level.
from yaml import YAMLError

# Logging needs this stuff for YAML formatted logs, so do not log from here.
# from veredi.logs               import log

from .exceptions import RegistryError


# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

_REPRESENTING: Dict[str, str] = {}
'''
A dictionary of classes already registered for representing and where
they came from.
'''


_CONSTRUCTING: Dict[str, str] = {}
'''
A dictionary of classes already registered for constructing and where
they came from.
'''


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
# Regex support in YAML.
# -----------------------------------------------------------------------------
# Because... what could possibly go wrong?

# ------------------------------
# Constructor == Reader
# ------------------------------

def regex_constructor(loader: yaml.SafeLoader,
                      node:   yaml.nodes.Node) -> re.Pattern:
    '''
    Returns the regex pattern.
    '''
    value = loader.construct_scalar(node)
    return re.compile(value)


# ------------------------------
# Representer == Writer
# ------------------------------

def regex_representer(dumper: yaml.SafeDumper,
                      regex:  re.Pattern) -> yaml.nodes.Node:
    '''
    Returns a string for the regex pattern.
    '''
    if isinstance(regex, re.Pattern):
        regex = regex.pattern
    return dumper.represent_scalar('!regex', regex)


# -----------------------------------------------------------------------------
# YAML Large String Dumpers
# -----------------------------------------------------------------------------

class FoldedString(UserString):
    '''
    Class just marks this string to be dumped in 'folded' YAML string format.
    '''

    def __init__(self, value: str, line_rstrip: bool = True) -> None:
        # Strip out whitespace to force YAML to obey our LiteralString style...
        # >.<
        if line_rstrip:
            lines = value.split('\n')
            for i in range(len(lines)):
                lines[i] = lines[i].rstrip()
            value = '\n'.join(lines)
        else:
            value = value.strip()

        super().__init__(value)


class LiteralString(UserString):
    '''
    Class just marks this string to be dumped in 'literal' YAML string format.
    '''

    def __init__(self, value: str, line_rstrip: bool = True) -> None:
        # Strip out whitespace to force YAML to obey our LiteralString style...
        # >.<
        if line_rstrip:
            lines = value.split('\n')
            for i in range(len(lines)):
                lines[i] = lines[i].rstrip()
            value = '\n'.join(lines)
        else:
            value = value.strip()

        super().__init__(value)


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


def enum_representer(enum_type: Type[enum.Enum] = None) -> YamlRepresenter:
    '''
    Get the correct representer function for the enum's value type.

    NOTE: Does not support multi-type enums like, oh, say... String value enums
    with an 'IGNORE = None' value in them.

    If we don't have a representer for that specific kind of value, raises an
    error.
    '''
    # Find a value to use for figuring out which enum representer to use for
    # this enum_type.
    value = None
    for each in enum_type:
        if each.value is not None:
            # Just use the first non-None as the value type of all of this
            # enum's values. We don't support multi-type enums, like the NOTE
            # says in the docstr.
            value = each.value
            break

    if isinstance(value, int):
        return enum_int_representer

    if isinstance(value, str):
        return enum_string_value_representer

    raise TypeError(f"No representer for {enum_type} with value "
                    f"type {type(value)}.",
                    enum_type,
                    value)


# -----------------------------------------------------------------------------
# Register representers with YAML.
# -----------------------------------------------------------------------------

def represent(klass:    Type,
              function: YamlRepresenter,
              file:     str) -> None:
    '''
    Add a representer to YAML.
    '''
    # ------------------------------
    # Make sure it's unique?
    # ------------------------------
    # NOTE: Not exactly necessary - yaml will register/use multiple classes of
    # the same name, however we want to ensure uniqueness because tags will
    # probably closely follow names?
    # But if this is too restrictive, we can just drop it.
    klass_name = str(klass)
    if klass_name in _REPRESENTING:
        blocker_file = _REPRESENTING[klass_name]
        raise RegistryError(f"{klass_name} already has representer; "
                            "one of you will need a rename...",
                            data={
                                'represent-this': klass,
                                'represent-with': function,
                                'represent-from': file,
                                'blocked-by': klass_name,
                                'blocked-from': blocker_file,
                            })

    # ------------------------------
    # Ok; we can add it.
    # ------------------------------
    _REPRESENTING[str(klass)] = file
    yaml.add_representer(klass,
                         function,
                         Dumper=yaml.SafeDumper)


def representers() -> None:
    '''
    Add additional, common, basic representers needed to YAML.
    '''
    represent(FoldedString,
              folded_string_representer,
              __file__)
    represent(LiteralString,
              literal_string_representer,
              __file__)
    represent(OrderedDict,
              ordered_dict_representer,
              __file__)
    represent(re.Pattern,
              regex_representer,
              __file__)


# -----------------------------------------------------------------------------
# Register constructors with YAML.
# -----------------------------------------------------------------------------

def construct(tag: str,
              function: YamlConstructor,
              file: str) -> None:
    '''
    Add a constructor to YAML.
    '''
    # Make sure it's unique...
    if tag in _CONSTRUCTING:
        blocker_file = _CONSTRUCTING[tag]
        raise RegistryError(f"{tag} already has constructor; ",
                            "one of you will need a rename...",
                            data={
                                'construct-this': tag,
                                'construct-with': function,
                                'construct-from': file,
                                'blocked-by': tag,
                                'blocked-from': blocker_file,
                            })
    # Ok; we can add it.
    _CONSTRUCTING[tag] = file
    yaml.add_constructor(tag,
                         function,
                         Loader=yaml.SafeLoader)


def constructors() -> None:
    '''
    Add additional, common, basic constructors needed to YAML.
    '''
    construct('!regex',
              regex_constructor,
              __file__)


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
