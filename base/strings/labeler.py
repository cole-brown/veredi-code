# coding: utf-8

'''
Decoration helper for labels.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, Type, Callable, Set


from veredi.logs import log

from .label import _DOTTED_NAME, LabelInput, normalize


# -------------------------------------------------------------------------
# Variables
# -------------------------------------------------------------------------

KLASS_FUNC_NAME: str = _DOTTED_NAME
'''
If at class level, and a function instead of a property... still call it
'dotted', for consistency.
'''

ATTRIBUTE_PRIVATE_NAME: str = '_DOTTED'
'''
Try to call your attribute/property 'dotted', for consistency.

If you use 'register', your class will get a 'dotted' property for free.
'''

# -------------------------------------------------------------------------
# Variables
# -------------------------------------------------------------------------

_DOTTED_FUNC_IGNORE: Set = set()
'''
Set of classes/functions to ignore if asked to make 'dotted' functions for.
'''


# -------------------------------------------------------------------------
# Decorator Functions
# -------------------------------------------------------------------------

# A lil' decorator factory to take our args and make the decorator...
def dotted(*dotted_label: LabelInput) -> Callable[..., Type[Any]]:
    '''
    Property for adding a `dotted()` function and/or `_DOTTED` attribute to a
    class.

    Calling this `tag` so it doesn't conflict with all our 'label' and 'dotted'
    names. It "tags" something with a veredi dotted label...

    e.g.:
      @tag('veredi', 'example', 'example-one')
      class ExampleOne:
        pass

      @tag('veredi', 'example', 'ExampleTwo')
      class ExampleTwo:
        pass
    '''

    # Now make the actual decorator...
    def label_decorator(
            cls_or_func: Union[Type[Any], Callable[..., Type[Any]]]
    ) -> Type[Any]:  # noqa E123
        '''
        Decorates class with `_DOTTED` attribute and `dotted()` function.
        '''
        dotted_helper('veredi.base.strings.labeler.dotted',
                      '@dotted',
                      cls_or_func, dotted_label)
        return cls_or_func

    return label_decorator


# -------------------------------------------------------------------------
# Labelling-Related
# -------------------------------------------------------------------------

def ignore(parent_class: Type) -> None:
    '''
    Add a parent class to the ignore list for log warnings about
    add_dotted_func()'s auto-magical creation of the 'dotted' func.

    e.g. System base class has to do this for its children.
    '''
    _DOTTED_FUNC_IGNORE.add(parent_class)


def has_dotted(klass: Type, const: bool, func: bool) -> bool:
    '''
    Returns True if `klass` has a dotted constant and/or accessor.

    If `const` is True, checks for ATTRIBUTE_PRIVATE_NAME. Returns False if
    `klass` does not have it.

    If `func` is True, checks for KLASS_FUNC_NAME. Returns False if
    `klass` does not have it.

    Otherwise returns True.
    '''
    # Assume true unless false. This can cause a 'false alarm' if
    # labeler.has_dotted(Jeff, False, False) is called for some reason, but
    # we'll allow it.
    has_const = True
    has_func = True
    if const:
        has_const = hasattr(klass, ATTRIBUTE_PRIVATE_NAME)
    if func:
        has_func = hasattr(klass, KLASS_FUNC_NAME)

    return has_const or has_func


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def dotted_helper(caller_label: LabelInput,
                  provider_str: str,
                  cls_or_func:  Union[Type[Any], Callable[..., Type[Any]]],
                  dotted_label: LabelInput) -> Type[Any]:
    '''
    Tag `cls_or_func` with a dotted `label`.

    Does nothing for functions - allows functions to be more useful to
    registries.

    Gives classes:
      - a `_DOTTED` attribute string (via `_add_dotted_value()`)
      - a `dotted(klass) -> str` function (via `_add_dotted_func()`)
    '''
    dotted = normalize(dotted_label)

    _add_dotted_value(cls_or_func, dotted)
    _add_dotted_func(caller_label, provider_str, cls_or_func, dotted)


def _add_dotted_value(
        cls_or_func:  Union[Type[Any], Callable[..., Type[Any]]],
        dotted_label: LabelInput) -> None:
    '''
    Add an attribute for the `dotted_label` of the `cls_or_func`.

    Allows but ignores functions.
    '''
    # Ignore things that aren't a class.
    if not isinstance(cls_or_func, type):
        return

    dotted = normalize(dotted_label)
    # Set the 'private'(-ish) attribute with the class's dotted name value.
    setattr(cls_or_func, ATTRIBUTE_PRIVATE_NAME, dotted)


def _add_dotted_func(
        caller_label: LabelInput,
        provider_str: str,
        cls_or_func:  Union[Type[Any], Callable[..., Type[Any]]],
        add_label:    LabelInput) -> None:
    '''
    Add a getter for the dotted name of registering classes. Getter returns
    Optional[str].

    Allows but ignores functions.

    `caller_label` and `provider_str` are used for error messages.
    For example, "config.registry.register()" function could provide:
      caller_label='veredi.data.config.registry',
      provider_str='@register',
    '''
    caller_dotted = normalize(caller_label)
    add_dotted = normalize(add_label)

    # Ignore things that aren't a class.
    if not isinstance(cls_or_func, type):
        return

    # ---
    # Set the attribute with the class's dotted name value.
    # ---
    setattr(cls_or_func, ATTRIBUTE_PRIVATE_NAME, add_dotted)

    # ---
    # Check the dotted func now.
    # ---

    # Ignore things that already have the attribute we want to add. But do
    # not ignore if they are abstract - we will replace with concrete in
    # that case.
    dotted_attr = getattr(cls_or_func, KLASS_FUNC_NAME, None)
    if dotted_attr:
        # Pre-existing dotted attribute; is it abstract?
        if getattr(dotted_attr, '__isabstractmethod__', False):
            msg = (f"{caller_dotted}: Failed to add function "
                   f"'{KLASS_FUNC_NAME}' to '{add_dotted}'. "
                   f"{cls_or_func.__name__} has an abstract "
                   "'{KLASS_FUNC_NAME}' attribute, which we cannot "
                   "auto-generate a replacement for. Please implement "
                   "one manually:\n"
                   "    @classmethod\n"
                   "    def dotted(klass: 'YOURKLASS') -> str:\n"
                   f"        # _DOTTED magically provided by {provider_str}\n"
                   "        return klass._DOTTED")
            raise log.exception(AttributeError(msg, cls_or_func),
                                None,
                                msg)

        elif isinstance(cls_or_func, tuple(_DOTTED_FUNC_IGNORE)):
            # This is fine, but let 'em know. They could've let it be
            # auto-magically created.
            msg = (f"{provider_str}: {cls_or_func.__name__} has a "
                   f"'{KLASS_FUNC_NAME}' attribute already. "
                   f"{provider_str}(...) can implement one "
                   "automatically though; your "
                   f"'{KLASS_FUNC_NAME}' attribute would "
                   f"be: '{add_dotted}'")
            log.warning(msg)
            return

    # ---
    # Make Getter.
    # ---
    def get_dotted(klass: Type[Any]) -> Optional[str]:
        return getattr(klass, ATTRIBUTE_PRIVATE_NAME, None)

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
    setattr(cls_or_func, KLASS_FUNC_NAME, method)
