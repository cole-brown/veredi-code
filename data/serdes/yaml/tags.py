# coding: utf-8

'''
YAML library subclasses for encoding identities.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Type, Tuple


from veredi.logs            import log
from veredi.base.exceptions import RegistryError


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def valid(tag: str) -> Tuple[bool, Optional[str]]:
    '''
    Sanity check for tag string.

    Returns:
      bool - True/False for passed valid checks.
      str  -
    '''
    if not tag.startswith('!'):
        return (False, "Missing starting '!'.")
    return (True, None)


def make(string: str) -> str:
    '''
    Slaps a '!' onto `string` then checks that that tag isn't already
    registered. Throws if it is.
    Returns the tag string created.
    '''
    tag = string
    if not string.startswith('!'):
        tag = '!' + string

    success, reason = valid(tag)
    if not success:
        raise log.exception(RegistryError,
                            "Invalid tag! {reason}"
                            f"Tag: '{tag}'")
    return tag
