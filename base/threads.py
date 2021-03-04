# coding: utf-8

'''
Generic collection-type or pair-ish or (named) tuple-ish things.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any


import threading


# -----------------------------------------------------------------------------
# Thread-Local Data Object
# -----------------------------------------------------------------------------

class Local(threading.local):
    '''
    Veredi's thread-local data object.

    Built on top of Python's `threading.local`; supports initializing certain
    variables in the constructor so all threads have a default value.
    '''

    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        self.__dict__.update(kwargs)

    def set(self, key: str, value: Any) -> None:
        '''
        Set a thread-local variable. Can also set directly:
          local_obj.key = value

        This is just here for pairity with `get()`...
        '''
        self.__dict__[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        '''
        Tries to get a key from our `__dict__`, which has all our thread-local
        variables in it.

        You can also access the key directly as `local_obj.key`, though that
        has the usual AttributeError caveats.

        Returns `default` if key is not present.
        '''
        return self.__dict__.get(key, default)
