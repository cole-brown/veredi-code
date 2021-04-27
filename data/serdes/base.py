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
from io import StringIO, TextIOBase


from veredi.logs               import log
from veredi.logs.mixin         import LogMixin

from veredi.base.strings       import label
from veredi.base.strings.mixin import NamesMixin
from veredi.data               import background
from veredi.data.codec         import Codec, Encodable


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


_DeserializeMidTypes = NewType('_DeserializeMidTypes',
                               Union[List[Any], Dict[str, Any], None])
'''
Serdes.deserialize deserializes to these types before decoding.
'''


_DeserializeAllMidTypes = NewType(
    '_DeserializeAllMidTypes',
    Union[_DeserializeMidTypes, Iterable[_DeserializeMidTypes]])
'''
Sereds.deserialize_all deserializes to this before decoding all.
'''

DeserializeTypes = NewType('DeserializeTypes',
                           Union[List[Any], Dict[str, Any], None, Encodable])
'''
Serdes.deserialize returns these types after deserializing & decoding.
'''

DeserializeAllTypes = NewType('DeserializeAllTypes',
                              Union[DeserializeTypes, List[DeserializeTypes]])
'''
Serdes.deserialize_all returns these types after deserializing & decoding.
'''


SerializeTypes = NewType('SerializeTypes',
                         Union[Encodable,
                               Iterable[Any],
                               Mapping[str, Any],
                               None])
'''
Serdes can serialize these types.
'''


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class BaseSerdes(ABC, LogMixin, NamesMixin):
    '''
    Base SERializer/DESerializer class.

    Sub-classes should register with ConfigRegistry.
    '''

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
        self._bg: Dict[Any, Any] = {}
        '''Our background context data that is shared to the background.'''

    def __init__(self,
                 config_context: Optional['VerediContext'] = None) -> None:
        '''
        `serdes_name` should be short and will be lowercased. It should
        probably be like a filename extension, e.g. 'yaml', 'json'.

        `config_context` is the context being used to set us up.
        '''
        self._define_vars()

        # ---
        # Set-Up LogMixin before _configure() so we have logging.
        # ---
        self._log_config(self.dotted)
        # Log both class and base name?
        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              f"{self.klass} init...")
        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              "BaseSerdes init...")

        self._configure(config_context)
        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              "Done with BaseSerdes init.")

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''
        Do whatever configuration we can as the base class; sub-classes should
        finish up whatever is needed to set up themselves.
        '''
        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              "BaseSerdes configure...")

        # Set up our background for when it gets pulled in.
        self._make_background()

        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              "Done with BaseSerdes configuration.")

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
        '''
        self._bg = {
            'dotted': self.dotted,
            'type': self.name,
        }
        return self._bg

    def _context_data(self,
                      context: 'VerediContext',
                      action:  'DataAction',
                      codec:   Codec) -> 'VerediContext':
        '''
        Inject our serdes data into the context.
        '''
        key = str(background.Name.SERDES)
        meta, _ = self.background
        codec_ctx, _ = codec.background
        context[key] = {
            # Push our context data into our sub-context key.
            'meta': meta,
            # And add any extra info.
            'action': action,
            'codec': codec_ctx,
        }

        return context

    def _stream_data(self,
                     stream: Union[TextIO, str],
                     data:   Optional[Dict] = None,
                     field:  str            = 'stream') -> Dict:
        '''
        Get info about `stream` for logging, error messages.
        '''
        if data is None:
            data = {}
        entry = data.setdefault(field, {})

        entry['type'] = stream.__class__.__name__
        if isinstance(stream, TextIOBase):
            entry['closed'] = stream.closed if stream else None
            entry['readable'] = stream.readable() if stream else None
            entry['position'] = stream.tell() if stream else None

        return data

    # -------------------------------------------------------------------------
    # Abstract: Deserialize Methods
    # -------------------------------------------------------------------------

    def _decode(self,
                data:  _DeserializeMidTypes,
                codec: Codec
                ) -> DeserializeTypes:
        '''
        Decode `data` after it has been deserialized.

        Final step before returning to caller.
        '''
        # # Don't need to do anything more for simpler collections.
        # if isinstance(data, (dict, list)):
        #     return decoded

        # Try to decode...
        # If it can't be decoded, use data as decoded. Could be just the
        # metadata document or something which is (currently) just a dict.
        decoded = codec.decode(None, data,
                               error_squelch=True,
                               fallback=data)
        return decoded

    def _decode_all(self,
                    data:  _DeserializeAllMidTypes,
                    codec: Codec) -> DeserializeAllTypes:
        '''
        Deserialize each item in the data.

        If the data is not a list or dict, we will put it in a list before
        decoding it, so the return will be a list of one decoded item.
        '''
        if not isinstance(data, (list, dict)):
            data = [data]
        decoded = []
        for item in data:
            decoded.append(self._decode(item, codec))
        return decoded

    @abstractmethod
    def deserialize(self,
                    stream:  Union[TextIO, str],
                    codec:   Codec,
                    context: 'VerediContext') -> DeserializeTypes:
        '''
        Read and deserializes a single document from the data stream.

        Raises:
          - exceptions.ReadError
            - wrapping a library error?
        '''
        raise NotImplementedError(
            f"{self.klass}.deserialize() "
            "is not implemented.")

    @abstractmethod
    def deserialize_all(self,
                        stream:  Union[TextIO, str],
                        codec:   Codec,
                        context: 'VerediContext') -> DeserializeAllTypes:
        '''
        Read and deserializes all documents from the data stream.

        Raises:
          - exceptions.ReadError
            - wrapping a library error?
        '''
        raise NotImplementedError(
            f"{self.klass}.deserialize_all() "
            "is not implemented.")

    @abstractmethod
    def _read(self,
              stream:  Union[TextIO, str],
              codec:   Codec,
              context: 'VerediContext') -> _DeserializeMidTypes:
        '''
        Read data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.ReadError
            - wrapped lib/module errors
        '''
        raise NotImplementedError(
            f"{self.klass}._read() "
            "is not implemented.")

    @abstractmethod
    def _read_all(self,
                  stream:  Union[TextIO, str],
                  codec:   Codec,
                  context: 'VerediContext') -> _DeserializeAllMidTypes:
        '''
        Read data from a single data stream.

        Returns:
          Based on subclass.

        Raises:
          - exceptions.ReadError
            - wrapped lib/module errors
        '''
        raise NotImplementedError(
            f"{self.klass}._read_all() "
            "is not implemented.")

    # -------------------------------------------------------------------------
    # Abstract: Serialize Methods
    # -------------------------------------------------------------------------

    @abstractmethod
    def serialize(self,
                  data:    SerializeTypes,
                  codec:   Codec,
                  context: 'VerediContext') -> StringIO:
        '''
        Write and serializes a single document from the data stream.

        Raises:
          - exceptions.WriteError
            - wrapping a library error?
        '''
        raise NotImplementedError(
            f"{self.klass}.serialize() "
            "is not implemented.")

    @abstractmethod
    def serialize_all(self,
                      data:    SerializeTypes,
                      codec:   Codec,
                      context: 'VerediContext') -> StringIO:
        '''
        Write and serializes all documents from the data stream.

        Raises:
          - exceptions.WriteError
            - wrapping a library error?
        '''
        raise NotImplementedError(
            f"{self.klass}.serialize_all() "
            "is not implemented.")

    @abstractmethod
    def _write(self,
               data:    Mapping[str, Any],
               codec:   Codec,
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
            f"{self.klass}._write() "
            "is not implemented.")

    @abstractmethod
    def _write_all(self,
                   data:    Mapping[str, Any],
                   codec:   Codec,
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
            f"{self.klass}._write_all() "
            "is not implemented.")
