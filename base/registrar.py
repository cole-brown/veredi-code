# coding: utf-8

'''
Bit of a Factory thing going on here...
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (Optional, Union, Type, NewType, Any, Mapping,
                    Callable, Iterable, Dict)


from abc import ABC, abstractmethod


from veredi.base.strings    import label
from veredi.logger          import log
from veredi.data            import background
from veredi.data.exceptions import RegistryError

from .context               import VerediContext


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

RegisterType = NewType('RegisterType',
                       Union[Type[Any], Callable[..., Type[Any]]])
'''
Can register either a Type (class), or a Callable (function).
'''


# -----------------------------------------------------------------------------
# Registration Class
# -----------------------------------------------------------------------------

class BaseRegistrar(ABC):
    '''
    A class to hold registration data for whatever type of register you want.

    Don't sub-class this for specific registries; sub-class one of the
    sub-classes in this module.
    '''

    # -------------------------------------------------------------------------
    # Class Vars
    # -------------------------------------------------------------------------

    # Registry is here, but also toss the reg strs into the background context.
    _REGISTRY: Dict[str, Any] = None
    '''
    DO NOT ACCESS DIRECTLY! Use `_get()`.

    The registry for this registrar. Technically of type:
      Dict[str,
           Union['RegisterType',
                 Dict[str,
                      Union['RegisterType',
                            Dict[
                                 etc ad nauseum
                                ]
                           ]
                     ]
                ]
           ]
        - with leaves being 'RegisterType'.
    '''

    # -------------------------------------------------------------------------
    # Unit Testing Helpers
    # -------------------------------------------------------------------------
    @classmethod
    def nuke(klass: 'BaseRegistrar') -> None:
        '''
        Resets _REGISTRY to None, effectively deleting all registrations.
        '''
        klass._REGISTRY = None

    # -------------------------------------------------------------------------
    # Registry Internal Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def _get(klass: 'BaseRegistrar') -> Dict[str, Any]:
        '''
        Get the `klass._REGISTRY`. Create if it is None.
        '''
        if klass._REGISTRY is None:
            klass._REGISTRY = {}

        return klass._REGISTRY

    # -------------------------------------------------------------------------
    # Identification
    # -------------------------------------------------------------------------

    @classmethod
    @abstractmethod
    def dotted(klass: 'BaseRegistrar') -> str:
        '''
        Returns this registrar's dotted name.
        '''
        # return 'veredi.base.registrar'
        raise NotImplementedError(f"{klass.__name__}.dotted() is "
                                  "not implemented.")

    # -------------------------------------------------------------------------
    # Sub-Class Adjustable Registration
    # -------------------------------------------------------------------------

    @classmethod
    def _init_register(klass:      'BaseRegistrar',
                       registeree: 'RegisterType',
                       reg_args:   Iterable[str]) -> bool:
        '''
        This is called before anything happens in `register()`.

        Raise an error to fail the registration or return False to ignore it.
          - Note that it will be totally ignored. Log if you want to.

        `reg_args` is the Iterable of args passed into `register()`.

        Default implmentation: None. Just return True.
        '''
        return True

    @classmethod
    def _register(klass:       'BaseRegistrar',
                  registeree:  'RegisterType',
                  reg_label:    Iterable[str],
                  leaf_key:     str,
                  reg_ours:     Dict,
                  reg_bg:       Dict) -> None:
        '''
        Subclasses can override this if they want to register slightly
        differently. For example, if they want to register background data of
        more than just the dotted name.

        Default implementation:
          - register `registeree` to `reg_ours[leaf_key]`
          - register `leaf_key` to list at `reg_bg['.']`.

        `reg_args` is the Iterable of args passed into `register()`.
        `reg_ours` is the place in klass._REGISTRY we placed this registration.
        `reg_bg` is the place in the background we placed this registration.
        '''
        # Set as registered cls/func.
        reg_ours[leaf_key] = registeree

        # Save as a thing that has been registered at this level.
        reg_bg.setdefault('.', []).append(leaf_key)

    @classmethod
    def _finalize_register(klass:       'BaseRegistrar',
                           registeree: 'RegisterType',
                           reg_args:    Iterable[str],
                           reg_ours:    Dict,
                           reg_bg:      Dict) -> None:
        '''
        Subclasses can use this for any last steps they need to take.

        `reg_args` is the Iterable of args passed into `register()`.
        `reg_ours` is the place in klass._REGISTRY we placed this registration.
        `reg_bg` is the place in the background we placed this registration.
        '''
        ...

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    @classmethod
    def register(klass:         'BaseRegistrar',
                 cls_or_func:   'RegisterType',
                 *dotted_label: label.LabelInput) -> None:
        '''
        This function does the actual registration.
        '''
        # Do any initial steps.
        dotted_list = label.regularize(*dotted_label)
        if not klass._init_register(cls_or_func, dotted_list):
            # Totally ignore if not successful. _init_register() should do
            # all the erroring itself.
            return

        # Pull final key off of list so we don't make too many
        # dictionaries.
        name = str(cls_or_func)
        try:
            leaf_key = dotted_list[-1]
            '''Final key where the registration will actually be stored.'''
        except IndexError as error:
            kwargs = log.incr_stack_level(None)
            raise log.exception(
                RegistryError,
                "Need to know what to register this ({}) as. "
                "E.g. @register('jeff', 'geoff'). Got no dotted_list: {}",
                name, dotted_list,
                **kwargs) from error

        registration = klass._get()
        '''Our register - full info saved here.'''

        reggie_jr = background.registry.get(klass.dotted())
        '''Background register - just names saved here.'''

        # ------------------------------
        # Get reg dicts to the leaf.
        # ------------------------------

        length = len(dotted_list)
        # -1 as we've got our config name already from that final
        # dotted_list entry.
        for i in range(length - 1):
            # Walk down into both dicts, making new empty sub-entries as
            # necessary.
            registration = registration.setdefault(dotted_list[i], {})
            reggie_jr = reggie_jr.setdefault(dotted_list[i], {})

        # ------------------------------
        # Register (warn if occupied).
        # ------------------------------

        # Helpful messages - but registering either way.
        try:
            if leaf_key in registration:
                if background.testing.get_unit_testing():
                    log.ultra_hyper_debug(klass._get())
                    msg = ("Something was already registered under this "
                           f"registration key... keys: {dotted_list}, "
                           f"replacing {str(registration[leaf_key])}' with "
                           f"this '{name}'.")
                    error = KeyError(leaf_key, msg, cls_or_func)
                    log.exception(error, None, msg,
                                  stacklevel=3)
                else:
                    log.warning("Something was already registered under this "
                                "registration key... keys: {}, replacing "
                                "'{}' with this '{}'",
                                dotted_list,
                                str(registration[leaf_key]),
                                name,
                                stacklevel=3)
            else:
                log.debug("Registered: keys: {}, value '{}'",
                          dotted_list,
                          name,
                          stacklevel=3)
        except TypeError as error:
            msg = (f"{klass.__name__}.register(): Our 'registration' dict is "
                   "the incorrect type? Expected something that can deal "
                   f"with 'in' operator. Have: {type(registration)} -> "
                   f"{registration}. Trying to register {cls_or_func} at "
                   f"'{label.normalize(dotted_list)}'. "
                   "Registry: \n{}")
            from veredi.logger import pretty
            log.exception(error, msg,
                          pretty.indented(klass._REGISTRY))
            # Reraise it. Just want more info.
            raise

        # Register cls/func to our registry, save some info to our
        # background registry.
        klass._register(cls_or_func,
                        dotted_list,
                        leaf_key,
                        registration,
                        reggie_jr)

        # ------------------------------
        # Finalize (if desired).
        # ------------------------------
        klass._finalize_register(cls_or_func, dotted_list,
                                 registration, reggie_jr)

    # -------------------------------------------------------------------------
    # Registry Access
    # -------------------------------------------------------------------------

    @classmethod
    def get_dotted(klass:   'BaseRegistrar',
                   dotted:  label.LabelInput,
                   context: Optional[VerediContext]) -> 'RegisterType':
        '''
        Get by dotted name.

        Returns a registered class/func from the dot-separated keys (e.g.
        "repository.player.file-tree").

        Context just used for errors/exceptions.

        Raises:
          KeyError - dotted string not found in our registry.
        '''
        registration = klass._get()
        split_keys = label.regularize(dotted)

        # ---
        # Walk into our registry using the keys for our path.
        # ---
        i = 0
        for key in split_keys:
            if registration is None:
                break
            # This can throw the KeyError...
            try:
                registration = registration[key]
            except KeyError as error:
                raise log.exception(
                    RegistryError,
                    "Registry has nothing at: {} (full path: {})",
                    split_keys[: i + 1],
                    split_keys) from error
            i += 1

        # ---
        # Sanity Check - ended at leaf node?
        # ---
        if isinstance(registration, dict):
            raise log.exception(
                RegistryError,
                "Registry for '{}' is not at a leaf - "
                "still has entries to go: {}",
                label.normalize(dotted),
                registration)

        # Good; return the leaf value (a RegisterType).
        return registration

    @classmethod
    def get_from_data(klass:   'BaseRegistrar',
                      data:    Mapping[str, Any],
                      context: Optional[VerediContext]) -> 'RegisterType':
        '''
        Try to get a dotted name from the data, then pass to get_dotted().

        Returns a registered class/func from the dot-separated keys (e.g.
        "repository.player.file-tree").

        Context just used for errors/exceptions.

        Raises:
          KeyError - dotted string not found the data.
        '''
        dotted = data['dotted']
        return klass.get_dotted(dotted, context)

    @classmethod
    def invoke(klass: 'BaseRegistrar',
               dotted_keys_str: str,
               context: Optional[VerediContext],
               # Leave (k)args for others.
               *args: Any,
               **kwargs: Any) -> Any:
        '''
        Use our `get()` to get the registered RegisterType (or error out)
        at `dotted_keys_str`.

        Then use args, kwargs to call the RegisterType. Returns the result.

        Context just used for error info.
        '''
        entry = klass.get(dotted_keys_str, context)

        try:
            # Leave (k)args for others.
            return entry(context, *args, **kwargs)

        except TypeError as error:
            # NOTE: Something to the tune of:
            #    TypeError: __init__() got multiple values for argument...
            #
            # Probably means your *args are too long (array is longer than
            # registered class/func's non-keyword parameters list), or an arg
            # got swapped in the entry().
            #
            # e.g.:
            #   args: (001,)
            #   kwargs: {'data': {...}}
            #   entry -> JeffCls.__init__(data, id, extra=None)
            #     - This dies cuz data was set to '001', then kwargs also
            #       had a 'data'.
            raise log.exception(
                RegistryError,
                # Leave (k)args for others.
                "Registry failed creating '{}' with: args: {}, "
                "kwargs: {},  context: {}",
                entry, args, kwargs, context) from error

    # -------------------------------------------------------------------------
    # Unit Testing
    # -------------------------------------------------------------------------

    @classmethod
    def _ut_unregister(klass: 'BaseRegistrar') -> None:
        '''
        Looks like we don't need to do anything. Well, more like: we have to
        leave registered right now or tests will fail because nothing is
        registered.
        '''
        # '''
        # Nuke everything from the register; reset it completely.
        # '''
        # klass._REGISTRY = None
        pass


# -----------------------------------------------------------------------------
# Registration-By-Calling Class
# -----------------------------------------------------------------------------

class DottedRegistrar(BaseRegistrar):
    '''
    A class to hold registration data for whatever type of register you want.

    The registry is class-level, so subclass this for each unique registry.

    This registrar layers creating a `dotted()` classmethod for registering
    classes on top of the BaseRegistrar funcionality.
    '''

    @classmethod
    def _register(klass:       'BaseRegistrar',
                  registeree:  'RegisterType',
                  reg_label:    label.LabelInput,
                  leaf_key:     str,
                  reg_ours:     Dict,
                  reg_bg:       Dict) -> None:
        '''
        Let the parent class (BaseRegistrar) register this `registeree`, then
        add these attribuets to the `registeree`.
          - 'dotted._KLASS_FUNC_NAME'
          - 'dotted._ATTRIBUTE_PRIVATE_NAME'
        As of [2020-11-09], these are:
          - dotted() class method
          - _DOTTED class variable
        '''
        super()._register(registeree,
                          reg_label,
                          leaf_key,
                          reg_ours,
                          reg_bg)

        # ---
        # Set the attribute with the class's dotted name value.
        # ---
        dotted_name = label.normalize(reg_label)
        setattr(registeree,
                label._ATTRIBUTE_PRIVATE_NAME,
                dotted_name)

        # ---
        # Check the dotted func now.
        # ---

        dotted_attr = getattr(registeree,
                              label._KLASS_FUNC_NAME, None)
        if dotted_attr:
            # Pre-existing dotted attribute; is it abstract?
            # Complain about abstract.
            if getattr(dotted_attr, '__isabstractmethod__', False):
                msg = (f"{klass.dotted()}: Failed '{dotted_name}' registry of "
                       f"{registeree.__name__}. Registree has an abstract "
                       "'{label._KLASS_FUNC_NAME}' attribute, "
                       "which we cannot auto-generate a replacement for. "
                       "Please implement one manually:\n"
                       "    @classmethod\n"
                       "    def dotted(klass: 'YOURKLASS') -> str:\n"
                       "        # klass._DOTTED magically provided "
                       "by {klass.__name__}\n"
                       "        return klass."
                       "{label._KLASS_FUNC_NAME}")
                raise log.exception(AttributeError(msg, registeree), msg)

            # Complain loudly if the registeree has a `dotted` function and
            # what it returns disagrees with what they gave us as their dotted
            # name.
            if registeree.dotted() != dotted_name:
                msg = (f"{klass.dotted()}: Failed '{dotted_name}' registry of "
                       f"{registeree.__name__}. Registree has a dotted() "
                       "return value of "
                       f"'{label._KLASS_FUNC_NAME}', which is "
                       "not what it's trying to register as. Please fix the "
                       "class to have the same registration dotted name as "
                       "it has in its dotted() function.")
                raise log.exception(AttributeError(msg, registeree), msg)
        # ---
        # Make Getter.
        # ---
        def get_dotted(klass: Type[Any]) -> Optional[str]:
            return getattr(klass,
                           label._ATTRIBUTE_PRIVATE_NAME,
                           None)

        # ---
        # No Setter.
        # ---
        # def set_dotted(self, value):
        #     return setattr(self, '_dotted', value)

        # ---
        # Set the getter @classmethod function.
        # ---
        method = classmethod(get_dotted)
        setattr(registeree,
                label._KLASS_FUNC_NAME,
                method)


# -----------------------------------------------------------------------------
# Registration-By-Decorator Class
# -----------------------------------------------------------------------------

class DecoratorRegistrar(DottedRegistrar):
    '''
    A class to hold registration data for whatever type of register you want.

    The registry is class-level, so subclass this for each unique registry.

    DecoratorRegistrar is for registering via the decorator `register`
    function.
    '''

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    # Decorator way of doing factory registration. Note that we will only get
    # classes/funcs that are imported, when they are imported. We don't know
    # about any that are sitting around waiting to be imported. If needed, we
    # can fix that by importing things in their folder's __init__.py.

    @classmethod
    def register(klass: 'BaseRegistrar',
                 *args: str) -> Callable[..., Type[Any]]:
        '''
        Decorator property for registering a class or function with this
        registry.

        e.g. for a class:
          @BaseRegistrar.register('veredi', 'example', 'example-class')
          class Example:
            pass

        e.g. for a function:
          @BaseRegistrar.register('veredi', 'example', 'function')
          def example(arg0, arg1, **kwargs):
            pass
        '''

        # Now make the actual decorator...
        def register_decorator(cls_or_func: 'RegisterType') -> Type[Any]:

            # ...which is just a call to the BaseRegistrar...
            super().register(cls_or_func, *args)

            # ...and then returning the cls_or_func we decorated.
            return cls_or_func

        # ...and return it.
        return register_decorator


# -----------------------------------------------------------------------------
# Registration-By-Calling Class
# -----------------------------------------------------------------------------

class CallRegistrar(DottedRegistrar):
    '''
    A class to hold registration data for whatever type of register you want.

    The registry is class-level, so subclass this for each unique registry.

    This registrar is for registering by just calling the register function
    from somewhere. For example, a base class that wants all its subclasses to
    register as they're imported could implement the registration in
    __init_subclass__().
      https://docs.python.org/3/reference/datamodel.html#object.__init_subclass__
    '''

    # Nothing special to do at the moment.
    pass
