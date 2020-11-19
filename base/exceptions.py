# coding: utf-8

'''
All your Exceptions are belong to these classes.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, Optional, Any
if TYPE_CHECKING:
    from .context    import VerediContext
    from .base.const import VerediHealth


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
            output += f" associated with {self.associated}"
        if self.context:
            output += f" with context {self.context}"

        return output


class ContextError(VerediError):
    '''
    VerediContext-related errors.
    '''
    ...


class HealthError(VerediError):
    '''
    VerediHealth-specific errors. Errors that incidentally cause a poor health
    probably would be better using an exception type related to the actual
    cause of the error instead.
    '''

    def __init__(self,
                 current_health: 'VerediHealth',
                 prev_health:    'VerediHealth',
                 message: str,
                 cause: Optional[Exception],
                 context: Optional['VerediContext'] = None,
                 associated: Optional[Any] = None):
        '''Healths saved in addition to the usual VerediError stuff.'''
        super().__init__(message, cause, context, associated)

        self.current = current_health
        '''Health the error creator set things to.'''

        self.previous = prev_health
        '''Health that the caller was at before the error happened.'''
