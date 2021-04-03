# coding: utf-8

'''
Registry functions for Encodables.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Any, Type, Callable, List)
if TYPE_CHECKING:
    from veredi.data.config.context import ConfigContext


from veredi.logs                import log
from veredi.data                import background
from veredi.base.registrar      import (RegisterType,
                                        registrar as base_registrar)
from veredi.base.strings        import label

from veredi.data.config.registry import ConfigRegistry


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # ------------------------------
    # Instances
    # ------------------------------
    'config',

    # ------------------------------
    # Functions
    # ------------------------------
    'create',
    'register',
    'ignore',
]


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

config: ConfigRegistry = None
'''
The registry instance for Configs.
'''

_DOTTED: label.DotStr = 'veredi.data.registration.config'
'''
For logging.
'''


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def create(log_groups: List[log.Group],
           context:    'ConfigContext') -> ConfigRegistry:
    '''
    Create the ConfigRegistry instance.
    '''
    log_dotted = label.normalize(_DOTTED, 'create')
    log.registration(log_dotted,
                     'Creating EncodableRegistry...')
    global config
    config = base_registrar(ConfigRegistry,
                            log_groups,
                            context,
                            config)
    log.registration(log_dotted,
                     'Created EncodableRegistry.')


def register(klass:          RegisterType,
             dotted:         Optional[label.LabelInput] = None,
             unit_test_only: Optional[bool]             = False) -> None:
    '''
    Register the `klass` with the `dotted` string to our registry.

    If `unit_test_only` is Truthy, the `klass` will be registered if we are
    running a unit test, or handed off to `ignore()` if we are not.
    '''
    log_dotted = label.normalize(_DOTTED, 'register')

    # ---
    # Sanity
    # ---
    if not dotted:
        # Check for class's dotted.
        try:
            dotted = klass.dotted()
        except AttributeError:
            pass
        # No dotted string is an error.
        if not dotted:
            msg = ("Config sub-classes must either have a `dotted()` "
                   "class method or be registered with a `dotted` "
                   "argument.")
            error = ValueError(msg, klass, dotted)
            log.registration(log_dotted,
                             msg + "Got '{}' for {}.",
                             dotted, klass)
            raise log.exception(error, msg)

    # ---
    # Unit Testing?
    # ---
    # Unit-test registrees should continue on if in unit-testing mode,
    # or be diverted to ignore if not.
    if unit_test_only and not background.testing.get_unit_testing():
        ignore(klass)
        return

    # ---
    # Register
    # ---
    # Registry should check if it is ignored already by someone previous,
    # if it cares.
    dotted_str = label.normalize(dotted)
    log.registration(log_dotted,
                     "{}: Registering '{}' to '{}'...",
                     config.__class__.__name__,
                     dotted_str,
                     klass.__name__)

    dotted_args = label.regularize(dotted)
    config.register(klass, *dotted_args)

    log.registration(log_dotted,
                     "{}: Registered '{}' to '{}'.",
                     config.__class__.__name__,
                     dotted_str,
                     klass.__name__)


# Decorator way of doing factory registration. Note that we will only get
# classes/funcs that are imported, when they are imported. We don't know
# about any that are sitting around waiting to be imported. If needed, we
# can fix that by importing things in their folder's __init__.py.
def register_this(*dotted_label: label.LabelInput) -> Callable[..., Type[Any]]:
    '''
    Decorator property for registering a class or function with this
    registry.

    e.g. for a class:
      @register_this('veredi', 'example', 'example-class')
      class Example:
        pass

    e.g. for a function:
      @register_this('veredi', 'example', 'function')
      def example(arg0, arg1, **kwargs):
        pass
    '''

    # Now make the actual decorator...
    def register_decorator(cls_or_func: 'RegisterType') -> Type[Any]:

        # ...which is just a call to the BaseRegistrar...
        register(cls_or_func, dotted_label)

        # _DOTTED and dotted() provided in super().register() by
        # our DottedRegistrar parent class.

        # ...and then returning the cls_or_func we decorated.
        return cls_or_func

    # ...and return it.
    return register_decorator


def ignore(ignoree: RegisterType) -> None:
    '''
    For flagging an Config class as one that is a base class
    or should not be registered for some other reason.
    '''
    log_dotted = label.normalize(ConfigRegistry.dotted, 'ignore')
    log.registration(log_dotted,
                     "{}: '{}' marking as ignored for registration...",
                     config.__class__.__name__,
                     ignoree)

    config.ignore(ignoree)

    log.registration(log_dotted,
                     "{}: '{}' marked as ignored.",
                     config.__class__.__name__,
                     ignoree)
