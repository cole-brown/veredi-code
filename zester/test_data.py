# coding: utf-8

'''
Test Data helper/util functions.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
import os

# Framework

# Our Stuff


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def abs_path(*rel):
    '''Returns absolute path to a file given its path rooted from this file's
    directory (that is, it should probably start with 'data').

    Returns None if file does not exist.

    '''
    path = os.path.join(THIS_DIR, *rel)
    if not os.path.exists(path):
        return None

    return path
