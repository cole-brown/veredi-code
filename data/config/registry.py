# coding: utf-8

'''
Bit of a Factory thing going on here...
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Type, Any, Callable


from veredi.logs         import log
from ..                  import background
from ..exceptions        import RegistryError, ConfigError
from veredi.base.strings import label
from veredi.base.strings import labeler
from veredi.base.context import VerediContext


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# Registry is here, but also toss the reg strs into the background context.
_REGISTRY = {}
_REG_DOTTED = 'veredi.data.config.registry'
_REG_DOT_SHORT = 'config.registry'


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def ignore(parent_class: Type) -> None:
    '''
    Add a parent class to the ignore list for log warnings about register() and
    labeler.add_dotted_func()'s auto-magical creation of the 'dotted' func.

    e.g. System base class has to do this for its children.
    '''
    return labeler.ignore(parent_class)


# Decorator way of doing factory registration. Note that we will only get
# classes/funcs that are imported, when they are imported. We don't know about
# any that are sitting around waiting to be imported. If needed, we can fix
# that by importing things in their folder's __init__.py.

# First, a lil' decorator factory to take our args and make the decorator...
def register(*dotted_label: label.LabelInput) -> Callable[..., Type[Any]]:
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
    registree_id = label.regularize(*dotted_label)

    # Now make the actual decorator...
    def register_decorator(
            cls_or_func: Union[Type[Any], Callable[..., Type[Any]]]
            ) -> Type[Any]:  # noqa E123
        # Pull final key off of list so we don't make too many dictionaries.
        name = str(cls_or_func)
        try:
            leaf_key = registree_id[-1]
        except IndexError as error:
            raise log.exception(
                RegistryError,
                "Need to know what to register this ({}) as. "
                "E.g. @register('veredi', 'jeff', 'system'). "
                "Got no label?: {}",
                name, registree_id,
                stacklevel=3) from error

        registry_our = _REGISTRY
        registry_bg = background.registry.registry(_REG_DOTTED)
        length = len(registree_id)
        # -1 as we've got our config name already from that final registree_id
        # entry.
        for i in range(length - 1):
            registry_our = registry_our.setdefault(registree_id[i], {})
            registry_bg = registry_bg.setdefault(registree_id[i], {})

        # Helpful messages - but registering either way.
        if leaf_key in registry_our:
            log.warning("Something was already registered under this "
                        "registration key... keys: {}, replacing "
                        "'{}' with this '{}'",
                        registree_id,
                        str(registry_our[leaf_key]),
                        name,
                        stacklevel=3)
        else:
            log.debug("Registered: keys: {}, value '{}'",
                      registree_id,
                      name,
                      stacklevel=3)
        # Set as registered cls/func.
        registry_our[leaf_key] = cls_or_func
        # Save as a thing that has been registered at this level.
        registry_bg.setdefault('.', []).append(leaf_key)

        # Finally, add the 'dotted' property if applicable.
        labeler.dotted_helper(_REG_DOTTED, '@register',
                              cls_or_func, registree_id)

        return cls_or_func

    return register_decorator


def get(dotted_keys: label.LabelInput,
        context:     Optional[VerediContext],
        # Leave (k)args for others.
        *args:       Any,
        **kwargs:    Any) -> Union[Type, Callable]:
    '''
    Returns a registered class/func from the dot-separated keys (e.g.
    "repository.player.file-tree"), passing it args and kwargs.

    Context just used for errors/exceptions.
    '''
    registration = _REGISTRY
    split_keys = label.regularize(dotted_keys)
    i = 0
    for key in split_keys:
        if registration is None:
            break
        # This can throw the KeyError if nothing registered...
        try:
            registration = registration[key]
        except KeyError as error:
            raise log.exception(
                RegistryError,
                "{} has nothing at: '{}' (full path: {})",
                _REG_DOT_SHORT,
                label.normalize(split_keys[: i + 1]),
                split_keys) from error

        i += 1

    if isinstance(registration, dict):
        raise log.exception(
            RegistryError,
            "{} for '{}' is not at a leaf - still has entries to go: {}",
            _REG_DOT_SHORT,
            label.normalize(split_keys),
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
            ConfigError,
            # Leave (k)args for others.
            "{} failed creating '{}' with: args: {}, "
            "kwargs: {},  context: {}",
            _REG_DOT_SHORT,
            entry, args, kwargs, context) from error


# -----------------------------------------------------------------------------
# Unit Testing
# -----------------------------------------------------------------------------

def _ut_unregister() -> None:
    '''
    Looks like we don't need to do anything. Well, more like: we have to leave
    registered right now or tests will fail because nothing is registered.
    '''
    # '''
    # Nuke everything from the register; reset it completely.
    # '''
    # global _REGISTRY
    # _REGISTRY = {}
    pass
