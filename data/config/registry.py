# coding: utf-8

'''
Bit of a Factory thing going on here...
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Type, Any, Callable

from veredi.logger import log
from .. import background
from .. import exceptions
from veredi.base import label
from veredi.base.context import VerediContext

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# Registry is here, but also toss the reg strs into the background context.
_REGISTRY = {}
_REG_DOTTED = 'veredi.data.config.registry'

_DOTTED_FUNC_IGNORE = set()


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def ignore(parent_class: Type) -> None:
    '''
    Add a parent class to the ignore list for log warnings about
    add_dotted_func()'s auto-magical creation of the 'dotted' func.

    e.g. System base class has to do this for its children.
    '''
    _DOTTED_FUNC_IGNORE.add(parent_class)


def add_dotted_value(cls_or_func: Union[Type[Any], Callable[..., Type[Any]]],
                     dotted_name: str) -> None:
    '''
    Add an attribute for the dotted name of registering classes.

    Ignore registering functions.
    '''
    # Ignore things that aren't a class.
    if not isinstance(cls_or_func, type):
        return

    # If it already has the label._KLASS_FUNC_NAME, and doesn't have the
    # label._ATTRIBUTE_PRIVATE_NAME, we'll give it the
    # _ATTRIBUTE_PRIVATE_NAME. We have an annoying case of not knowing enough
    # Python to magically shenanigan our way out of an '@abstractfunc', so e.g.
    # System base class declares 'dotted' as one and the systems that register
    # still have to declare their own but I'd like to at least auto-fill their
    # dotted names in for them.

    # So, basically... Add the _ATTRIBUTE_PRIVATE_NAME regardless. *shrug*

    # ---
    # Set the attribute with the class's dotted name value.
    # ---
    setattr(cls_or_func, label._ATTRIBUTE_PRIVATE_NAME, dotted_name)


def add_dotted_func(
        cls_or_func: Union[Type[Any], Callable[..., Type[Any]]],
        dotted_name: str) -> None:
    '''
    Add a getter for the dotted name of registering classes. Getter returns
    Optional[str].

    Ignore registering functions.
    '''
    # Ignore things that aren't a class.
    if not isinstance(cls_or_func, type):
        return

    # ---
    # Set the attribute with the class's dotted name value.
    # ---
    setattr(cls_or_func, label._ATTRIBUTE_PRIVATE_NAME, dotted_name)

    # ---
    # Check the dotted func now.
    # ---

    # Ignore things that already have the attribute we want to add. But do not
    # ignore if they are abstract - we will replace with concrete in that case.
    dotted_attr = getattr(cls_or_func, label._KLASS_FUNC_NAME, None)
    if dotted_attr:
        # Pre-existing dotted attribute; is it abstract?
        if getattr(dotted_attr, '__isabstractmethod__', False):
            msg = (f"{_REG_DOTTED}: Failed '{dotted_name}' registry of "
                   f"{cls_or_func.__name__} has an abstract "
                   "'{label._KLASS_FUNC_NAME}' attribute, which we cannot "
                   "auto-generate a replacement for. Please implement "
                   "one manually:\n"
                   "    @classmethod\n"
                   "    def dotted(klass: 'YOURKLASS') -> str:\n"
                   "        # klass._DOTTED magically provided by @register\n"
                   "        return klass._DOTTED")
            raise log.exception(AttributeError(msg, cls_or_func),
                                None,
                                msg)
        elif isinstance(cls_or_func, tuple(_DOTTED_FUNC_IGNORE)):
            # This is fine, but let 'em know. They could've let it be
            # auto-magically created.
            msg = (f"{_REG_DOTTED}: {cls_or_func.__name__} "
                   f"has a '{dotted._KLASS_FUNC_NAME}' attribute already. "
                   "@register(...) can implement one automatically though; "
                   f"your '{label._KLASS_FUNC_NAME}' attribute would be: "
                   f"'{dotted_name}'")
            log.info(msg)
            return

    # ---
    # Make Getter.
    # ---
    def get_dotted(klass: Type[Any]) -> Optional[str]:
        return getattr(klass, label._ATTRIBUTE_PRIVATE_NAME, None)

    # ---
    # No Setter.
    # ---
    # def set_dotted(self, value):
    #     return setattr(self, '_dotted', value)

    # prop = property(get_dotted, set_dotted)

    # ---
    # Set the getter @classmethod function.
    # ---
    method = classmethod(get_dotted)
    setattr(cls_or_func, label._KLASS_FUNC_NAME, method)


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
                exceptions.RegistryError,
                "Need to know what to register this ({}) as. "
                "E.g. @register('veredi', 'jeff', 'system'). Got no args: {}",
                name, args,
                stacklevel=3)

        registration = _REGISTRY
        reggie_jr = background.registry.get(_REG_DOTTED)
        length = len(args)
        # -1 as we've got our config name already from that final args entry
        for i in range(length - 1):
            registration = registration.setdefault(args[i], {})
            reggie_jr = reggie_jr.setdefault(args[i], {})

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
        reggie_jr.setdefault('.', []).append(config_name)

        # Finally, add the 'dotted' property if applicable.
        dotted_name = label.join(*args)
        add_dotted_value(cls_or_func, dotted_name)
        add_dotted_func(cls_or_func, dotted_name)

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
    split_keys = label.split(dotted_keys_str)
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
                "Registry has nothing at: {} (full path: {})",
                split_keys[: i + 1],
                split_keys) from error

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
