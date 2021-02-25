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
                    Optional, Union, NewType, Any,
                    Iterable, Mapping, List, Dict, Tuple, TextIO)
if TYPE_CHECKING:
    from veredi.base.context        import VerediContext
    from veredi.data.config.context import ConfigContext
    from veredi.data.context        import DataAction


from abc import ABC, abstractmethod
from io import StringIO


from veredi              import log
from veredi.logger.mixin import LogMixin

from veredi.data         import background
from ..codec.encodable   import Encodable


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


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# Subclasses, register like this:
# @register('veredi', 'serdes', 'SerdesSubclass')
class BaseSerdes(LogMixin, ABC):

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # ------------------------------
    # Logging
    # ------------------------------

    _LOG_INIT: List[log.Group] = [
        log.Group.START_UP,
        log.Group.DATA_PROCESSING
    ]
    '''
    Group of logs we use a lot for log.group_multi().
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        self._name: str = None
        '''The name of the repository.'''

        self._bg: Dict[Any, Any] = {}
        '''Our background context data that is shared to the background.'''

    def __init__(self,
                 serdes_name:    str,
                 config_context: Optional['VerediContext'] = None) -> None:
        '''
        `serdes_name` should be short and will be lowercased. It should
        probably be like a filename extension, e.g. 'yaml', 'json'.

        `config_context` is the context being used to set us up.
        '''
        self._define_vars()
        self._name = serdes_name.lower()

        # ---
        # Set-Up LogMixin before _configure() so we have logging.
        # ---
        self._log_config(self.dotted())
        # Log both class and base name?
        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              f"{self.__class__.__name__} init...")
        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              "BaseSerdes init...")

        self._configure(config_context)
        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              "Done with BaseSerdes init.")

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''
        Do whatever configuration we can as the base class; sub-classes should
        finish up whatever is needed to set up themselves.
        '''
        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              "BaseSerdes configure...")

        # Set up our background for when it gets pulled in.
        self._make_background()

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
    def background(self) -> Tuple[Dict[str, str], background.Ownership]:
        '''
        Data for the Veredi Background context.

        Returns: (data, background.Ownership)
        '''
        return self._bg, background.Ownership.SHARE

    def _make_background(self) -> Dict[str, str]:
        '''
        Start of the background data.

        `dotted_name` should be the dotted version of your @register() string.
        e.g. for:
          @register('veredi', 'repository', 'file-bare')
        `dotted_name` is:
          'veredi.repository.file-bare'
        '''
        self._bg = {
            'dotted': self.dotted(),
            'type': self.name,
        }
        return self._bg

    def _context_data(self,
                      context: 'VerediContext',
                      action:  'DataAction') -> 'VerediContext':
        '''
        Inject our serdes data into the context.
        '''
        key = str(background.Name.SERDES)
        meta, _ = self.background
        context[key] = {
            # Push our context data into our sub-context key.
            'meta': meta,
            # And add any extra info.
            'action': action,
        }

        return context

    # -------------------------------------------------------------------------
    # Abstract: Deserialize Methods
    # -------------------------------------------------------------------------

    @abstractmethod
    def deserialize(self,
                    stream:  Union[TextIO, str],
                    context: 'VerediContext') -> DeserializeTypes:
        '''
        Read and deserializes a single document from the data stream.

        Raises:
          - exceptions.ReadError
            - wrapping a library error?
        '''
        raise NotImplementedError(
            f"{self.__class__.__name__}.deserialize() "
            "is not implemented.")

    @abstractmethod
    def deserialize_all(self,
                        stream:  Union[TextIO, str],
                        context: 'VerediContext') -> DeserializeTypes:
        '''
        Read and deserializes all documents from the data stream.

        Raises:
          - exceptions.ReadError
            - wrapping a library error?
        '''
        raise NotImplementedError(
            f"{self.__class__.__name__}.deserialize_all() "
            "is not implemented.")

    @abstractmethod
    def _read(self,
              stream:  Union[TextIO, str],
              context: 'VerediContext') -> Any:
        '''
        Read data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.ReadError
            - wrapped lib/module errors
        '''
        raise NotImplementedError(
            f"{self.__class__.__name__}._read() "
            "is not implemented.")

    @abstractmethod
    def _read_all(self,
                  stream:  Union[TextIO, str],
                  context: 'VerediContext') -> Any:
        '''
        Read data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.ReadError
            - wrapped lib/module errors
        '''
        raise NotImplementedError(
            f"{self.__class__.__name__}._read_all() "
            "is not implemented.")

    # -------------------------------------------------------------------------
    # Abstract: Serialize Methods
    # -------------------------------------------------------------------------

    @abstractmethod
    def serialize(self,
                  data:    SerializeTypes,
                  context: 'VerediContext') -> StringIO:
        '''
        Write and serializes a single document from the data stream.

        Raises:
          - exceptions.WriteError
            - wrapping a library error?
        '''
        raise NotImplementedError(
            f"{self.__class__.__name__}.serialize() "
            "is not implemented.")

    @abstractmethod
    def serialize_all(self,
                      data:    SerializeTypes,
                      context: 'VerediContext') -> StringIO:
        '''
        Write and serializes all documents from the data stream.

        Raises:
          - exceptions.WriteError
            - wrapping a library error?
        '''
        raise NotImplementedError(
            f"{self.__class__.__name__}.serialize_all() "
            "is not implemented.")

    @abstractmethod
    def _write(self,
               data:    Mapping[str, Any],
               context: 'VerediContext') -> Any:
        '''
        Write data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.WriteError
            - wrapped lib/module errors
        '''
        raise NotImplementedError(
            f"{self.__class__.__name__}._write() "
            "is not implemented.")

    @abstractmethod
    def _write_all(self,
                   data:    Mapping[str, Any],
                   context: 'VerediContext') -> Any:
        '''
        Write data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.WriteError
            - wrapped lib/module errors
        '''
        raise NotImplementedError(
            f"{self.__class__.__name__}._write_all() "
            "is not implemented.")
