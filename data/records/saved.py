# coding: utf-8

'''
A class for loading a saved data record.

Record can have multiple documents, like 'metadata' and 'definition.system'.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from .record       import Record


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Mappings
# -----------------------------------------------------------------------------

class Saved(Record):
    '''
    Collection of saved data documents - characters, items, game data whatever.
    '''

    # Currently just a Record, but will diverge once it's used more.
    ...
