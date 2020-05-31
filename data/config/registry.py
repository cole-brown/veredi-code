# coding: utf-8

'''
Bit of a Factory thing going on here...
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Callable, Type, Any
import functools

from veredi.logger import log
from .. import exceptions

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_REGISTRY = {}

# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


# Decorator way of doing factory registration. Note that we will only get
# classes that are imported, when they are imported. We don't know about any
# that are sitting around waiting to be imported. If needed, we can fix that by
# importing things in their folder's __init__.py.

# First, a lil' decorator factory to take our args and make the decorator...
def register(*args: str) -> Callable[..., Type[Any]]:
    # Now make the actual class decorator...
    def register_decorator(cls: Type[Any]) -> Type[Any]:
        # Pull final key off of list so we don't make too many dictionaries.
        try:
            config_name = args[-1]
        except IndexError:
            log.warning("Need to know what to register this ({}) as. "
                        "E.g. @register('foo', 'bar'). Got no args: {}",
                        cls.__name__, args,
                        stacklevel=3)
            raise

        registration = _REGISTRY
        length = len(args)
        # -1 as we've got our config name already from that final args entry
        for i in range(length - 1):
            registration = registration.setdefault(args[i], {})

        # Helpful messages - but registering either way.
        if config_name in registration:
            log.warning("Something was already registered under this "
                        "registration key... keys: {}, replacing "
                        "'{}' with this '{}'",
                        args,
                        str(registration[config_name]),
                        str(cls),
                        stacklevel=3)
        else:
            log.debug("Registered: keys: {}, class '{}'",
                        args,
                        str(cls),  # cls.__name__,
                        stacklevel=3)
        registration[config_name] = cls

        return cls

    return register_decorator


def create(dotted_keys_str: str,
           *args: Any,
           **kwargs: Any):
    '''Create a registered class from the dot-separated keys (e.g.
    "repository.player.file-tree"), passing it args and kwargs.

    '''
    registration = _REGISTRY
    split_keys = dotted_keys_str.split('.')
    i = 0
    for key in split_keys:
        if registration is None:
            break
        # This can throw the KeyError...
        try:
            registration = registration[key]
        except KeyError as error:
            raise log.exception(
                error,
                exceptions.ConfigError,
                "Registry has nothing at: {}",
                split_keys[ : i + 1 ]) from error

        i += 1

    try:
        return registration(*args, **kwargs)
    except TypeError as error:
        raise log.exception(
            error,
            exceptions.ConfigError,
            "Registry failed creating '{}' with: args: {}, kwargs: {}",
            registration, args, kwargs) from error
