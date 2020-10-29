# coding: utf-8

'''
For Serializing/Deserializing strings.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, NewType, Any, Iterable, TextIO)
if TYPE_CHECKING:
    from veredi.base.context        import VerediContext
    from veredi.data.config.context import ConfigContext


from io import IOBase, StringIO
from collections.abc import Iterable


from veredi.logger import log
from veredi.base.null import null_or_none
from veredi.data                 import background
from veredi.data.config.registry import register

from .serializable import Serializable
from .base import (BaseSerdes, SerializeTypes, DeserializeTypes)
from ..exceptions import SerializableError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'serdes', 'string')
class StringSerdes(BaseSerdes):
    '''
    Serialize from encoded output to string.
    Deserialize from string to decodable input.
    '''

    def __init__(self,
                 config_context: Optional['VerediContext'] = None) -> None:
        '''
        `config_context` is the context being used to set us up.
        '''
        super().__init__('string', config_context)

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''
        Grab anything from the config data that we need to set ourselves up.
        '''
        # Set up our background for when it gets pulled in.
        self._make_background()

    # -------------------------------------------------------------------------
    # Context Properties/Methods
    # -------------------------------------------------------------------------

    @property
    def background(self):
        '''
        Data for the Veredi Background context.
        '''
        return self._bg, background.Ownership.SHARE

    def _make_background(self):
        '''
        Our background data.
        '''
        self._bg = super()._make_background(self.dotted)

    # -------------------------------------------------------------------------
    # Deserialize Methods
    # -------------------------------------------------------------------------

    def deserialize(self,
                    stream:  SerializeTypes,
                    context: 'VerediContext') -> DeserializeTypes:
        '''
        Takes `stream` and deserializes it to a single DeserializeTypes.

        Raises:
          - SerializableError
        '''
        deserialized = None
        if isinstance(stream, StringIO):
            deserialized = stream.getvalue()
            stream.close()

        elif isinstance(stream, str):
            deserialized = stream

        elif isinstance(stream, bytes):
            # Not sure what to do with bytes... let the decoder decide?
            deserialized = stream

        return deserialized

    # -------------------------------------------------------------------------
    # Serialize Methods
    # -------------------------------------------------------------------------

    def serialize(self,
                  data: DeserializeTypes,
                  context: 'VerediContext') -> str:
        '''
        Serialize `data` into a str.
        Takes ownership of the data stream - closes it when it's done.

        Raises:
          - SerializableError
        '''
        serialized = None

        try:
            log.debug(f"Serializing data: {data}")

            # ---
            # Serialize something!
            # ---
            if isinstance(data, StringIO):
                serialized = self._serialize(data.getvalue(), context)

            elif isinstance(data, str):
                serialized = self._serialize(data.getvalue(), context)

            # Strings and streams and such are Iterable, apparently, so put
            # this as last as possible.
            elif isinstance(data, Iterable):
                log.debug(f"Serializing iterable... {data}")
                serializing = []
                for item in data:
                    serializing.add(self._serialize(item, context))
                serialized = '\n'.join(serializing)

            else:
                serialized = self._serialize(data, context)

        finally:
            # Don't forget to close the data stream if is a data stream;
            # it's our stream to dispose of once it hits this function.
            if isinstance(data, IOBase):
                data.close()

        log.debug(f"Serialized data to: {serialized}")
        return serialized

    def _serialize(self,
                   data:    DeserializeTypes,
                   context: 'VerediContext') -> str:
        '''
        Serialize one serializable thing in `data` into the StringIO `stream`.
        Does not close the stream.

        Raises:
          - SerializableError
        '''
        serialized = None

        # Simplest: str is str.
        if isinstance(data, str):
            serialized = data
            log.debug(f"serialized str to str: {serialized}")

        # Serializable? Serialize it.
        elif isinstance(data, Serializable):
            serialized = data.serialize()
            log.debug(f"serialized Serializable to str?: {serialized}")

        # Not sure if this'll work out ok, but try it out?
        # May need to return an empty str or something?
        elif null_or_none(data):
            serialized = None
            log.debug(f"serialized null/none to None: {serialized}")

        # Not sure...
        # Is data simple and serialized directly?
        else:
            serialized = str(data)
            log.debug(f"serialized IDK to str?: {serialized}")

        return serialized
