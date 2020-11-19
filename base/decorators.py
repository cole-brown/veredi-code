# coding: utf-8

'''
Some general decorators for Veredi.
'''

# -----------------------------------------------------------------------------
# Notes
# -----------------------------------------------------------------------------
#
# ------------------------------
# Note-00: Ordering of @classmethod @abstractmethod:
# ------------------------------
#    @classmethod
#    @abstractmethod
#    def func(klass: 'KlassName', ...) -> ...:
#       ...
#
# ------------------------------
# Note-00:
# ------------------------------
#


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Type, Any, Callable


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# @classproperty decorator
# -----------------------------------------------------------------------------

# from:
#   https://gist.github.com/Skinner927/413c0e9cc8433123f426832f9fe8d931
#   Which is derived from: https://stackoverflow.com/a/5191224/721519

# Only needed if we want get and settable class properties.
# Leaving commented out until that is true:
#
# class ClassPropertyMeta(type):
#     '''
#     Using @classproperty will set that class's metaclass to this.
#     '''
#
#     def __setattr__(self, key, value):
#         obj = self.__dict__.get(key, None)
#         if type(obj) is classproperty:
#             return obj.__set__(self, value)
#         return super().__setattr__(key, value)

class classproperty(object):
    '''
    Similar to @property but used on classes instead of instances.

    The only caveat being that your class must use the
    classproperty.meta metaclass.
      NOTE [2020-08-25]: Currently not true - not using setter capability.

    Class properties will still work on class instances unless the class
    instance has overidden the class default. This is no different than how
    class instances normally work.

    # class Z(object, metaclass=classproperty.meta):
    class Z(object):
        _bar = None

        @classproperty
        def foo(cls):
            return 123

        @classproperty
        def bar(cls):
            return cls._bar

        # @bar.setter
        # def bar(cls, value):
        #     return cls_bar = value

    Z.foo  # 123
    Z.bar  # None
    # Z.bar = 222
    # Z.bar  # 222
    '''

    # meta = ClassPropertyMeta

    def __init__(self, fget, fset=None):
        self.fget = self._fix_function(fget)
        self.fset = None if fset is None else self._fix_function(fset)

    def __get__(self, instance, owner=None):
        # if not issubclass(type(owner), ClassPropertyMeta):
        #     raise TypeError(
        #         f"Class {owner} does not extend from the required "
        #         f"ClassPropertyMeta metaclass"
        #     )
        return self.fget.__get__(None, owner)()

    # def __set__(self, owner, value):
    #     if not self.fset:
    #         raise AttributeError("can't set attribute")
    #     if type(owner) is not ClassPropertyMeta:
    #         owner = type(owner)
    #     return self.fset.__get__(None, owner)(value)

    # def setter(self, fset):
    #     self.fset = self._fix_function(fset)
    #     return self

    _fn_types = (type(__init__), classmethod, staticmethod)

    @classmethod
    def _fix_function(cls, fn):
        if not isinstance(fn, cls._fn_types):
            raise TypeError("Getter or setter must be a function")

        # Always wrap in classmethod so we can call its __get__ and not
        # have to deal with difference between raw functions.
        if not isinstance(fn, (classmethod, staticmethod)):
            return classmethod(fn)

        return fn


# -----------------------------------------------------------------------------
# Abstract Class Property
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
