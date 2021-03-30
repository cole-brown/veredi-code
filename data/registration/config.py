# coding: utf-8

'''
Registry functions for Encodables.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Type, List)
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
    # Functions
    # ------------------------------
    'registrar',
    'registry',
    'register',
    'ignore',
]


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_REGISTRAR: ConfigRegistry = None
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

def registrar(log_groups: List[log.Group],
              context:    'ConfigContext') -> ConfigRegistry:
    '''
    Create the ConfigRegistry instance.
    '''
    log_dotted = label.normalize(_DOTTED, 'registrar')
    log.registration(log_dotted,
                     'Creating EncodableRegistry...')
    global _REGISTRAR
    _REGISTRAR = base_registrar(ConfigRegistry,
                                log_groups,
                                context,
                                _REGISTRAR)
    log.registration(log_dotted,
                     'Created EncodableRegistry.')


def registry() -> ConfigRegistry:
    '''
    Get the ConfigRegistry.
    '''
    return _REGISTRAR


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
                     _REGISTRAR.__class__.__name__,
                     dotted_str,
                     klass.__name__)

    dotted_args = label.regularize(dotted)
    _REGISTRAR.register(klass, *dotted_args)

    log.registration(log_dotted,
                     "{}: Registered '{}' to '{}'.",
                     _REGISTRAR.__class__.__name__,
                     dotted_str,
                     klass.__name__)


def ignore(ignoree: RegisterType) -> None:
    '''
    For flagging an Config class as one that is a base class
    or should not be registered for some other reason.
    '''
    log_dotted = label.normalize(ConfigRegistry.dotted(), 'ignore')
    log.registration(log_dotted,
                     "{}: '{}' marking as ignored for registration...",
                     _REGISTRAR.__class__.__name__,
                     ignoree)

    _REGISTRAR.ignore(ignoree)

    log.registration(log_dotted,
                     "{}: '{}' marked as ignored.",
                     _REGISTRAR.__class__.__name__,
                     ignoree)
