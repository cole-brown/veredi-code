# coding: utf-8

'''
YAML library subclasses for encoding outputs.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Tuple

import yaml

from veredi.logger                  import log
from veredi.interface.output.event  import OutputEvent
from veredi.math.event              import MathOutputEvent

from veredi.base.null               import null_to_none
from veredi.interface.input.context import InputContext
from veredi.interface.output.tree   import MathOutputTree


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Represent: OutputEvent
# -----------------------------------------------------------------------------

def event_title(event: OutputEvent) -> Tuple[str, str]:
    '''
    Gives the title of the event.
    '''
    return ('title',
            {
                'name':    null_to_none(event.title),
                'caption': null_to_none(event.subtitle),
            })


def event_input(event: OutputEvent) -> Tuple[str, str]:
    '''
    Gives the input of the event.
    '''
    return ('input', null_to_none(InputContext.input(event.context)))


def event_id(event: OutputEvent) -> Tuple[str, str]:
    '''
    Gives the input id of the event.
    '''
    return ('id', null_to_none(event.serial_id.encode()))


def event_type(event: OutputEvent) -> Tuple[str, str]:
    '''
    Gives the dotted type of the event.
    '''
    return ('type', null_to_none(event.dotted))


def event_names(event: OutputEvent) -> Tuple[str, str]:
    '''
    Gives the display names of... anything that needs a display name in the
    OutputEvent.
    '''
    return ('names',
            null_to_none(event.designations))


# -----------------------------------------------------------------------------
# Represent: MathOutputEvent
# -----------------------------------------------------------------------------

def event_math(event: MathOutputEvent) -> Tuple[str, str]:
    '''
    Gives the math tree of the event.
    '''
    return ('output',
            null_to_none(MathOutputTree.to_map(event.root)))


def ordered_yield_math(event: MathOutputEvent) -> Tuple[str, str]:
    '''
    Yields out the data for a MathOutputEvent in order.
    '''
    yield event_title(event)
    yield event_input(event)

    yield event_id(event)
    yield event_type(event)
    yield event_math(event)

    yield event_names(event)


def output_math_representer(dumper: yaml.SafeDumper,
                            event: MathOutputEvent) -> yaml.nodes.Node:
    '''
    Dump out a representation of a MathOutputEvent.
    '''
    return dumper.represent_mapping('!effect.math',
                                    ordered_yield_math(event))


yaml.add_representer(MathOutputEvent,
                     output_math_representer,
                     Dumper=yaml.SafeDumper)
