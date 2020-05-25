# coding: utf-8

'''
Helper for unit test data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import os

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


# -----------------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------------

def data_path(*relative):
    '''Returns absolute path to a file given its path rooted from this file's
    directory.

    Returns None if file does not exist.

    '''
    path = os.path.join(THIS_DIR, *relative)
    if not os.path.exists(path):
        return None

    return path
