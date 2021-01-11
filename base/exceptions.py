# coding: utf-8

'''
All your Exceptions are belong to these classes.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, Optional, Union, Any, Type, Dict
if TYPE_CHECKING:
    from .context    import VerediContext
    from .base.const import VerediHealth

from veredi.logger import pretty


# -----------------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------------

def is_veredi(error_or_type: Union[Exception, Type[Exception]]) -> bool:
    '''
    Given `error_or_type`, this will return True if it is a VerediError or
    sub-class, and False otherwise.

    `error_or_type` can be either an instance or a class type.
    '''
    # ---
    # Need to get the real actual type.
    # ---
    type_of_error = (type(error_or_type)
                     if isinstance(error_or_type, Exception) else
                     error_or_type)

    # ---
    # Now we can check for the relation to our base exception class.
    # ---
    return issubclass(type_of_error, VerediError)


# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------

class VerediError(Exception):
    def __init__(self,
                 message:    str,
                 cause:      Optional[Exception]       = None,
                 context:    Optional['VerediContext'] = None,
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

        self.data       = data
        '''
        A bucket to stuff any extra data about the error.
        '''

    def __str__(self):
        output = f"{self.message}"
        if self.cause:
            output += f" from {self.cause}"
        if self.context:
            output += f" with context {self.context}"
        if self.data:
            output += "\nAdditional Error Data:\n"
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
                 message:        str,
                 cause:          Optional[Exception],
                 context:        Optional['VerediContext'] = None,
                 **data:         Optional[Dict[Any, Any]]):
        '''Healths saved in addition to the usual VerediError stuff.'''
        super().__init__(message, cause, context, **data)

        self.current = current_health
        '''Health the error creator set things to.'''

        self.previous = prev_health
        '''Health that the caller was at before the error happened.'''
