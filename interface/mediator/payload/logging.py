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

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type, NewType, Mapping)
if TYPE_CHECKING:
    from veredi.data.codec import Codec

import enum


from veredi.logs         import log
from veredi.data.codec   import (Encodable,
                                 EncodedComplex,
                                 EncodedSimple)

from .base               import BasePayload, Validity

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

class LogReply(Encodable,
               name_dotted='veredi.interface.mediator.payload.log.reply',
               name_string='reply'):
    '''
    A helper class for logging payload fields from the client. Allows client to
    refuse to comment about specific things.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

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
    def validity(klass: Type['LogReply'],
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

    def encode_simple(self, codec: 'Codec') -> EncodedSimple:
        '''
        Don't support simple for LogReplies.
        '''
        msg = (f"{self.klass} doesn't support encoding to a "
               "simple string.")
        raise NotImplementedError(msg)

    @classmethod
    def decode_simple(klass: Type['LogReply'],
                      data: EncodedSimple,
                      codec: 'Codec') -> 'LogReply':
        '''
        Don't support simple by default.
        '''
        msg = (f"{klass.__name__} doesn't support decoding from a "
               "simple string.")
        raise NotImplementedError(msg)

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        # self.value is "Any", so... Try to decode it. It may already be
        # decoded - this function should handle those cases.
        value = codec.encode(self.value)

        # Build our representation to return.
        return {
            'valid': codec.encode(self.valid),
            'value': value,
        }

    @classmethod
    def decode_complex(klass: Type['LogReply'],
                       data:  EncodedComplex,
                       codec: 'Codec',
                       instance: Optional['LogReply'] = None) -> 'LogReply':
        '''
        Decode ourself from an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        klass.error_for(data, keys=['valid', 'value'])

        valid = codec.decode(Validity, data['valid'])
        value = codec.decode(None, data['value'])

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
            f"{self.klass}(self.valid): {self.value}"
        )

    def __repr__(self):
        return (
            f"{self.klass}({self.value}, valid={self.valid})"
        )


# -----------------------------------------------------------------------------
# Payload Actual
# -----------------------------------------------------------------------------

class LogPayload(BasePayload,
                 name_dotted='veredi.interface.mediator.payload.log.payload',
                 name_string='payload.log'):
    '''
    Payload for a MsgType.LOGGING Message instance.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

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

    # Simple:  BasePayload's are good.

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        # Our data is a dict with LogField enum values as keys and LogReplies
        # or log.Level or something as values.
        encoded = codec.encode_map(self.data)

        # Build our representation to return.
        return {
            'valid': codec.encode(self.valid),
            'data': encoded,
        }

    @classmethod
    def decode_complex(klass: Type['BasePayload'],
                       data:  EncodedComplex,
                       codec: 'Codec',
                       instance: Optional['BasePayload'] = None
                       ) -> 'BasePayload':
        '''
        Decode ourself from an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        klass.error_for(data, keys=['valid', 'data'])

        # Decode the validity field.
        valid = codec.decode(Validity, data['valid'])

        # Decode the data field with our expected key hint of LogField.
        decoded = codec.decode_map(data['data'],
                                   expected=[LogField, log.Level])

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
            f"{self.klass}(self.valid): {self.data}"
        )

    def __repr__(self):
        return (
            f"{self.klass}(data={self.data}, valid={self.valid})"
        )
