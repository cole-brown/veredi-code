# coding: utf-8

'''
Pretty printing utilities for Veredi. Most likely used for logging, so they're
in the logger module.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import pprint


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# Logging / Output Help
# ------------------------------------------------------------------------------

def to_str(data):
    '''
    Tries to pretty print data. Returns a string.
    '''
    return pprint.pformat(data)


def indented(obj, indent_amount=2):
    '''
    pprint.pformat(obj), then indents string by indent number of spaces.
    '''
    obj_str = pprint.pformat(obj)
    lines = []
    indent = ' ' * indent_amount
    for each in obj_str.splitlines():
        lines.append(indent + each)
    return '\n'.join(lines)
