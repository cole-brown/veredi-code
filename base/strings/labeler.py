# coding: utf-8

'''
Decoration helper for labels.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, Type, Callable, Set


from veredi.logs import log

from .label import DOTTED_NAME, LabelInput, normalize
from .mixin import DottedDescriptor


# -------------------------------------------------------------------------
# Variables
# -------------------------------------------------------------------------

DESCRIPTOR_NAME: str = DOTTED_NAME
'''
Try to call your descriptor 'dotted', for consistency.
'''


KLASS_FUNC_NAME: str = DOTTED_NAME
'''
If at class level, and a function instead of a descriptor... still call it
'dotted', for consistency.
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
    Property for adding a `dotted` DottedDescriptor to a class.
    '''

    # Now make the actual decorator...
    def label_decorator(
            cls_or_func: Union[Type[Any], Callable[..., Type[Any]]]
    ) -> Type[Any]:  # noqa E123
        '''
        Decorates class with `dotted` descriptor.
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


def has_dotted(klass: Type) -> bool:
    '''
    Returns True if `klass` has a DOTTED_NAME, DESCRIPTOR_NAME, or
    KLASS_FUNC_NAME attribute already.

    Can cause a false positive if e.g. `labeler.has_dotted(Jeff, False, False)`
    is called for some reason, so... Don't do that.

    Otherwise returns False.
    '''
    # Assume true unless false. This can cause a false positive if
    # labeler.has_dotted(Jeff, False, False) is called for some reason, but
    # we'll allow it. Don't be stupid please.
    return (hasattr(klass, DOTTED_NAME)
            or hasattr(klass, DESCRIPTOR_NAME)
            or hasattr(klass, KLASS_FUNC_NAME))


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
      - a `dotted` DottedDescriptor (via `_add_dotted_value()`)
    '''
    dotted = normalize(dotted_label)

    _add_dotted_descriptor(caller_label, provider_str,
                           cls_or_func, dotted)


def _add_dotted_descriptor(
        caller_label: LabelInput,
        provider_str: str,
        cls_or_func:  Union[Type[Any], Callable[..., Type[Any]]],
        add_label:    LabelInput) -> None:
    '''
    Add a DottedDescriptor for the dotted name of this classes.

    Allows but ignores functions.

    `caller_label` and `provider_str` are used for error messages.
    For example, "config.registry.register_this()" function could provide:
      caller_label='veredi.data.config.registry',
      provider_str='@register_this',
    '''
    if not isinstance(cls_or_func, type):
        return

    # ---
    # Set the descriptor with the class's dotted name value.
    # ---
    caller_dotted = normalize(caller_label)
    descriptor = DottedDescriptor(add_label, DESCRIPTOR_NAME)
    if not hasattr(cls_or_func, DESCRIPTOR_NAME):
        setattr(cls_or_func, DESCRIPTOR_NAME, descriptor)
    else:
        add_dotted = normalize(add_label)
        msg = (f"{caller_dotted}->{provider_str}: Failed to add descriptor "
               f"'{DESCRIPTOR_NAME}' to '{add_dotted}'. "
               f"{cls_or_func.__name__} has an atttribute by that "
               "name alerady.")
        # Changed into an info log... If it has a dotted already then why do we
        # care, really...
        log.info(msg)
        # raise log.exception(AttributeError(msg, cls_or_func),
        #                     msg)
