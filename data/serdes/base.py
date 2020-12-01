# coding: utf-8

'''
Base class for Reader/Loader & Writer/Dumper of ___ Format.
Aka ___ Serdes.
Aka ___ Serializer/Deserializer.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union,
                    NewType, Any, Iterable, Mapping, List, Dict, TextIO)
if TYPE_CHECKING:
    from veredi.base.context        import VerediContext
    from veredi.data.config.context import ConfigContext


from abc import ABC, abstractmethod
from io import StringIO


from ..codec.encodable import Encodable


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


DeserializeTypes = NewType('DeserializeTypes',
                           Union[List[Any], Dict[str, Any], None])
'''Serdes can deserialize to these types.'''


SerializeTypes = NewType('SerializeTypes',
                         Union[Encodable,
                               Iterable[Any],
                               Mapping[str, Any],
                               None])
'''Serdes can serialize these types.'''

# TODO [2020-11-30]: ReadTypes/WriteTypes for _read(_all) and _write(_all)
# functions?


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# Subclasses, register like this:
# @register('veredi', 'serdes', 'SerdesSubclass')
class BaseSerdes(ABC):
    def __init__(self,
                 serdes_name:    str,
                 config_context: Optional['VerediContext'] = None) -> None:
        '''
        `serdes_name` should be short and will be lowercased. It should
        probably be like a filename extension, e.g. 'yaml', 'json'.

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
        Should be lowercase and short. Probably like the filename extension.
        E.g.: 'yaml', 'json'
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
        '''
        return {
            'dotted': dotted_name,
            'type': self.name,
        }

    def make_context_data(self) -> Mapping[str, str]:
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
        Allows serdess to grab anything from the config data that they need to
        set up themselves.
        '''
        raise NotImplementedError(f"{self.__class__.__name__}._configure() "
                                  "is not implemented.")

    # -------------------------------------------------------------------------
    # Abstract: Decode Methods
    # -------------------------------------------------------------------------

    @abstractmethod
    def deserialize(self,
               stream: Union[TextIO, str],
               context: 'VerediContext') -> DeserializeTypes:
        '''Read and deserializes a single document from the data stream.

        Raises:
          - exceptions.ReadError
            - wrapping a library error?
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.deserialize() "
                                  "is not implemented.")

    @abstractmethod
    def deserialize_all(self,
                   stream: Union[TextIO, str],
                   context: 'VerediContext') -> DeserializeTypes:
        '''Read and deserializes all documents from the data stream.

        Raises:
          - exceptions.ReadError
            - wrapping a library error?
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.deserialize_all() "
                                  "is not implemented.")

    @abstractmethod
    def _read(self,
              stream: Union[TextIO, str],
              context: 'VerediContext') -> Any:
        '''Read data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.ReadError
            - wrapped lib/module errors
        '''
        raise NotImplementedError(f"{self.__class__.__name__}._read() "
                                  "is not implemented.")

    @abstractmethod
    def _read_all(self,
                  stream: Union[TextIO, str],
                  context: 'VerediContext') -> Any:
        '''Read data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.ReadError
            - wrapped lib/module errors
        '''
        raise NotImplementedError(f"{self.__class__.__name__}._read_all() "
                                  "is not implemented.")

    # -------------------------------------------------------------------------
    # Abstract: Serialize Methods
    # -------------------------------------------------------------------------

    @abstractmethod
    def serialize(self,
               data: SerializeTypes,
               context: 'VerediContext') -> StringIO:
        '''Write and serializes a single document from the data stream.

        Raises:
          - exceptions.WriteError
            - wrapping a library error?
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.serialize() "
                                  "is not implemented.")

    @abstractmethod
    def serialize_all(self,
                   data: SerializeTypes,
                   context: 'VerediContext') -> StringIO:
        '''Write and serializes all documents from the data stream.

        Raises:
          - exceptions.WriteError
            - wrapping a library error?
        '''
        raise NotImplementedError(f"{self.__class__.__name__}.serialize_all() "
                                  "is not implemented.")

    @abstractmethod
    def _write(self,
               data: Mapping[str, Any],
               context: 'VerediContext') -> Any:
        '''Write data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.WriteError
            - wrapped lib/module errors
        '''
        raise NotImplementedError(f"{self.__class__.__name__}._write() "
                                  "is not implemented.")

    @abstractmethod
    def _write_all(self,
                   data: Mapping[str, Any],
                   context: 'VerediContext') -> Any:
        '''Write data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.WriteError
            - wrapped lib/module errors
        '''
        raise NotImplementedError(f"{self.__class__.__name__}._write_all() "
                                  "is not implemented.")
