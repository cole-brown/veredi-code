# coding: utf-8

'''
Bit of a Factory thing going on here...
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Type, Any, Callable
from veredi.base.null import Nullable
from ..background import ContextMap

from veredi.logger import log
from .. import background
from .. import exceptions
from veredi.base.context import VerediContext

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# Registry is here, but also toss the reg strs into the background context.
_REGISTRY = {}


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# Decorator way of doing factory registration. Note that we will only get
# classes/funcs that are imported, when they are imported. We don't know about
# any that are sitting around waiting to be imported. If needed, we can fix
# that by importing things in their folder's __init__.py.

# First, a lil' decorator factory to take our args and make the decorator...
def register(*args: str) -> Callable[..., Type[Any]]:
    '''
    Property for registering a class or function with the registry.

    e.g. for a class:
      @register('veredi', 'example', 'example-class')
      class Example:
        pass

    e.g. for a function:
      @register('veredi', 'example', 'function')
      def example(arg0, arg1, **kwargs):
        pass
    '''

    # Now make the actual decorator...
    def register_decorator(
            cls_or_func: Union[Type[Any], Callable[..., Type[Any]]]
            ) -> Type[Any]:  # noqa E123
        # Pull final key off of list so we don't make too many dictionaries.
        name = str(cls_or_func)
        try:
            config_name = args[-1]
        except IndexError as error:
            raise log.exception(
                error,
                exceptions.RegistyError,
                "Need to know what to register this ({}) as. "
                "E.g. @register('foo', 'bar'). Got no args: {}",
                name, args,
                stacklevel=3)

        registration = _REGISTRY
        reggie_jr = background.registry.get()
        length = len(args)
        # -1 as we've got our config name already from that final args entry
        for i in range(length - 1):
            registration = registration.setdefault(args[i], {})
            rj_def = {} if i < (length - 2) else []
            reggie_jr = reggie_jr.setdefault(args[i], rj_def)

        # Helpful messages - but registering either way.
        if config_name in registration:
            log.warning("Something was already registered under this "
                        "registration key... keys: {}, replacing "
                        "'{}' with this '{}'",
                        args,
                        str(registration[config_name]),
                        name,
                        stacklevel=3)
        else:
            log.debug("Registered: keys: {}, value '{}'",
                      args,
                      name,
                      stacklevel=3)
        # Set as registered cls/func.
        registration[config_name] = cls_or_func
        # Save as a thing that has been registered at this level.
        reggie_jr.append(config_name)

        return cls_or_func

    return register_decorator


def get(dotted_keys_str: str,
        context: Optional[VerediContext],
        # Leave (k)args for others.
        *args: Any,
        **kwargs: Any) -> Union[Type, Callable]:
    '''
    Returns a registered class/func from the dot-separated keys (e.g.
    "repository.player.file-tree"), passing it args and kwargs.

    Context just used for errors/exceptions.
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
                exceptions.RegistryError,
                "Registry has nothing at: {}",
                split_keys[: i + 1]) from error

        i += 1

    if isinstance(registration, dict):
        raise log.exception(
            None,
            exceptions.RegistryError,
            "Registry for '{}' is not at a leaf - still has entries to go: {}",
            dotted_keys_str,
            registration)

    return registration


def create(dotted_keys_str: str,
           context: Optional[VerediContext],
           # Leave (k)args for others.
           *args: Any,
           **kwargs: Any) -> Any:
    '''
    Create a registered class from the dot-separated keys (e.g.
    "repository.player.file-tree"), passing it args and kwargs.
    '''
    entry = get(dotted_keys_str, context)

    try:
        # Leave (k)args for others.
        return entry(context, *args, **kwargs)
    except TypeError as error:
        # NOTE: Something to the tune of:
        #    TypeError: __init__() got multiple values for argument...
        # Probably means your *args are too long, or an arg got swapped in
        # the entry().
        # e.g.:
        #   args: (001,)
        #   kwargs: {'data': {...}}
        #   entry -> JeffCls.__init__(data, id, extra=None)
        #     - This dies cuz data was set to '001', then kwargs also
        #       had a 'data'.
        raise log.exception(
            error,
            exceptions.ConfigError,
            # Leave (k)args for others.
            "Registry failed creating '{}' with: args: {}, "
            "kwargs: {},  context: {}",
            entry, args, kwargs, context) from error
