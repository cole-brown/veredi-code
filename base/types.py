# coding: utf-8

'''
Helpers for type info, type checking, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, Type


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def is_class(check: Any) -> bool:
    '''
    Is `check` a class type?

    Returns True for a class type, False for not.
      - NOTE: Returns False for a class /instance/. Checks for a /type/.
    '''
    return (isinstance(check, type)
            and issubclass(check, object))


def is_subclass(check: Any, parent: Type) -> bool:
    '''
    Is `check` a class type?

    Returns True if:
      - `check` is a class type.
      - `parent` is a class type.
      - `check` is either `parent` or a subclass of it.

    NOTE: Returns False for class /instances/. Checks for /types/.
    '''
    return (is_class(parent)
            and is_class(check)
            and issubclass(check, parent))


def is_function(check: Any) -> bool:
    '''
    Is `check` a function?

    Returns True for a callable that is not a class; False otherwise.
    '''
    return (not is_class(check)
            and callable(check))
