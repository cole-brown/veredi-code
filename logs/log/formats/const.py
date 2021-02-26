# coding: utf-8

'''
Constants for Formatters and Handlers.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_STYLE = '{'


# https://docs.python.org/3/library/logging.html#logrecord-attributes
_FMT_LINE_HUMAN = (
    '{asctime:s} - {name:s} - {levelname:8s} - '
    '{module:s}.{funcName:s}{message:s}'
)
'''
Having no space between Python logging variables and `message` will allow
for nicer formatting of e.g. GROUP logging.
'''
