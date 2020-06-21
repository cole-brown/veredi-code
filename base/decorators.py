# coding: utf-8

'''
Some general decorators for Veredi.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Type, Any, Callable


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def abstract_class_attribute(*names: str) -> Callable[..., Type]:
    '''
    Each argument will be required from subclasses as an attribute.

    Original from [2020-06-19]:
      https://stackoverflow.com/questions/45248243/most-pythonic-way-to-declare-an-abstract-class-property
    '''

    def aca_decorator(klass: Type, *names: str) -> Type:
        '''
        This extends the __init_subclass__ method of the decorated class.

        Adds checks for each name we want as a required
        abstract class attribute.
        '''

        # Start each attribute off with the value of NotImplemented.
        for name in names:
            setattr(klass, name, NotImplemented)

        # Save the original __init_subclass__ implementation, then wrap
        # it with our new implementation.
        orig_init_subclass = klass.__init_subclass__

        def new_init_subclass(klass: Type, **kwargs: Any):
            '''
            New definition of __init_subclass__ that checks that
            attributes are implemented.
            '''

            # The default implementation of __init_subclass__ takes no
            # positional arguments, but a custom implementation does.
            # If the user has not reimplemented __init_subclass__ then
            # the first signature will fail and we try the second.
            try:
                orig_init_subclass(klass, **kwargs)
            except TypeError:
                orig_init_subclass(**kwargs)

            # Check that each required attribute is defined.
            for name in names:
                if getattr(klass, name, NotImplemented) is NotImplemented:
                    raise NotImplementedError(
                        "Abstract attribute/property still undefined: "
                        f"{name}")

        # Bind this new function to the __init_subclass__. We have to manually
        # declare it as a classmethod because it is not done automatically as
        # it would be if declared in the standard way.
        klass.__init_subclass__ = classmethod(new_init_subclass)

        return klass

    # And return a lambda call to our internal aca_decorator() with names
    # filled in.
    return lambda klass: aca_decorator(klass, *names)
