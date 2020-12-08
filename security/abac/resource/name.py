# coding: utf-8

'''
Module for dealing with Attribute-based Access Control resource names.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Type, Mapping

import enum
import re

from veredi.logger               import log
from veredi.data.codec.encodable import Encodable


# -----------------------------------------------------------------------------
# Regex
# -----------------------------------------------------------------------------

_NAME_FLAGS = re.IGNORECASE
'''
Don't care about case because we force all lowercase in the end.
'''

_NAME_LENGTH_MIN = 1
'''Name must be at least 3 characters. Less will result in an error.'''

_NAME_LENGTH_MAX = 60
'''Name can only be this long, max. Longer will get truncated or errored.'''

_NAME_VALID_STR = (
    # Start of string.
    r'^'

    # ---
    # Allowed Characters:
    # ---

    # Start the group.
    # And start it with hyphen to put that in a spot where it means
    # 'hyphen allowed' rather than 'range of characters marker'.
    r'[-'

    # Rest of the Punctuation Allowed:
    r'._/'

    # All unicode letters are allowed.
    # NOTE!: If we need to restrict, we can OR the re.ASCII flag into
    # _NAME_FLAGS for a-z only.
    r'\w'

    # All digits allowed too.
    r'\d'

    # End the group.
    r']'

    # Min/max sizes.
    r'{'
    f'{_NAME_LENGTH_MIN},{_NAME_LENGTH_MAX}'
    r'}'

    # End of string.
    r'$')
'''
Regex for parsing human time duration strings.
'''

_NAME_VALID_REGEX = re.compile(_NAME_VALID_STR,
                               _NAME_FLAGS)
'''
Regex for validating VRN 'name' fields.
'''


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_SEPERATOR = ':'
'''
Seperator character between fields of the Veredi Resource Name.
'''


_VERSION_CURR = '2020-10-18'
_VERSIONS = (
    _VERSION_CURR,
)
'''
Version string, in case format string has to change or something like that.
'''

_FORMAT = (
    'vrn:'
    '{version}:'
    '{dotted}:'
    '{owner_id}:'
    '{type}:'
    '{name}'
)
'''
Format of a Veredi Resource Name
'''

# ------------------------------
# Misc
# ------------------------------

_ENCODE_FIELD_NAME = 'name'
'''
For encoding a Veredi Resoure Name:
  {'name': 'vrn:2020-10-18:veredi.jeff:9888aeournh:uh...:idk-yet...'}
'''


# -----------------------------------------------------------------------------
# Veredi Resource Type
# -----------------------------------------------------------------------------

@enum.unique
class ResourceType(enum.Enum):
    '''
    Resource Types for our Attribute-Based Access Control.
    '''

    # ------------------------------
    # This is not a type:
    # ------------------------------

    INVALID = None
    '''No one is allowed to use this. Definitely an error...'''

    # ------------------------------
    # Generic
    # ------------------------------

    RESOURCE = 'resource'

    # ------------------------------
    # Specific
    # ------------------------------

    # IDK. None for now?

    def __str__(self) -> str:
        '''
        Convert the ResourceType enum instance/const to a string value.

        Lowercases the string before returning.
        '''
        if self.value is None or not isinstance(self.value, str):
            msg = ("ResourceTypes with a value of None or non-string are "
                   f"not allowed. Got: '{self.value}'")
            err = ValueError(msg, self)
            raise log.exception(err, msg)

        return str(self.value).lower()


# -----------------------------------------------------------------------------
# Veredi Resource Name
# -----------------------------------------------------------------------------

def make(dotted: str,
         # TODO: 'encodable as short str w/ restrictions' subclass instead of
         # 'Encodable'?
         owner_id: Union[str, Encodable],
         type:     Union[str, ResourceType],
         name:     str) -> str:
    '''
    Builds a VRN (Veredi Resource Name) out of the supplied parameters and
    returns it.
    '''
    return _FORMAT.format({
        'version': _VERSION_CURR,
        'dotted':  dotted.lower(),
        'owner_id': _make_owner(owner_id),
        'name':  _make_name(name),
    })


def _make_owner(owner_id: Union[str, Encodable]) -> str:
    '''
    Builds a VRN (Veredi Resource Name) 'owner_id' field string value from the
    input `owner_id`.

    Returns lowercase string.
    Raises ValueError if input is not of the correct types.
    '''
    # ---
    # Parse owner to str.
    # ---
    owner_str = None
    if isinstance(owner_id, str):
        owner_str = owner_id.lower()

    elif isinstance(owner_id, Encodable):
        owner_str = owner_id.encode(None)

    else:
        msg = ("Cannot make a VRN owner string from an owner_id "
               f"value of: '{owner_id}'.")
        err = ValueError(msg, owner_id)
        raise log.exception(err, msg)

    # ---
    # Validate owner.
    # ---
    # Use same regex as name for now. Change to using its own if needed.
    if not _NAME_VALID_REGEX.match(owner_str):
        msg = ("OwnerId failed validation. "
               f"'{owner_str}' (from '{owner_id}') did not match the regex:"
               f"'{_NAME_VALID_STR}'")
        err = ValueError(msg, owner_str, owner_id)
        raise log.exception(err, msg)

    # ---
    # Lowercase before returning.
    # ---
    return owner_str.lower()


def _make_name(name: str) -> str:
    '''
    Builds a VRN (Veredi Resource Name) 'name' field string value from the
    input `name`.

    `name` is validate by the _NAME_VALID_REGEX.

    Returns lowercase string.
    Raises ValueError if input is not of the correct types.
    '''
    # ---
    # Parse name to str.
    # ---
    name_str = None
    if isinstance(name, str):
        name_str = name.lower()

    elif isinstance(name, Encodable):
        name_str = name.encode_str()

    else:
        msg = ("Cannot make a VRN name string from a"
               f"value of: '{name}'.")
        err = ValueError(msg, name)
        raise log.exception(err, msg)

    # ---
    # Validate name.
    # ---
    if not _NAME_VALID_REGEX.match(name_str):
        msg = ("Name failed validation. "
               f"'{name}' did not match the regex:"
               f"'{_NAME_VALID_STR}'")
        err = ValueError(msg, name)
        raise log.exception(err, msg)

    # ---
    # Lowercase before returning.
    # ---
    return name_str.lower()
