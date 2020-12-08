# coding: utf-8

'''
All your Exceptions are belong to these classes.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, Optional, Any, Dict
if TYPE_CHECKING:
    from .context    import VerediContext
    from .base.const import VerediHealth

from veredi.logger import pretty


# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------

class VerediError(Exception):
    def __init__(self,
                 message:    str,
                 cause:      Optional[Exception]       = None,
                 context:    Optional['VerediContext'] = None,
                 associated: Optional[Any]             = None,
                 **data:     Optional[Dict[Any, Any]]) -> None:
        '''Context data included.'''
        self.message    = message
        '''Human-friendly error message.'''

        self.cause      = cause
        '''
        (Optional) Python/Third-Party exception that caused Veredi to raise
        this exception.
        '''

        self.context    = context
        '''
        The Veredi Context, if there is one.
        '''

        self.associated = associated
        '''
        Something closely associated with the error.
        TODO: remove and just use `data`.
        '''

        self.data       = data
        '''
        A bucket to stuff any extra data about the error.
        '''

    def __str__(self):
        output = f"{self.message}"
        if self.cause:
            output += f" from {self.cause}"
        if self.associated:
            output += f" associated with {self.associated}"
        if self.context:
            output += f" with context {self.context}"
        if self.data:
            output += ". \nAdditional Error Data:\n"
            output += pretty.indented(self.data)

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
