# coding: utf-8

'''
Pretty printing utilities for Veredi. Most likely used for logging, so they're
in the logger module.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import pprint
import textwrap

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# ------------------------------
# TextWrap
# ------------------------------
_TW_MAX_STR_WIDTH = 70
'''
Max width of the output lines of a str passed to indented. Note: non-strs
use pprint instead of textwrap so currently [2020-11-08] they don't obey this.
'''


_TW_EXPAND_TABS = True
'''
Whether textwrap calls here will translate tabs to spaces.
'''


_TW_TAB_WIDTH = 4
'''
Number of spaces to use when _EXPAND_TABS is True.
'''


_TW_REPLACE_WHITESPACE = False
'''
Whether whitespace ('\t\n\v\f\r') will be replaced by a single whitespace
character during textwrap calls.
'''


_TW_DROP_WHITESPACE = False
'''
If true, whitespace at the beginning and ending of every line (after
wrapping but before indenting) is dropped.
'''


# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

__initialized = False


wrapper = None
'''
Our instance of a textwrap object for formatting strings input into our funcs.
'''


# -----------------------------------------------------------------------------
# Initialization
# -----------------------------------------------------------------------------

def init() -> None:
    '''
    Initializes pretty stuff like our textwrapper instance.
    '''
    # ------------------------------
    # No Re-Init.
    # ------------------------------
    global __initialized
    if __initialized:
        return

    # ------------------------------
    # TextWrapper
    # ------------------------------
    global wrapper
    wrapper = textwrap.TextWrapper(
        width=_TW_MAX_STR_WIDTH,
        expand_tabs=_TW_EXPAND_TABS,
        tabsize=_TW_TAB_WIDTH,
        replace_whitespace=_TW_REPLACE_WHITESPACE,
        drop_whitespace=_TW_DROP_WHITESPACE,
        # initial_indent=...,
        # subsequent_indent=...,
        # fix_sentence_endings=...,
        # break_long_words=...,
        # break_on_hyphens=...,
        # max_lines=...,
        # placeholder=...,
    )


# -----------------------------------------------------------------------------
# Prettification
# -----------------------------------------------------------------------------

def to_str(data, sort=True):
    '''
    Tries to pretty print data. Returns a string.
    '''
    return pprint.pformat(data, sort_dicts=sort)


def indented(obj, indent_amount=2, sort=True, max_width=None):
    '''
    pprint.pformat(obj), then indents string by indent number of spaces.
    '''
    obj_str = None
    # Don't use pprint on a string... it just returns an escaped string in a
    # stringified tuple, which is just... weird.
    if isinstance(obj, str):
        width = None
        if max_width != wrapper.width:
            width = wrapper.width
        # Do wrapping inside try so we can always reset width.
        try:
            obj_str = wrapper.fill(obj)
            # Don't need/want to handle any exception, just want to reset
            # width in `finally` block.

        finally:
            if width is not None:
                wrapper.width = width

    # Something that isn't a string - have pprint deal with it.
    # And have dicts sorted by key name unless `sort` set to False.
    else:
        obj_str = pprint.pformat(obj, sort_dicts=sort)

    lines = []
    indent = ' ' * indent_amount
    for each in obj_str.splitlines():
        lines.append(indent + each)
    return '\n'.join(lines)


def sq(arg):
    '''
    Wrap str(`arg`) in single quotes and return.
    '''
    return "'" + str(arg) + "'"


def dq(arg):
    '''
    Wrap str(`arg`) in double quotes and return.
    '''
    return '"' + str(arg) + '"'


# -----------------------------------------------------------------------------
# Module Setup
# -----------------------------------------------------------------------------

if not __initialized:
    init()
