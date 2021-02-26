# coding: utf-8

'''
Attribute-based access control.

See: https://en.wikipedia.org/wiki/Attribute-based_access_control
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.logs.lumberjack import Lumberjack

from .policy                import PolicyDecisionPoint

from .attributes.subject    import Subject


# -----------------------------------------------------------------------------
# General Logger for this Module:
# -----------------------------------------------------------------------------

_DOTTED: str = 'veredi.security.abac'
'''Dotted name string used to name this logger.'''


_ABAC_LOGGER: Lumberjack = Lumberjack(_DOTTED)
'''
A named logger (child of the general veredi logger), used for logging in all
of these functions.
'''


@property
def log() -> Lumberjack:
    '''
    Getter property for the general abac logger by the name `_DOTTED`.
    '''
    return _ABAC_LOGGER


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # ------------------------------
    # File-Local
    # ------------------------------
    'log',

    # ------------------------------
    # Attributes
    # ------------------------------
    'Subject',


    # ------------------------------
    # Policy
    # ------------------------------
    'PolicyDecisionPoint',
]
