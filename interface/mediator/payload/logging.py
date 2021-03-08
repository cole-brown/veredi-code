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

from typing import Optional, Union, Any, NewType, Mapping

import enum


from veredi.logs                 import log
from veredi.base.enum            import EnumEncodeNameMixin
from veredi.data.codec.encodable import (Encodable,
                                         EncodedComplex,
                                         EncodedSimple)

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
class LogField(EnumEncodeNameMixin, enum.Enum):
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

    # ------------------------------
    # Encodable
    # ------------------------------

    @classmethod
    def dotted(klass: 'LogField') -> str:
        return 'veredi.interface.mediator.payload.logfield'

    @classmethod
    def type_field(klass: 'LogField') -> str:
        '''
        A short, unique name for encoding an instance into a field in a dict.
        Override this if you don't like what veredi.base.label.auto() and
        veredi.base.label.munge_to_short() do for your type field.
        '''
        return 'field'


# Enums and that auto-register parameter "dotted='jeff.whatever'" don't
# get along - registering manually...
LogField.register_manually()


# -----------------------------------------------------------------------------
# LogPayload Reply Value from Client
# -----------------------------------------------------------------------------

class LogReply(Encodable, dotted='veredi.interface.mediator.payload.logreply'):
    '''
    A helper class for logging payload fields from the client. Allows client to
    refuse to comment about specific things.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # ------------------------------
    # Constants: Encodable
    # ------------------------------

    _ENCODE_NAME: str = 'reply'
    '''
    Name for this class when encoding/decoding. Will be inside a LogPayload, so
    lacking 'log' is fine.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''

        self.value: Any = None
        '''
        The actual reply. Type and such depend on what the reply actually
        is for...
        '''

        self.valid: Validity = Validity.INVALID
        '''Validity of `self.value`.'''

    def __init__(self,
                 value:            Any,
                 valid:            'Validity' = Validity.INVALID,
                 no_comment_check: Any        = Validity.INVALID,
                 skip_validation:  bool       = False,
                 ) -> None:
        self._define_vars()

        # Just set value
        self.value = value

        # Validate or not?
        if skip_validation:
            # Ok. `valid` is what it is.
            self.valid = valid

        else:
            # Validate this LogReply.
            if valid != Validity.INVALID:
                self.valid = valid
            elif no_comment_check != Validity.INVALID:
                self.valid = self.validity(value, no_comment_check)

            # Error out for invalid LogReplies.
            if self.valid == Validity.INVALID:
                raise ValueError(
                    "LogReply cannot have a `valid` status of INVALID.",
                    value, valid, no_comment_check, self.valid)

    @classmethod
    def validity(klass: 'LogReply',
                 value: Any,
                 no_comment: Any) -> 'Validity':
        '''
        Returns VALID if `value` is not equal to `no_comment`
        or NO_COMMENT otherwise.
        '''
        return (Validity.VALID
                if value != no_comment else
                Validity.NO_COMMENT)

    def get_or_validity(self) -> Union['Validity', Optional[Any]]:
        '''
        If `self.valid` is VALID, returns `self.value`.
        Otherwise return `self.valid`.
        '''
        if self.valid == Validity.VALID:
            return self.value

        return self.valid

    # -------------------------------------------------------------------------
    # Encodable API
    # -------------------------------------------------------------------------

    @classmethod
    def type_field(klass: 'LogReply') -> str:
        return klass._ENCODE_NAME

    def encode_simple(self) -> EncodedSimple:
        '''
        Don't support simple for LogReplies.
        '''
        msg = (f"{self.__class__.__name__} doesn't support encoding to a "
               "simple string.")
        raise NotImplementedError(msg)

    @classmethod
    def decode_simple(klass: 'LogReply',
                      data: EncodedSimple) -> 'LogReply':
        '''
        Don't support simple by default.
        '''
        msg = (f"{klass.__name__} doesn't support decoding from a "
               "simple string.")
        raise NotImplementedError(msg)

    def encode_complex(self) -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        # self.value is "Any", so... Try to decode it. It may already be
        # decoded - this function should handle those cases.
        value = self.encode_any(self.value)

        # Build our representation to return.
        return {
            'valid': self.valid.encode(None),
            'value': value,
        }

    @classmethod
    def decode_complex(klass: 'LogReply',
                       data:  EncodedComplex) -> 'LogReply':
        '''
        Decode ourself from an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        klass.error_for(data, keys=['valid', 'value'])

        valid = Validity.decode(data['valid'])
        value = klass.decode_any(data['value'])

        # Make class with decoded data, skip_validation because this exists and
        # we're just decoding it, not creating a new one.
        decoded = klass(value, valid,
                        skip_validation=True)
        return decoded

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self):
        return (
            f"{self.__class__.__name__}(self.valid): {self.value}"
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}({self.value}, valid={self.valid})"
        )


# -----------------------------------------------------------------------------
# Payload Actual
# -----------------------------------------------------------------------------

class LogPayload(BasePayload,
                 dotted='veredi.interface.mediator.payload.logging'):
    '''
    Payload for a MsgType.LOGGING Message instance.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # ------------------------------
    # Constants: Encodable
    # ------------------------------

    _ENCODE_NAME: str = 'payload.log'
    '''Name for this class when encoding/decoding.'''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 data: Mapping[str, Union[str, int]] = None) -> None:
        # Ignoring validity to start with...
        super().__init__(data, Validity.VALID)

    # -------------------------------------------------------------------------
    # Data Structure
    # -------------------------------------------------------------------------

    @property
    def request(self) -> Mapping[str, str]:
        '''
        Get the Server->Client request portion of the data mapping.
        '''
        return self.data.setdefault(LogField.REQUEST, {})

    @property
    def response(self):
        '''
        Get the Client->Server response portion of the data mapping.
        '''
        return self.data.setdefault(LogField.RESPONSE, {})

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

    # -------------------------------------------------------------------------
    # Server -> Client: Set Requests
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Client -> Server: Logging Report
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Server: Get Logging Report
    # -------------------------------------------------------------------------

    @property
    def report(self) -> Mapping[str, LogReply]:
        '''Returns validity of the entire logging report.'''
        report = self.response.get(LogField.REPORT, None)
        return report

    # -------------------------------------------------------------------------
    # Encodable API (Codec Support)
    # -------------------------------------------------------------------------

    @classmethod
    def type_field(klass: 'LogPayload') -> str:
        return klass._ENCODE_NAME

    # Simple:  BasePayload's are good.

    def encode_complex(self) -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        # Our data is a dict with LogField enum values as keys and LogReplies
        # or log.Level or something as values.
        encoded = self._encode_map(self.data)

        # Build our representation to return.
        return {
            'valid': self.valid.encode(None),
            'data': encoded,
        }

    @classmethod
    def decode_complex(klass: 'BasePayload',
                       data:  EncodedComplex) -> 'BasePayload':
        '''
        Decode ourself from an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        klass.error_for(data, keys=['valid', 'data'])

        # Decode the validity field.
        valid = Validity.decode(data['valid'])

        # Decode the data field with our expected key hint of LogField.
        decoded = klass._decode_map(data['data'],
                                    expected_keys=[LogField])

        # And make our class... Set valid afterwards since LogPayload doesn't
        # care about validity to start with.
        log_payload = klass(decoded)
        log_payload.valid = valid
        return log_payload

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self):
        return (
            f"{self.__class__.__name__}(self.valid): {self.data}"
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(data={self.data}, valid={self.valid})"
        )
