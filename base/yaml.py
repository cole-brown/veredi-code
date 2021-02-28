# coding: utf-8

'''
Custom YAML Formatter for:
  - Logging
  - Serialization/Deserialiazition (Serdes).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, Mapping


import yaml
from collections import OrderedDict


# Logging needs this stuff for YAML formatted logs, so do not log from here.
# from veredi.logs               import log


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


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
# Register representers with YAML.
# -----------------------------------------------------------------------------

def representers() -> None:
    '''
    Reentrant: Add additional representers needed to YAML.
    '''
    yaml.add_representer(FoldedString,
                         folded_string_representer,
                         Dumper=yaml.SafeDumper)
    yaml.add_representer(LiteralString,
                         literal_string_representer,
                         Dumper=yaml.SafeDumper)
    yaml.add_representer(OrderedDict,
                         ordered_dict_representer,
                         Dumper=yaml.SafeDumper)


# -----------------------------------------------------------------------------
# Automatically set up when imported.
# -----------------------------------------------------------------------------

representers()
