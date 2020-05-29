# coding: utf-8

'''
Helper for unit test data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, Optional
import pathlib

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

THIS_DIR = pathlib.Path(__file__).resolve().parent


# -----------------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------------

def retval(path: pathlib.Path) -> Optional[pathlib.Path]:
    '''Returns path if it exists or None if not.'''
    if not path.exists():
        return None
    return path


def rooted(*relative: Union[pathlib.Path, str]) -> Optional[pathlib.Path]:
    '''Returns absolute path to a file given its path rooted from this file's
    directory.

    Returns None if file does not exist.

    Return value is a pathlib.Path.
    '''
    return retval(THIS_DIR.joinpath(*relative))

# ------------------------------------------------------------------------------
# Codecs
# ------------------------------------------------------------------------------

def codec() -> Optional[pathlib.Path]:
    '''
    Returns pathlib.Path to codec test data.
    '''
    return retval(rooted('codec'))


# ------------------------------------------------------------------------------
# Repositories
# ------------------------------------------------------------------------------

def repository() -> Optional[pathlib.Path]:
    '''
    Returns pathlib.Path to repository test data.
    '''
    return retval(rooted('repository'))


def repository_file_tree() -> Optional[pathlib.Path]:
    '''
    Returns pathlib.Path to FileTreeRepository test data.
    '''
    return retval(rooted('repository', 'file-tree'))


# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

def config(filepath: Union[pathlib.Path, str, None]) -> Optional[pathlib.Path]:
    '''
    Returns pathlib.Path to config test data.
    '''
    path = retval(rooted('config'))
    if not filepath:
        return path
    path = path / filepath
    return retval(path)
