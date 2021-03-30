# coding: utf-8

'''
Base Repository Pattern for load, save, etc. from
various backend implementations (db, file, etc).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Callable, Tuple

import pathlib
import re
import hashlib


from ..strings                   import label, text
from .                           import const, utils


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# ---
# Path Safing Consts
# ---

_HUMAN_SAFE = re.compile(r'[^\w\d_.-]')
_REPLACEMENT = '_'


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def default() -> Tuple[Callable, label.DotStr]:
    '''
    Returns the default path-safing function and its Dotted String label.
    '''
    return to_human_readable, 'veredi.paths.sanitize.human'


# --------------------------------------------------------------------------
# Path Safing Option:
#   "us?#:er" -> "us___er"
# --------------------------------------------------------------------------
def to_human_readable(*part: const.PathType) -> pathlib.Path:
    '''
    Sanitize each part of the path by converting illegal characters to safe
    characters.

    "/" is illegal.

    So ensure that the safe portion of the paths is split if providing a full
    path.
    '''
    sanitized = []
    try:
        first = True
        for each in part:
            # First part can be a root, in which case we can't sanitize it.
            if first:
                check = utils.cast(each)
                # Must be a path.
                if (isinstance(check, pathlib.Path)
                        # Must be absolute.
                        and check.is_absolute()
                        # Must be /only/ the root.
                        and len(check.parts) == 1):
                    # Ok; root can be used as-is.
                    sanitized.append(check)

                # Not a root; sanitize it.
                else:
                    sanitized.append(_part_to_human_readable(each))

            # All non-first parts get sanitized.
            else:
                sanitized.append(_part_to_human_readable(each))
            first = False

    except TypeError as error:
        wrapper = TypeError("to_human_readable: Cannot sanitize path!", part)
        raise wrapper from error

    return utils.cast(*sanitized)


def _part_to_human_readable(part: const.PathType) -> str:
    '''
    Sanitize a single part of the path by converting illegal characters to safe
    characters.

    "/" is illegal.
    '''
    try:
        # Normalize our string first.
        normalized = text.normalize(part)
        # Then ensure part is a string before doing the regex replace.
        humanized = _HUMAN_SAFE.sub(_REPLACEMENT, normalized)
    except TypeError as error:
        wrapper = TypeError(
            "_part_to_human_readable: Cannot sanitize path part!",
            part
        )
        raise wrapper from error
    return humanized


# --------------------------------------------------------------------------
# Path Safing Option:
#   "us?#:er" ->
#     'b3b31a87f6cca2e4d8e7909395c4b4fd0a5ee73b739b54eb3aeff962697ca603'
# --------------------------------------------------------------------------
def to_hashed(*part: const.PathType) -> pathlib.Path:
    '''
    Sanitize each part of the path by converting it to a hash string.

    So ensure that all directories in the path are split if providing a full
    path.
    '''
    sanitized = []
    try:
        first = True
        for each in part:
            # First part can be a root, in which case we can't sanitize it.
            if first:
                check = utils.cast(each)
                # Must be a path.
                if (isinstance(check, pathlib.Path)
                        # Must be absolute.
                        and check.is_absolute()
                        # Must be /only/ the root.
                        and len(check.parts) == 1):
                    # Ok; root can be used as-is.
                    sanitized.append(check)

                # Not a root; sanitize it.
                else:
                    sanitized.append(_part_to_hashed(each))

            # All non-first parts get sanitized.
            else:
                sanitized.append(_part_to_hashed(each))

    except TypeError as error:
        wrapper = TypeError(
            "to_hashed: Cannot sanitize path!",
            part
        )
        raise wrapper from error

    return utils.cast(*sanitized)


def _part_to_hashed(part: const.PathType) -> str:
    '''
    Sanitize each part of the path by converting it to a hash.
    '''
    try:
        # Ensure part is a string, encode to bytes, and hash those.
        hashed = hashlib.sha256(str(part).encode()).hexdigest()
    except TypeError as error:
        wrapper = TypeError(
            "_part_to_hashed: Cannot sanitize part!",
            part
        )
        raise wrapper from error
    return hashed
