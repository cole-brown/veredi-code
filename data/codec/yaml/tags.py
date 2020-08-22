# coding: utf-8

'''
YAML library subclasses for encoding identities.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Type

from veredi.logger import log
from ...exceptions import RegistryError

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def valid(tag: str) -> bool:
    '''
    Sanity check for tag string.
    '''
    return tag.startswith('!')


def make(string: str) -> str:
    '''
    Slaps a '!' onto `string` then checks that that tag isn't already
    registered. Throws if it is.
    Returns the tag string created.
    '''
    tag = string
    if not string.startswith('!'):
        tag = '!' + string

    if not valid(tag):
        raise log.exception(None,
                            RegistryError,
                            "Invalid tag! Already registered maybe? "
                            f"Tag: {tag}, registered to?: "
                            f"{get_class(tag)}")
    return tag
