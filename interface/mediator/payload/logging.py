# coding: utf-8

'''
Message payload for MsgType.LOGGING, helper functions.

For:
  - Server Mediator asking client LOGGING things.
  - Client Mediator (optionally, if it feels like it) obeying/replying.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, NewType, Mapping, Tuple

from abc import ABC, abstractmethod
import multiprocessing
import multiprocessing.connection
import asyncio
import enum
import contextlib

from veredi.logger               import log
from veredi.data.codec.encodable import Encodable
from veredi.data.exceptions      import EncodableError
from veredi.base.identity        import MonotonicId
from veredi.data.identity        import UserId, UserKey

from .base                       import BasePayload, Validity

# TODO
# TODO
# TODO
# TODO: Mapping[x, y] value's actual types correct?
# TODO
# TODO
# TODO


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

LogRequest  = NewType('LogRequest',  Mapping[str, Any])
LogResponse = NewType('LogResponse', Mapping[str, Any])


# ------------------------------
# Default Params
# ------------------------------

# For differentiating between "didn't say" and "said it was None".

_NC_LEVEL = -1000
_NC_STR   = "no-comment"


# ------------------------------
# Log Field Names for Encode/Decode
# ------------------------------

@enum.unique
class LogField(enum.Enum):
    '''
    Trying this out for the logging field names?
    '''

    # ------------------------------
    # Top-Level Fields
    # ------------------------------
    REQUEST = 'request'
    '''Top-level dict of all of server's request data.'''

    RESPONSE = 'response'
    '''Top-level dict of all of client's response data.'''

    # ------------------------------
    # Sub-Level Fields
    # ------------------------------
    LEVEL = 'level'
    '''Logging level (aka veredi.logger.log.Level).'''

    REPORT = 'report'
    '''
    Request for client to send logging meta-data (current log level, log
    handlers, whatever) to the server.
    '''

    REMOTE = 'remote'
    '''
    Request for client to connect their logging to this logging_server (in
    addition to local log output).
    '''


# -----------------------------------------------------------------------------
# LogPayload Reply Value from Client
# -----------------------------------------------------------------------------

class LogReply(Encodable):
    '''
    A helper class for logging payload fields from the client. Allows client to
    refuse to comment about specific things.
    '''

    @enum.unique
    class Valid(enum.Enum):
        '''
        Validity of field so we can tell "actually 'None'" from
        "'None' because I don't want to say", for example.
        '''
        INVALID    = enum.auto()
        NO_COMMENT = enum.auto()
        VALID      = enum.auto()

    def __init__(self,
                 value:            Any,
                 valid:            'LogReply.Valid' = Valid.INVALID,
                 no_comment_check: Any              = Valid.INVALID
                 ) -> None:
        self.value = value

        if valid != LogReply.Valid.INVALID:
            self.valid = valid
        elif no_comment_check != LogReply.Valid.INVALID:
            self.valid = self.validity(value, no_comment_check)

        if self.valid == LogReply.Valid.INVALID:
            raise ValueError(
                "LogReply cannot have a `valid` status of INVALID.",
                value, valid, no_comment_check, self.valid)

    @classmethod
    def validity(klass: 'LogReply',
                 value: Any,
                 no_comment: Any) -> 'LogReply.Valid':
        '''
        Returns VALID if `value` is not equal to `no_comment`
        or NO_COMMENT otherwise.
        '''
        return (LogReply.Valid.VALID
                if value != no_comment else
                LogReply.Valid.NO_COMMENT)

    def get_or_validity(self) -> Union['LogReply.Valid', Optional[Any]]:
        '''
        If `self.valid` is VALID, returns `self.value`.
        Otherwise return `self.valid`.
        '''
        if self.valid == LogReply.Valid.VALID:
            return self.value

        return self.valid

    # ------------------------------
    # Encodable API (Codec Support)
    # ------------------------------

    def encode(self) -> Mapping[str, Union[str, int]]:
        '''
        Returns a representation of ourself as a dictionary.
        '''
        encoded = super().encode()
        encoded.update({
            'valid': self.valid.value,
            'value': self.value
        })
        return encoded

    @classmethod
    def decode(klass: 'LogReply',
               mapping: Mapping[str, Union[str, int]]) -> 'LogReply':
        '''
        Turns our encoded dict into a LogReply instance.
        '''
        klass.error_for(mapping, keys=['valid', 'value'])
        return klass(valid=klass.Valid(mapping['valid']),
                     value=mapping['value'])


# -----------------------------------------------------------------------------
# Payload Actual
# -----------------------------------------------------------------------------

class LogPayload(BasePayload):
    '''
    Payload for a MsgType.LOGGING Message instance.
    '''

    def __init__(self,
                 data: Mapping[str, Union[str, int]] = None) -> None:
        # Ignoring validity to start with...
        super().__init__(data, Validity.VALID)

    # ------------------------------
    # Data Structure
    # ------------------------------

    @property
    def request(self) -> Mapping[str, str]:
        '''
        Get the Server->Client request portion of the data mapping.
        '''
        return self.data.setdefault(LogField.REQUEST, {})

    # TODO: probably delete? Will just set sub-fields on return from request
    # getter property.
    @request.setter
    def request(self, value: Mapping[str, Any]) -> None:
        '''
        Set the Server->Client request portion of the data mapping.
        '''
        self.data[LogField.REQUEST] = value

    @property
    def response(self):
        '''
        Get the Client->Server response portion of the data mapping.
        '''
        return self.data.setdefault(LogField.RESPONSE, {})

    # TODO: probably delete? Will just set sub-fields on return from response
    # getter property.
    @response.setter
    def response(self, value: Mapping[str, Any]) -> None:
        '''
        Set the Client->Server response portion of the data mapping.
        '''
        self.data[LogField.RESPONSE] = value

    def _set_or_pop(self,
                    submap:    Mapping,
                    field:     str,
                    value:     Any,
                    set_value: bool) -> None:
        '''
        Sets `field` in `submap` if `set_value`.
        Pops `field` out of `submap` if not `set_value`.
        '''
        if not field:
            raise ValueError(
                f"_set_or_pop cannot work with invalid field name: '{field}'",
                field, value, set_value, submap)

        # Set it and return.
        if set_value:
            submap[field] = value
            return

        # Otherwise pop it in a way that doesn't throw any
        # "but it isn't there" error.
        submap.pop(field, None)

    # ------------------------------
    # Server -> Client: Set Requests
    # ------------------------------

    # def request_many(self,
    #                  level: log.Level = log.Level.NOTSET,
    #                  report: bool     = True) -> None:
    #     '''
    #     Sets up a request for any param set to True.
    #     Clears out any requests set to False.
    #     '''
    #     request = self.request
    #     self._set_or_pop(request,
    #                      LogField.LEVEL,
    #                      level,
    #                      level != log.Level.NOTSET)
    #     self._set_or_pop(request,
    #                      LogField.REPORT,
    #                      report, report)

    def request_level(self, level) -> None:
        '''Sets up a request for logging level.'''
        self.request[LogField.LEVEL] = level

    def request_report(self) -> None:
        '''Sets up a request for logging report.'''
        self.request[LogField.REPORT] = True

    # ------------------------------
    # Client -> Server: Logging Report
    # ------------------------------

    def create_report(self,
                      level:   log.Level = _NC_LEVEL,
                      remotes: str       = _NC_STR) -> None:
        '''
        Creates logging report for LogPayload.

        `level` should be client's logging level

        `remotes` should be a string of client's logging remote handler(s)

        Any unspecificed/default params will be marked as NO_COMMENT validity.
        '''
        report = self.response.setdefault(LogField.REPORT, {})
        report[LogField.LEVEL] = LogReply(level, no_comment_check=_NC_LEVEL)
        report[LogField.REMOTE] = LogReply(remotes, no_comment_check=_NC_STR)

    # ------------------------------
    # Server: Get Logging Report
    # ------------------------------

    @property
    def report(self) -> Mapping[str, LogReply]:
        '''Returns validity of the entire logging report.'''
        report = self.response.get(LogField.REPORT, None)
        return report

    # ------------------------------
    # Encodable API (Codec Support)
    # ------------------------------

    def _encode(self,
                encoding: Mapping[str, Union[str, int]]
                ) -> Mapping[str, Union[str, int]]:
        '''
        Returns a representation of ourself as a dictionary.
        '''
        # log.debug(f"\n\nlogging.encode: {self.data}\n\n")

        # Updated with our specific encoding.
        encoding = self._encode_map(self.data, encoding)

        # log.debug(f"\n\n   done.encode: {encoding}\n\n")
        return encoding

    def _encode_key(self, key: Any) -> str:
        '''
        Encode a dict key.
        '''
        # log.debug(f"\n\nlogging._encode_key: {key}\n\n")
        field = None
        if isinstance(key, LogField):
            field = key.value
        else:
            field = super()._encode_key(key)

        # log.debug(f"\n\n   done._encode_key: {field}\n\n")
        return field

    # TODO [2020-08-18]: Move _decode_map, _decode_key, _decode_value to
    # Encodable?
    @classmethod
    def _decode_map(klass: 'LogPayload',
                    mapping: Mapping
                    # TODO: Better return type - NewType it so it's usable all
                    # over for encodables?
                    ) -> Mapping[str, Any]:
        # log.debug(f"\n\nlogging._decode_map {type(mapping)}: {mapping}\n\n")

        # Have parent deal with it first.
        decoded = super()._decode_map()

        # Is this dictionary anything special?
        if LogReply.claim(decoded):
            decoded = LogReply.decode(decoded)

        # log.debug(f"\n\n   done._decode_map: {decoded}\n\n")
        return decoded

    @classmethod
    def _decode_key(klass: 'LogPayload', key: Any) -> str:
        # log.debug(f"\n\nlogging._decode_key {type(key)}: {key}\n\n")
        field = None
        if isinstance(key, str):
            try:
                field = LogField(key)
            except ValueError:
                # Not a LogField, so... pass up to parent?
                field = super()._decode_key()
        else:
            # Not a LogField, so... pass up to parent?
            field = super()._decode_key()

        # log.debug(f"\n\n   done._decode_key: {field}\n\n")
        return field

    # ------------------------------
    # To String
    # ------------------------------

    def __str__(self):
        return (
            f"{self.__class__.__name__}: {self.data}"
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(data={self.data})"
        )
