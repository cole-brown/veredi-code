# coding: utf-8

'''
Exceptions for Mediators, asyncio.

Apparently the proper way to handle asyncio exceptions is some global exception
handler...

https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.set_exception_handler
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Callable


from veredi.logger import log


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_exception_callbacks = set()


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def add_exception_callback(func: Callable[[str, Optional[Exception]], bool]
                           ) -> None:
    '''
    Add a callback of signature "callback_func(exception) -> bool".

    This will be called if the `async_handle_exception()` function catches an
    exception.
    '''
    _exception_callbacks.add(func)


def async_handle_exception(loop, context):
    '''
    Global handler for asyncio exceptions.
    '''
    # context["message"] will always be there; but context["exception"] may not
    error = context.get("exception", None)
    msg = context["message"]
    if not error:
        log.error(f"Caught asyncio exception (with just message): {msg}")
    else:
        log.exception(error,
                      None,
                      "Caught asyncio exception: "
                      f"error: {error}, msg: {msg}")

    for callback in _exception_callbacks:
        callback(msg, error)
