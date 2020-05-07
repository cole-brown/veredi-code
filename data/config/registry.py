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

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_REGISTRY = {}

# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


# Decorator way of doing it...
# First, a lil' decorator factory to take our args and make the decorator...
def register(*args):
    print(f'register: {args}')
    def register_decorator(cls):
        print(f'register_decorator: {cls}')
        # pull final key off of list so we
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
