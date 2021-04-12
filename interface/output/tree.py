# coding: utf-8

'''
Translator from MathTrees to output.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, Type, Mapping, MutableMapping
from veredi.base.null import Nullable

import copy

from veredi.math.parser import MathTree, NodeType


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class MathOutputTree:
    '''
    Transform a MathTree node into something ready for encoding for final
    output to client(s).
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # NULL_SIGN = '\u2205'
    # NULL_SIGN = '\N{EMPTY SET}'
    NULL_SIGN = '∅'

    # ---
    # Template Fields
    # ---
    T_TYPE = 'type'
    T_MONIKER = 'moniker'
    T_VALUE = 'value'
    T_CHILD = 'children'

    # ---
    # Templates
    # ---
    TEMPLATE_LEAF = {T_TYPE: None,
                     T_MONIKER: None,
                     T_VALUE: None}

    TEMPLATE_BRANCH = {T_TYPE: None,
                       T_MONIKER: None,
                       T_VALUE: None,
                       T_CHILD: None}

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def _get_template(klass: Type['MathOutputTree'],
                      node:  MathTree) -> Optional[Mapping[str, Any]]:
        '''
        Get a copy of the correct template for this node's type.

        Returns the dictionary template if it finds one.
        Returns None for NodeType.INVALID.
        Raises ValueError otherwies.
        '''
        if node.type.has(NodeType.LEAF):
            return copy.copy(klass.TEMPLATE_LEAF)

        if node.type.has(NodeType.BRANCH):
            return copy.copy(klass.TEMPLATE_BRANCH)

        if node.type.has(NodeType.INVALID):
            return None

        raise ValueError(f"No template for NodeType: {node.type}", node)

    @classmethod
    def _convert(klass: Type['MathOutputTree'],
                 node:  MathTree) -> Optional[Mapping[str, Any]]:
        '''
        Get a (shallow) copy of the correct template for this node's type, fill
        in these values and returns the data:
          type, moniker, value
        '''
        if node.type == NodeType.INVALID:
            return None

        type_name = None
        if node.type.has(NodeType.FUNCTION):
            type_name = 'function'
        elif node.type.has(NodeType.OPERATOR):
            type_name = 'operator'
        elif node.type.has(NodeType.RANDOM):
            type_name = 'random'
        elif node.type.has(NodeType.VARIABLE):
            type_name = 'variable'
        elif node.type.has(NodeType.CONSTANT):
            type_name = 'constant'

        data = klass._get_template(node)
        data[klass.T_TYPE] = type_name.lower()
        data[klass.T_MONIKER] = str(node.moniker)
        data[klass.T_VALUE] = node.value
        return data

    # -------------------------------------------------------------------------
    # API
    # -------------------------------------------------------------------------

    @classmethod
    def to_map(klass: Type['MathOutputTree'],
               root:  MathTree) -> Nullable[Mapping[str, Any]]:
        '''
        Walk MathTree, extracting each node's output values.
        '''

        output = {}
        for node in root.walk():
            data = klass._convert(node)
            if data:
                output[id(node)] = data
            if node.type.has(NodeType.BRANCH):
                klass._add_children(node, data, output)

        return output[id(root)]

    @classmethod
    def _add_children(klass:     Type['MathOutputTree'],
                      node:      MathTree,
                      data:      MutableMapping[str, str],
                      converted: MutableMapping[str, str]) -> None:
        '''
        Add already-`converted` children of this `node` to its
        conversion `data`.

        Inserts into `data` dict so no return.
        Raises AttributeError if node has no 'children' attribute.
        Raises ValueError if wrong node type or unknown child.
        '''
        if not node.children:
            raise ValueError(
                f"NodeType.BRANCH node has no children: {node}", node)

        data[klass.T_CHILD] = []
        for child in node.children:
            # Do we have this child in converted?
            kid = converted.get(id(child), None)
            if not kid:
                raise ValueError(
                    f"Node has a child that didn't get converted? {node}",
                    node, child, id(child), converted)
            data[klass.T_CHILD].append(kid)
