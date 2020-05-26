# coding: utf-8

'''
Helper for unit test data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import pathlib

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

THIS_DIR = pathlib.Path(__file__).resolve().parent


# -----------------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------------

def data_path(*relative):
    '''Returns absolute path to a file given its path rooted from this file's
    directory.

    Returns None if file does not exist.

    '''
    path = THIS_DIR.joinpath(*relative)
    if not path.exists():
        return None

    return path
