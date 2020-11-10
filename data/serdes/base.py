# coding: utf-8

'''
Base class for Serializing/Deserializing.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, NewType, Iterable, TextIO)
if TYPE_CHECKING:
    from veredi.base.context        import VerediContext
    from veredi.data.config.context import ConfigContext


from abc import ABC, abstractmethod


from .serializable import Serializable


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

SerializeTypes = NewType('SerializeTypes',
                         Union[str, bytes, TextIO, None])


DeserializeTypes = NewType('DeserializeTypes',
                           Union[Serializable, Iterable[Serializable],
                                 str, None])


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# Subclasses, register like this:
# @register('veredi', 'serdes', 'SerdesSubclass')
class BaseSerdes(ABC):
    def __init__(self,
                 serdes_name:     str,
                 config_context: Optional['VerediContext'] = None) -> None:
        '''
        `serdes_name` should be short and will be lowercased.
        'string', 'file', 'IDK'?

        `config_context` is the context being used to set us up.
        '''
        self._name = serdes_name.lower()

        self._configure(config_context)

    # -------------------------------------------------------------------------
    # Serdes Properties/Methods
    # -------------------------------------------------------------------------

    @property
    def name(self) -> str:
        '''
        Should be lowercase and short.
        '''
        return self._name

    # -------------------------------------------------------------------------
    # Context Properties/Methods
    # -------------------------------------------------------------------------

    @property
    @abstractmethod
    def background(self):
        '''
        Data for the Veredi Background context.
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.background() "
                                  "is not implemented.")

    def _make_background(self, dotted_name):
        '''
        Start of the background data.

        `dotted_name` should be the dotted version of your @register() string.
        e.g. for:
          @register('veredi', 'repository', 'file-bare')
        `dotted_name` is:
          'veredi.repository.file-bare'

        @register will give you the self._DOTTED string, and probably the
        self.dotted property to use as the argument.
        '''
        return {
            'dotted': dotted_name,
            'type': self.name,
        }

    def make_context_data(self) -> Union[str, str]:
        '''
        Returns context data for inserting into someone else's context.
        '''
        return {
            'dotted': self.dotted(),
            'type': self.name,
        }

    # -------------------------------------------------------------------------
    # Abstract Methods
    # -------------------------------------------------------------------------

    @abstractmethod
    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''
        Allows serdes to grab anything from the config data that they need to
        set up themselves.
        '''
        raise NotImplementedError(f"{self.__class__.__name__}._configure() "
                                  "is not implemented.")

    # -------------------------------------------------------------------------
    # Abstract: Deserialize Methods
    # -------------------------------------------------------------------------

    @abstractmethod
    def deserialize(self,
                    stream:  SerializeTypes,
                    context: 'VerediContext') -> DeserializeTypes:
        '''
        Read and deserializes a single document from the data stream.

        Raises:
          - exceptions.ReadError
            - wrapping a library error?
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.deserialize() "
                                  "is not implemented.")

    # -------------------------------------------------------------------------
    # Abstract: Serialize Methods
    # -------------------------------------------------------------------------

    @abstractmethod
    def serialize(self,
                  data: DeserializeTypes,
                  context: 'VerediContext') -> SerializeTypes:
        '''
        Write and serializes a single document from the data stream.

        Raises:
          - exceptions.WriteError
            - wrapping a library error?
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.serialize() "
                                  "is not implemented.")
