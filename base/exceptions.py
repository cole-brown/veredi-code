# coding: utf-8

'''
All your Exceptions are belong to these classes.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, Optional, Any
if TYPE_CHECKING:
    from .context import VerediContext


# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------

class VerediError(Exception):
    def __init__(self,
                 message: str,
                 cause: Optional[Exception],
                 context: Optional['VerediContext'] = None,
                 associated: Optional[Any] = None):
        '''Context data included.'''
        self.message    = message
        self.cause      = cause
        self.context    = context
        self.associated = associated

    def __str__(self):
        output = f"{self.message}"
        if self.cause:
            output += f" from {self.cause}"
        if self.associated:
            output += f" associtaed with {self.associated}"
        if self.context:
            output += f" with context {self.context}"

        return output


class KeyError(VerediError):
    '''
    Veredi Version of Python's KeyError.
    # TODO [2020-07-08]: Just use Python's?
    '''
    ...


class ContextError(VerediError):
    '''
    VerediContext-related errors.
    '''
    ...
