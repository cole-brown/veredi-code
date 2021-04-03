# coding: utf-8

'''
Mixin class for a few string/label functions.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, Type, Callable
from ..null import Null


from . import label
from veredi.logs import log


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class DottedDescriptor:
    '''
    Veredi label.DotStr provided via descriptor - usually named `dotted`.
    '''

    def __init__(self,
                 *dotted: Optional[label.LabelInput],
                 name_descriptor: str = None) -> None:
        self.name: str = name_descriptor
        # Could be initialized to None so that it gets its name, then used
        # later to transfer name to actual DottedDescriptor when a dotted input
        # is procured (see DottedMixin class).
        self.dotted: label.DotStr = label.normalize(*dotted, empty_ok=True)

    def __get__(self,
                instance: Optional[Any],
                owner:    Type[Any]) -> label.DotStr:
        '''
        Returns the dotted label value.
        '''
        return self.dotted

    def __set__(self,
                instance: Optional[Any],
                dotted:   Optional[label.LabelInput]) -> None:
        '''
        Setter should not be used during normal operation...
        Dotted labels should not change.
        '''
        self.dotted = label.normalize(dotted, empty_ok=False)

    def __set_name__(self, owner: Type[Any], name: str) -> None:
        '''
        Save our descriptor variable's name in its owner's class.
        '''
        self.name = name


class StringDescriptor:
    '''
    A constant read-only string provided via descriptor - for e.g. `name`,
    `klass`.
    '''

    def __init__(self,
                 value: str,
                 transform: Optional[Callable[[str], str]],
                 name_descriptor: str = None) -> None:
        self.name: str = name_descriptor
        self.value: str = None

        # lower case? UPPER CASE? SaRcAsM CaSe?
        if transform:
            self.value = transform(value)
        else:
            self.value = value

    def __get__(self,
                instance: Optional[Any],
                owner:    Type[Any]) -> label.DotStr:
        '''
        Returns the string value.
        '''
        return self.value

    def __set__(self,
                instance: Optional[Any],
                value:    Optional[str]) -> None:
        '''
        Set the string value.
        '''
        self.value = value

    def __set_name__(self, owner: Type[Any], name: str) -> None:
        '''
        Save our descriptor variable's name in its owner's class.
        '''
        self.name = name


class ClassDescriptor(StringDescriptor):
    '''
    A constant read-only string provided via descriptor. Is either
    automatically set to the name of the class, or set to the value provided if
    something else is desired.
    '''

    def __init__(self,
                 auto:      bool,
                 value:     Optional[str],
                 transform: Optional[Callable[[str], str]],
                 name_descriptor: str = None) -> None:
        '''
        NOTE: Need to init in the class level if using auto-generated name!

        /Cannot/ do something like this:

        class Jeff:
            klass: ClassDescriptor = Null()
            def __init_subclass__(klass, ...):
                if name_klass:
                    klass.klass = ClassDescriptor(True, None, None)

        Instead must do something like this:

        class Jeff:
            # Set-up auto-init in actual klass vars.
            klass: ClassDescriptor = ClassDescriptor(True, None, None)

            # OR manually init somewhere else.
            def __init_subclass__(klass,
                                  name_klass=None,
                                  name_klass_xform=None,
                                  ...):
                if name_klass:
                    klass.klass = ClassDescriptor(False,
                                                   name_klass,
                                                   name_klass_xform)
        '''
        if not auto and not value:
            raise ValueError(
                "ClassDescriptor: "
                "Need a value provided if not auto-generating one!",
                auto, value, transform)

        self.transform: Optional[Callable[[str], str]] = None
        if auto:
            # Need to save transform in case value isn't provided here and we
            # auto-fill in `__set_name__()`.
            self.transform = transform

        # Finish w/ StringDescriptor's init. Want to run it after all our stuff
        # since it may or may not be setting a value in our case.
        super().__init__(value, transform, name_descriptor)


    def __set__(self,
                instance: Optional[Any],
                value:    Optional[str]) -> None:
        '''
        Setter should not be used during normal operation...
        Klass names should not change.
        '''
        # Could maybe have some check here...
        # Like only set if currently None/Null?
        super().__set__(instance, value)

    def __set_name__(self, owner: Type[Any], name: str) -> None:
        super().__set_name__(owner, name)

        # Automatically set class name if not provided in init
        if not self.value:
            if self.transform:
                self.value = self.transform(owner.__name__)
            else:
                self.value = owner.__name__


class DottedMixin:
    '''
    Veredi label.DotStr read-only class-level descriptor.
    '''

    dotted: DottedDescriptor = DottedDescriptor(None)
    '''
    A short-hand name for the class, if desired.
    '''

    def __init_subclass__(
            klass:             Type[Any],
            name_dotted:       Optional[label.LabelInput] = None,
            **kwargs:          Any) -> None:
        '''
        Initialize the dotted descriptor if provided.
        '''
        # Pass up to parent.
        super().__init_subclass__(**kwargs)

        if name_dotted:
            klass.dotted = name_dotted


class NamesMixin(DottedMixin):
    '''
    Veredi dotted, name, and klass read-only class-level descriptors.
    '''

    name: StringDescriptor = StringDescriptor(None, None)
    '''
    A short-hand name for the class, if desired.
    '''

    klass: ClassDescriptor = None
    '''
    A short-cut to 'self.__class__.__name__', or it can hold some other class
    related name string.
    '''

    def __init_subclass__(
            klass:             Type[Any],
            name_dotted:       Optional[label.LabelInput]     = None,
            name_string:       Optional[str]                  = None,
            name_klass:        Optional[str]                  = None,
            name_string_xform: Optional[Callable[[str], str]] = None,
            name_klass_xform:  Optional[Callable[[str], str]] = None,
            **kwargs:          Any) -> None:
        '''
        Initialize any of the descriptors we get values for.

        The `name_xxx_xform` params are if a caller is providing some existing
        string but wants it e.g. lowercased.

        Leave the rest as Null().
        '''
        # Pass up to parent.
        super().__init_subclass__(name_dotted=name_dotted,
                                  **kwargs)

        # Create the name/klass short-hand if provided.
        if name_string:
            if name_string_xform:
                klass.name = name_string_xform(name_string)
            else:
                klass.name = name_string

        # Initialize the ClassDescriptor now. If initialized in class vars like
        # StringDescriptor and DottedDescriptor, it won't be able to
        # auto-generate its owmner class name because its owner is technically
        # this - NamesMixin.
        if name_klass:
            klass.klass = ClassDescriptor(False,
                                          name_klass,
                                          name_klass_xform)
        else:
            # "Auto"-generate class name. If using directly in a class, you can
            # just init in class consts/vars like this:
            #     klass: ClassDescriptor = ClassDescriptor(True, None, None)
            # But we're in a mixin so:
            klass.klass = ClassDescriptor(False,
                                          klass.__name__,
                                          name_klass_xform)
