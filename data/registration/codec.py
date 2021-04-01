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
    from veredi.data.codec.encodable import Encodable
    from veredi.data.config.context import ConfigContext


from veredi.logs                import log
from veredi.data                import background
from veredi.base.registrar      import (RegisterType,
                                        registrar as base_registrar)
from veredi.base.strings        import label

from veredi.data.codec.registry import EncodableRegistry


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # ------------------------------
    # Instances
    # ------------------------------
    'codec',

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

codec: EncodableRegistry = None
'''
The registry instance for Encodables.
'''

_DOTTED: label.DotStr = 'veredi.data.registration.codec'
'''
For logging.
'''


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def create(log_groups: List[log.Group],
           context:    'ConfigContext') -> EncodableRegistry:
    '''
    Create the EncodableRegistry instance.
    '''
    log.registration(label.normalize(_DOTTED, 'create'),
                     'Creating EncodableRegistry...')
    global codec
    codec = base_registrar(EncodableRegistry,
                           log_groups,
                           context,
                           codec)
    log.registration(label.normalize(_DOTTED, 'create'),
                     'Created EncodableRegistry.')


def register(klass:          Type['Encodable'],
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
            msg = ("Encodable sub-classes must either have a `dotted()` "
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
                     codec.__class__.__name__,
                     dotted_str,
                     klass.__name__)

    dotted_args = label.regularize(dotted)
    codec.register(klass, *dotted_args)

    log.registration(log_dotted,
                     "{}: Registered '{}' to '{}'.",
                     codec.__class__.__name__,
                     dotted_str,
                     klass.__name__)


def ignore(ignoree: Type['Encodable']) -> None:
    '''
    For flagging an Encodable class as one that is a base class
    or should not be registered for some other reason.
    '''
    log_dotted = label.normalize(EncodableRegistry.dotted(), 'ignore')
    log.registration(log_dotted,
                     "{}: '{}' marking as ignored for registration...",
                     codec.__class__.__name__,
                     ignoree)

    codec.ignore(ignoree)

    log.registration(log_dotted,
                     "{}: '{}' marked as ignored.",
                     codec.__class__.__name__,
                     ignoree)
