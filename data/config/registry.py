# coding: utf-8

'''
Bit of a Factory thing going on here...
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
import functools

# Framework

# Our Stuff
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
def register(*args):
    # Now make the actual class decorator...
    def register_decorator(cls):
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


def create(dotted_keys_str, *args, **kwargs):
    '''Create a registered class from the dot-separated keys (e.g.
    "repository.player.file-tree"), passing it args and kwargs.

    '''
    try:
        registration = _REGISTRY
        for key in dotted_keys_str.split('.'):
            if registration is None:
                break
            # This can throw the KeyError...
            registration = registration[key]

        # TODO: Check for if this is callable?
        return registration(*args, **kwargs)

    except KeyError as error:
        raise exceptions.ConfigError(
                f"Registry has nothing under the keys: {dotted_keys_str}",
                error,
                {'keys': dotted_keys_str}) from error
