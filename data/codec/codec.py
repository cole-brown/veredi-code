# coding: utf-8

'''
Class for Encoding/Decoding the Encodables.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type, NewType,
                    Dict, List, Iterable, Mapping, Tuple)
from veredi.base.null import NullNoneOr, null_or_none
if TYPE_CHECKING:
    from veredi.base.context        import VerediContext
    from veredi.data.config.context import ConfigContext

import collections
from datetime import datetime
import enum as py_enum


from veredi.logs                 import log
from veredi.logs.mixin           import LogMixin
from veredi.base                 import numbers
from veredi.base.const           import SimpleTypes, SimpleTypesTuple
from veredi.base.strings         import label, pretty
from veredi.base.strings.mixin   import NamesMixin
from veredi                      import time
from veredi.data                 import background
from veredi.data.context         import DataOperation
from veredi.data.registration    import codec as registrar

from ..exceptions                import EncodableError
from .const                      import (EncodeNull,
                                         EncodeAsIs,
                                         EncodedComplex,
                                         EncodedSimple,
                                         EncodedSimpleTuple,
                                         EncodedEither,
                                         Encoding)
from .encodable                  import Encodable
from .                           import enum

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

EncodableAny = NewType('EncodeInput',
                       Union[EncodeNull,
                             EncodeAsIs,
                             Encodable,
                             Mapping,
                             enum.EnumEncode,
                             py_enum.Enum])


EncodableTypes = NewType('EncodableTypes',
                         Union[Encodable,
                               enum.EnumEncode,
                               py_enum.Enum])


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Codec(LogMixin, NamesMixin,
            name_dotted='veredi.codec.codec',
            name_string='codec'):
    '''
    Coder/Decoder for Encodables and the EncodableRegistry.

    Repository gets data from storage to Veredi.
    Serdes gets data from storage format to Python simple data types.
    Codec gets data from simple data types to Veredi classes.

    And the backwards version for saving.
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
                 config_context: Optional['ConfigContext'] = None,
                 codec_name:     Optional[str] = None) -> None:
        '''
        `codec_name` should be short and will be lowercased. It should be
        equivalent to the Serdes names of 'json', 'yaml'... It will be 'codec'
        if not supplied.

        `config_context` is the context being used to set us up.
        '''
        self._define_vars()
        if codec_name:
            self.name = codec_name.lower()

        # ---
        # Set-Up LogMixin before _configure() so we have logging.
        # ---
        self._log_config(self.dotted)
        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              f"Codec ({self.__class__.__name__}) init...")

        self._configure(config_context)
        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              f"Done with Codec init.")

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''
        Do whatever configuration we can as the base class; sub-classes should
        finish up whatever is needed to set up themselves.
        '''
        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              f"Codec ({self.__class__.__name__}) "
                              "configure...")

        # Set up our background for when it gets pulled in.
        self._make_background()

        self._log_group_multi(self._LOG_INIT,
                              self.dotted,
                              "Done with Codec configuration.")

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
                      action:  DataOperation) -> 'VerediContext':
        '''
        Inject our codec data into the context.
        '''
        key = str(background.Name.CODEC)
        meta, _ = self.background
        context[key] = {
            # Push our context data into our sub-context key.
            'meta': meta,
            # And add any extra info.
            'action': action,
        }

        return context

    # -------------------------------------------------------------------------
    # API Encoding
    # -------------------------------------------------------------------------

    def encode(self,
               target:         EncodableAny,
               in_progress:    Optional[EncodedComplex] = None,
               with_reg_field: bool = True) -> EncodedEither:
        '''
        Encode `target`, depending on target's type and encoding settings. See
        typing of `target` for all encodable types.

        If target is Null or None:
          - returns None

        If target is an Encodable or enum with registered Encodable wrapper:
          - Encodes using Encodable functionality. See `_encode_encodable()`
            for details.

        If target is a Mapping:
          - Encodes as a dictionary.

        If target is a non-Encodable py_enum.Enum:
          - Encodes target.value.

        If target is an EncodeAsIs type:
          - Returns as-is; already 'encoded'.

        Else raises an EncodableError.
        '''
        # log.debug(f"{self.__class__.__name__}.encode: {target}")
        encoded = None
        if null_or_none(target):
            # Null/None encode to None.
            return encoded

        # Translate enum to its wrapper if needed/supported.
        if enum.is_encodable(target):
            input_enum = target
            target = enum.wrap(target)
            self._log_data_processing(self.dotted,
                                      "codec.encode: enum found. "
                                      "enum: {} -wrap-> {}",
                                      input_enum, target)

        if isinstance(target, Encodable):
            # Encode via its function.
            encoded = self._encode_encodable(target,
                                             in_progress,
                                             with_reg_field)

        elif isinstance(target, collections.abc.Mapping):
            # Encode via our map helper.
            encoded = self.encode_map(target)

        elif isinstance(target, py_enum.Enum):
            # Assume, if it's a py_enum.Enum (that isn't an Encodable), that
            # just value is fine. If that isn't fine, the enum can make itself
            # an Encodable.
            encoded = target.value

        elif (isinstance(target, time.DateTypesTuple)
              or isinstance(target, SimpleTypesTuple)):
            encoded = self._encode_simple_types(target)

        else:
            msg = (f"Do not know how to encode type '{type(target)}'.")
            error = EncodableError(msg,
                                   data={
                                       'target': target,
                                       'in_progress': in_progress,
                                       'with_reg_field': with_reg_field,
                                   })
            raise self._log_exception(error, msg)

        # log.debug(f"{self.__class__.__name__}.encode: Done. {encoded}")
        return encoded

    def _encode_encodable(self,
                          target:         Optional[Encodable],
                          in_progress:    Optional[EncodedComplex] = None,
                          with_reg_field: bool = True) -> EncodedEither:
        '''
        Encode `target` as a simple or complex encoding, depending on
        `target`.encoding().

        If `target`.encoding() is SIMPLE, encodes to a string/number.

        Otherwise:
          - If `encode_in_progress` is provided, encodes this to a sub-field
            under `target.type_field()`.
          - Else encodes this to a dict and provides `target.type_field()` as
            the value of `target.TYPE_FIELD_NAME`.

        If `with_reg_field` is True, returns:
          An output dict with key/values:
            - ENCODABLE_REG_FIELD: `target.dotted`
            - ENCODABLE_PAYLOAD_FIELD: `target` encoded data

        Else returns:
          `target` encoded data
        '''
        # TODO v://future/2021-03-14T12:27:54
        self._log_data_processing(self.dotted,
                                  '_encode_encodable(): target: {}, '
                                  'in_progress: {}, with_reg_field: {}',
                                  target,
                                  in_progress,
                                  with_reg_field)

        encoded = None
        if null_or_none(target):
            # Null/None encode to None.
            return encoded

        encoding, encoded = target.encode(self)
        # TODO v://future/2021-03-14T12:27:54
        self._log_data_processing(self.dotted,
                                  '_encode_encodable(): Encoded.\n'
                                  '  encoding: {}\n'
                                  '      data: {}',
                                  encoding,
                                  encoded)

        # ---
        # Encoding.SIMPLE
        # ---
        # If we encoded it simply, we're basically done.
        if encoding.has(Encoding.SIMPLE):
            # If there's an in_progress that's been pass in, and we just
            # encoded ourtarget to a string... That's a bit awkward. But I
            # guess do this. Will make weird-ish looking stuff like: 'v.mid':
            # 'v.mid:1'
            if in_progress is not None:
                in_progress[target.type_field()] = encoded
                # TODO v://future/2021-03-14T12:27:54
                self._log_data_processing(
                    self.dotted,
                    '_encode_encodable(): Simple encoding was inserted into '
                    '`in_progress` data and is complete.\n'
                    '        field: {}\n'
                    '  in_progress: {}',
                    target.type_field(),
                    in_progress)
                return in_progress

            # TODO v://future/2021-03-14T12:27:54
            self._log_data_processing(
                self.dotted,
                '_encode_encodable(): Simple encoding is complete.\n'
                '  encoded: {}',
                encoded)
            return encoded

        # ---
        # Encoding.COMPLEX
        # ---

        # Put the type somewhere and return encoded data.
        if in_progress is not None:
            # Encode as a sub-field in the provided data.
            in_progress[target.type_field()] = encoded
            # TODO v://future/2021-03-14T12:27:54
            self._log_data_processing(
                self.dotted,
                '_encode_encodable(): Complex encoding inserted into '
                '`in_progress` data.\n'
                '        field: {}\n'
                '  in_progress: {}',
                target.type_field(),
                in_progress)
            return in_progress

        encoded[target.TYPE_FIELD_NAME] = target.type_field()
        # TODO v://future/2021-03-14T12:27:54
        self._log_data_processing(
            self.dotted,
            '_encode_encodable(): Complex encoding had type-field '
            'added to its data.\n'
            '  field: {}\n'
            '  data: {}',
            target.type_field(),
            encoded)

        # Encode with reg/payload fields if requested.
        if with_reg_field:
            enc_with_reg = {
                Encodable.ENCODABLE_REG_FIELD: target.dotted,
                Encodable.ENCODABLE_PAYLOAD_FIELD: encoded,
            }

            # TODO v://future/2021-03-14T12:27:54
            self._log_data_processing(
                self.dotted,
                '_encode_encodable(): Complex encoding had reg-field '
                'added to its data and is complete.\n'
                '      reg: {}\n'
                '    value: {}\n'
                '  payload: {}\n'
                '    value: {}\n'
                '  encoded: {}',
                Encodable.ENCODABLE_REG_FIELD,
                target.dotted,
                Encodable.ENCODABLE_PAYLOAD_FIELD,
                encoded,
                enc_with_reg)

            return enc_with_reg

        # Or just return the encoded data.
        # TODO v://future/2021-03-14T12:27:54
        self._log_data_processing(
            self.dotted,
            '_encode_encodable(): Complex encoding is complete.\n'
            '  encoded: {}',
            encoded)
        return encoded

    def encode_map(self,
                   encode_from: Mapping,
                   encode_to:   Optional[Mapping] = None,
                   ) -> Mapping[str, Union[str, numbers.NumberTypes, None]]:
        '''
        If `encode_to` is supplied, use that. Else create an empty `encode_to`
        dictionary. Get values in `encode_from` dict, encode them, and put them
        in `encode_to` under an encoded key.

        Returns `encode_to` instance (either the new one we created or the
        existing updated one).
        '''
        if null_or_none(encode_from):
            # Null/None encode to None.
            return None

        if encode_to is None:
            encode_to = {}

        # log.debug(f"\n\nlogging.encode_map: {encode_from}\n\n")
        for key, value in encode_from.items():
            field = self._encode_key(key)
            node = self._encode_value(value)
            encode_to[field] = node

        # log.debug(f"\n\n   done.\nencode_map: {encode_to}\n\n")
        return encode_to

    def _encode_key(self, key: Any) -> str:
        '''
        Encode a dict key.
        '''
        # log.debug(f"\n\nlogging._encode_key: {key}\n\n")
        field = None

        if enum.is_encodable(key):
            input_enum = key
            key = enum.wrap(key)
            self._log_data_processing(self.dotted,
                                      "codec._encode_key: enum found. "
                                      "enum: {} -wrap-> {}",
                                      input_enum, key)

        # If key is an encodable, can it encode into a key?
        if isinstance(key, Encodable):
            if key.encoding().has(Encoding.SIMPLE):
                field = self._encode_encodable(key)
            else:
                msg = (f"{self.__class__.__name__}._encode_key: Encodable "
                       f"'{key}' cannot be encoded into a key value for "
                       "a dict - only Encoding.SIMPLE can be used here.")
                error = EncodableError(msg,
                                       data={
                                           'key': key,
                                       })
                raise log.exception(error, msg)

        # Is key something simple?
        elif isinstance(key, SimpleTypesTuple):
            field = self._encode_simple_types(key)

        # If key is an enum that is not an Encodable, use it's value, I guess?
        elif isinstance(key, py_enum.Enum):
            field = self._encode_simple_types(key.value)

        # If key is a just a number, just use it.
        elif isinstance(key, numbers.NumberTypesTuple):
            field = numbers.serialize(key)

        # No idea... error on it.
        else:
            # # Final guess: stringify it.
            # field = str(key)
            msg = (f"{self.__class__.__name__}._encode_key: Key of type "
                   f"'{type(key)}' is not currently supported for encoding "
                   " into a field for an encoded dictionary.")
            error = EncodableError(msg,
                                   data={
                                       'key': key,
                                   })
            raise log.exception(error, msg)

        # log.debug(f"\n\n   done._encode_key: {field}\n\n")
        return field

    def _encode_simple_types(self,
                             value: SimpleTypes) -> Union[str, int, float]:
        '''
        Encode a simple type.
        '''
        encoded = value
        if isinstance(value, numbers.NumberTypesTuple):
            # Numbers have to serialize their Decimals.
            encoded = numbers.serialize(value)
        elif isinstance(value, str):
            encoded = value
        else:
            msg = (f"{self.__class__.__name__}._encode_simple_types: "
                   f"'{type(value)}' is not a member of "
                   "SimpleTypes and cannot be encoded this way.")
            error = EncodableError(msg, value)
            raise log.exception(error, msg)

        return encoded

    def _encode_value(self, value: Any) -> str:
        '''
        Encode a dict value.

        If value is:
          - dict or encodable: Step into them for encoding.
          - enum: Use the enum's value.

        Else assume it is already encoded.
        '''
        # log.debug(f"\n\nlogging._encode_value: {value}\n\n")
        node = None
        if isinstance(value, dict):
            node = self.encode_map(value)

        elif (isinstance(value, Encodable)
              or enum.is_encodable(value)):
            # Encode it with its registry field so we can
            # know what it was encoded as during decoding.
            node = self.encode(value, with_reg_field=True)

        elif isinstance(value, py_enum.Enum):
            # An enum that isn't registered as Encodable - just use value.
            node = value.value

        else:
            node = value

        # log.debug(f"\n\n   done._encode_value: {node}\n\n")
        return node

    # -------------------------------------------------------------------------
    # Decoding
    # -------------------------------------------------------------------------

    def _decode_enum_check(self,
                           target: Optional[EncodableTypes]
                           ) -> Type[Encodable]:
        '''
        Convert `target` to its Encodable EnumWrap if it is an enum.

        Return as-is otherwise.
        '''
        # Allow target of either the Enum type or the EnumWrap type
        # as target.
        if enum.is_encodable(target):  # Given the enum type as the target?
            # Target is enum; translate to its EnumWrap class for decoding.
            input_enum = target
            target = enum.wrap(target)
            self._log_data_processing(self.dotted,
                                      "codec._decode_enum_check: enum found. "
                                      "enum: {} -wrap-> {}",
                                      input_enum, target)

        elif enum.is_decodable(target):  # Given the EnumWrap as target?
            # EnumWrap is what we need - no change.
            self._log_data_processing(self.dotted,
                                      "codec._decode_enum_check: EnumWrap found. "
                                      "EnumWrap: {} - Use as-is.",
                                      target)

        return target

    def _decode_finalize(self, result: Any) -> Any:
        '''
        Finalize decoding by e.g. converting EnumWrap to its enum value.
        '''
        finalized = result
        if result and enum.needs_unwrapped(result):
            finalized = enum.unwrap(result)
        self._log_data_processing(self.dotted,
                                  "codec._decode_finalize: "
                                  "{} -> {}",
                                  result, finalized)
        return finalized

    def decode(self,
               target:          Optional[EncodableTypes],
               data:            EncodedEither,
               error_squelch:   bool                           = False,
               reg_find_dotted: Optional[str]                  = None,
               reg_find_types:  Optional[Type[Encodable]]      = None,
               map_expected:    Iterable[Type[EncodableTypes]] = None,
               fallback:        Optional[Type[Any]]            = None
               ) -> Optional[Any]:
        '''
        Decode simple or complex `data` input, using it to build an
        instance of the `target` class.

        If `target` is known, it is used to decode and return a new
        `target` instance or None.

        If `target` is unknown (and therefore None), `data` must exist and
        have keys:
          - Encodable.ENCODABLE_REG_FIELD
          - Encodable.ENCODABLE_PAYLOAD_FIELD
        Raises KeyError if not present.

        Takes EncodedComplex `data` input, and uses
        `Encodable.ENCODABLE_REG_FIELD` key to find registered Encodable to
        decode `data[Encodable.ENCODABLE_PAYLOAD_FIELD]`.

        These keyword args are used for getting Encodables from the
        EncodableRegistry:
          - reg_find_dotted: Encodable's dotted registry string to use for
            searching for the encodable that can decode the data.
          - reg_find_types: Search for Encodables of this class or its
            subclasses that can decode the data.
          - fallback: Thing to return if no valid Encodable found for
            decoding.

        If data is a map with several expected Encodables in it, supply
        those in `map_expected` or just use `decode_map()`.

        `error_squelch` will try to only raise the exception, instead of
        raising it through log.exception().
        '''
        # ---
        # Decode at all?
        # ---
        if null_or_none(data):
            # Can't decode nothing; return nothing.
            self._log_data_processing(
                self.dotted,
                "decode: Cannot decode nothing:\n"
                "  data: {}",
                data)
            return self._decode_finalize(None)

        # ---
        # Decode target already known?
        # ---
        if target:
            self._log_data_processing(
                self.dotted,
                "decode: Attempting to decode via Encodable:\n"
                "  data: {}",
                data)
            decoded = self._decode_encodable(target, data)

            self._log_data_processing(
                self.dotted,
                "decode: Decode via Encodable returned:\n"
                "  decoded: {}",
                decoded)
            return self._decode_finalize(decoded)

        self._log_data_processing(
            self.dotted,
            "decode: No target...\n"
            "  type: {}\n"
            "  data: {}",
            type(data),
            data)

        # ---
        # Is it an Encoding.SIMPLE?
        # ---
        if isinstance(data, EncodedSimpleTuple):
            self._log_data_processing(
                self.dotted,
                "decode: Attempting to decode simply encoded data...\n"
                "  data: {}",
                data)
            decoded = self._decode_simple(data, None)

            if decoded:
                self._log_data_processing(
                    self.dotted,
                    "decode: Decoded simply encoded data to:\n"
                    "  decoded: {}",
                    decoded)
                return self._decode_finalize(decoded)

            # Else: not this... Keep looking.
            self._log_data_processing(
                self.dotted,
                "decode: Data is not Encoding.SIMPLE. Continuing...")

        # ---
        # Does the EncodableRegistry know about it?
        # ---
        try:
            self._log_data_processing(
                self.dotted,
                "decode: Attempting to decode with registry...\n"
                "  reg_find_dotted: {}\n"
                "   reg_find_types: {}\n"
                "    error_squelch: {}\n\n"
                "  data:\n{}\n"
                "  fallback:\n{}\n",
                reg_find_dotted,
                reg_find_types,
                error_squelch,
                log.format_pretty(data, prefix='    '),
                log.format_pretty(fallback, prefix='    '))
            decoded = self._decode_with_registry(data,
                                                 dotted=reg_find_dotted,
                                                 data_types=reg_find_types,
                                                 error_squelch=error_squelch,
                                                 fallback=fallback)
            if self._log_will_output(log.Group.DATA_PROCESSING):
                self._log_data_processing(
                    self.dotted,
                    "decode: Decode with registry returned:\n"
                    "  type: {}\n"
                    "{}",
                    type(decoded),
                    log.format_pretty(decoded,
                                      prefix='  '))
            return self._decode_finalize(decoded)

        except (KeyError, ValueError, TypeError):
            # Expected exceptions from `_decode_with_registry`...
            # Try more things?
            pass

        # ---
        # Mapping?
        # ---
        if isinstance(data, dict):
            self._log_data_processing(
                self.dotted,
                "decode: Attempting to decode mapping...\n"
                "  map_expected: {}\n"
                "          data: {}",
                map_expected,
                data)
            # Decode via our map helper.
            decoded = self.decode_map(data, expected=map_expected)
            self._log_data_processing(
                self.dotted,
                "decode: Decoded mapping returned:\n"
                "  decoded: {}",
                decoded)
            return self._decode_finalize(decoded)

        # ---
        # Something Basic?
        # ---
        try:
            self._log_data_processing(
                self.dotted,
                "decode: Attempting to decode basic data type...\n"
                "  data: {}",
                data)
            decoded = self._decode_basic_types(data)

            self._log_data_processing(
                self.dotted,
                "decode: Decoded basic data to:\n"
                "  decoded: {}",
                decoded)
            return self._decode_finalize(decoded)
        except EncodableError:
            # Not this either...
            pass

        # ---
        # Ran out of options... Return fallback or error out.
        # ---
        if fallback:
            self._log_data_processing(
                self.dotted,
                "decode: No decoding known for data; returning fallback:\n"
                "  fallback: {}",
                fallback)
            return self._decode_finalize(fallback)

        msg = (f"{self.__class__.__name__}.decode: unknown "
               f"type of data {type(data)}. Cannot decode.")
        error = EncodableError(msg,
                               data={
                                   'target': target,
                                   'data': data,
                                   'error_squelch': error_squelch,
                                   'reg_find_dotted': reg_find_dotted,
                                   'reg_find_types': reg_find_types,
                                   'fallback': fallback,
                               })
        raise self._log_exception(error, msg)

    def _decode_encodable(self,
                          target: Optional[Type[Encodable]],
                          data:   EncodedEither,
                          ) -> Union[Encodable,
                                     enum.EnumEncode,
                                     None]:
        '''
        Decode simple or complex `data` input, using it to build an
        instance of the `target` class.

        If `target` is known, it is used to decode and return a new
        `target` instance or None.
        '''
        self._log_data_processing(
            self.dotted,
            "_decode_encodable will be decoding data to target '{}'.\n"
            "  data: {}",
            target,
            data)

        # ---
        # Wrong data for target?
        # ---
        target = self._decode_enum_check(target)
        target.error_for_claim(data)

        # ---
        # Decode it.
        # ---
        encoding, decoded = target.decode(data, self, None)

        self._log_data_processing(
            self.dotted,
            "_decode_encodable decoded target '{}' to: {}",
            target,
            decoded)

        if enum.needs_unwrapped(decoded):
            self._log_data_processing(
                self.dotted,
                "_decode_encodable unwrapped decoded EnumWrap "
                "'{}' to: {} {}",
                decoded,
                type(decoded.enum),
                decoded.enum)
            decoded = decoded.enum

        # Right now, same from here on for SIMPLE vs COMPLEX.
        # Keeping split up for parity with `_encode_encodable`, clarity,
        # and such.

        # ---
        # Decode Simply?
        # ---
        if encoding == Encoding.SIMPLE:
            self._log_data_processing(
                self.dotted,
                "_decode_encodable {} decoding completed.\n"
                "  type():  {}\n"
                "  decoded: {}",
                encoding,
                type(decoded),
                decoded)
            return decoded

        # ---
        # Decode Complexly?
        # ---
        self._log_data_processing(
            self.dotted,
            "_decode_encodable {} decoding completed.\n"
            "  type():  {}\n"
            "  decoded: {}",
            encoding,
            type(decoded),
            decoded)
        return decoded

    def _decode_simple(self,
                       data:      EncodedSimple,
                       data_type: Optional[Type[Encodable]]
                       ) -> Optional[Encodable]:
        '''
        Input data must be a string.

        Will look for an Encodable that can claim the simple encoding, and then
        use that to decode it if found.

        Will return None if no Encodable target is found.
        '''
        self._log_data_processing(self.dotted,
                                  "_decode_simple:\n"
                                  "  data_type: {}\n"
                                  "  data: {}",
                                  data_type, data)
        if not data:
            self._log_data_processing(self.dotted,
                                      "_decode_simple:\n"
                                      "  no data; returning None")
            return None

        target = registrar.codec.simple(data,
                                        data_type=data_type)
        if not target:
            self._log_data_processing(self.dotted,
                                      "_decode_simple: "
                                      "codec.simple() found no target for:\n"
                                      "  data_type: {}\n"
                                      "  data: {}",
                                      data_type, data)
            return None

        self._log_data_processing(self.dotted,
                                  "_decode_simple: "
                                  "codec.simple() found target {}; "
                                  "decoding...",
                                  target)
        return self._decode_encodable(target, data)

    def _decode_with_registry(self,
                              data:          EncodedComplex,
                              dotted:        Optional[str]             = None,
                              data_types:    Optional[Type[Encodable]] = None,
                              error_squelch: bool                      = False,
                              fallback:      Optional[Type[Encodable]] = None,
                              ) -> Optional[Encodable]:
        '''
        Input `data` must have keys:
          - Encodable.ENCODABLE_REG_FIELD
          - Encodable.ENCODABLE_PAYLOAD_FIELD
        Raises KeyError if not present.

        Takes EncodedComplex `data` input, and uses
        `Encodable.ENCODABLE_REG_FIELD` key to find registered Encodable to
        decode `data[Encodable.ENCODABLE_PAYLOAD_FIELD]`.

        All the keyword args are forwarded to EncodableRegistry.get() (e.g.
        'data_types').

        Return a new `target` instance.
        '''
        # ------------------------------
        # Fallback early.
        # ------------------------------
        if data is None:
            # No data at all. Use either fallback or None.
            if fallback:
                self._log_data_processing(
                    self.dotted,
                    "decode_with_registry: data is None; using "
                    "fallback.\n"
                    "  data: {}\n"
                    "  fallback:\n"
                    "{}",
                    data,
                    log.format_pretty(fallback, prefix='    '))
                return fallback
            # `None` is an acceptable enough value for us... Lots of things are
            # optional. Errors for unexpectedly None things should happen in
            # the caller.
            self._log_data_processing(
                self.dotted,
                "decode_with_registry: data is None; no "
                "fallback. Returning None.",
                data, fallback)
            return None

        self._log_data_processing(
            self.dotted,
            "decode_with_registry: Decoding...\n"
            "  dotted: {}\n"
            "  data_types: {}\n"
            "  error_squelch: {}\n"
            "  data:\n{}\n"
            "  fallback:\n{}\n",
            dotted,
            data_types,
            error_squelch,
            log.format_pretty(data, prefix='    '),
            log.format_pretty(fallback, prefix='    '))

        # When no ENCODABLE_REG_FIELD, we can't do anything since we don't
        # know how to decode. But only deal with fallback case here. If they
        # don't have a fallback, let it error soon (but not here).
        if (fallback
                and Encodable.ENCODABLE_REG_FIELD not in data):
            # No hint as to what data is - use fallback.
            self._log_data_processing(
                self.dotted,
                "decode_with_registry: No {} in data; using fallback. "
                "data: {}, fallback: {}",
                Encodable.ENCODABLE_REG_FIELD,
                data, fallback,
                log_minimum=log.Level.WARNING)
            return fallback

        # ------------------------------
        # Better KeyError exceptions.
        # ------------------------------
        if not dotted:
            try:
                dotted = data[Encodable.ENCODABLE_REG_FIELD]
                self._log_data_processing(
                    self.dotted,
                    "decode_with_registry: No 'dotted' provided; "
                    "got dotted from data: {}",
                    dotted)

            except KeyError:
                # Error on the missing decoding hint.
                self._log_data_processing(
                    self.dotted,
                    "decode_with_registry: No 'dotted' provided "
                    "and none in data!")
                # Don't `self._log_exception()`... exceptions expected.
                raise KeyError(Encodable.ENCODABLE_REG_FIELD,
                               ("decode_with_registry: data has no "
                                f"'{Encodable.ENCODABLE_REG_FIELD}' key."),
                               data)

            except TypeError:
                # Error on the missing decoding hint.
                self._log_data_processing(
                    self.dotted,
                    "decode_with_registry: No 'dotted' provided. "
                    "...and data is not a dict type?\n"
                    "  type: {}",
                    type(data))
                # Don't `self._log_exception()`... exceptions expected.
                raise TypeError(Encodable.ENCODABLE_REG_FIELD,
                                ("decode_with_registry: data is not dict "
                                 "type? Cannot check for "
                                 f"'{Encodable.ENCODABLE_REG_FIELD}' key."),
                                data)

        try:
            encoded_data = data[Encodable.ENCODABLE_PAYLOAD_FIELD]
            self._log_data_processing(
                self.dotted,
                "decode_with_registry: Pulled encoded data field from data.\n"
                "  encoded_data: {}",
                encoded_data)

        except KeyError:
            self._log_data_processing(
                self.dotted,
                "decode_with_registry: No payload in encoded_data?\n"
                "  payload field name: {}\n"
                "  encoded_data: {}",
                Encodable.ENCODABLE_PAYLOAD_FIELD,
                encoded_data)
            # Don't `self._log_exception()`... exceptions expected.
            raise KeyError(Encodable.ENCODABLE_PAYLOAD_FIELD,
                           ("decode_with_registry: data has no "
                            f"'{Encodable.ENCODABLE_PAYLOAD_FIELD}' key. "
                            "Cannot decode data.."),
                           data)

        except TypeError:
            self._log_data_processing(
                self.dotted,
                "decode_with_registry: ...encoded_data is not a dict type?\n"
                "  type: {}"
                "  encoded_data: {}",
                type(encoded_data),
                encoded_data)
            # Don't `self._log_exception()`... exceptions expected.
            raise KeyError(Encodable.ENCODABLE_PAYLOAD_FIELD,
                           ("decode_with_registry: data is not dict type? "
                            f"Cannot find '{Encodable.ENCODABLE_PAYLOAD_FIELD}' "
                            "key."),
                           data)

        # ------------------------------
        # Now decode it.
        # ------------------------------

        self._log_data_processing(
            self.dotted,
            "decode_with_registry: Checking registrar for:"
            "  dotted: {}\n"
            "  data_type: {}\n"
            "  encoded_data: {}",
            dotted,
            data_types,
            encoded_data)
        target = registrar.codec.get(encoded_data,
                                     dotted=dotted,
                                     data_type=data_types,
                                     error_squelch=error_squelch,
                                     fallback=fallback)
        self._log_data_processing(
            self.dotted,
            "decode_with_registry: registrar returned target: {}",
            target)
        decoded = self._decode_encodable(target, data)
        return decoded


    def decode_map(self,
                   mapping:  NullNoneOr[Mapping],
                   expected: Iterable[Type[Encodable]] = None
                   ) -> Mapping[str, Any]:
        '''
        Decode a mapping.
        '''
        if null_or_none(mapping):
            self._log_data_processing(
                self.dotted,
                "decode_map: Cannot decode nothing.\n"
                "  expecting: {}\n"
                "  mapping: {}",
                expected,
                log.format_pretty(mapping,
                                  prefix='  '))
            return None

        self._log_data_processing(
            self.dotted,
            "decode_map: Decoding...\n"
            "  expecting: {}\n"
            "{}",
            expected,
            log.format_pretty(mapping,
                              prefix='  '))

        # ---
        # Decode the Base Level
        # ---
        decoded = {}
        for key, value in mapping.items():
            field = self._decode_key(key, expected)
            node = self._decode_value(value, expected)
            decoded[field] = node

        self._log_data_processing(
            self.dotted,
            "decode_map: Decoded to:\n"
            "  decoded: {}",
            decoded)
        return decoded

    def _decode_key(self,
                    key:      Any,
                    expected: Iterable[Type[Encodable]] = None) -> str:
        '''
        Decode a mapping's key.

        Encodable is pretty stupid. string is only supported type. Override or
        smart-ify if you need support for more key types.
        '''
        self._log_data_processing(
            self.dotted,
            "decode_key:\n"
            "  expecting: {}\n"
            "  key: {}",
            expected,
            key)
        field = None

        # Can we decode to a specified Encodable?
        if expected:
            for encodable in expected:
                encodable = self._decode_enum_check(encodable)
                # Does this encodable want the key?
                claiming, claim, _ = encodable.claim(key)
                if not claiming:
                    continue

                self._log_data_processing(
                    self.dotted,
                    "decode_key:\n"
                    "  Found expected to use as target: {}",
                    encodable)

                # Yeah - get it to decode it then.
                field = self.decode(encodable, claim,
                                    map_expected=expected)
                self._log_data_processing(
                    self.dotted,
                    "decode_key:\n"
                    "  Decoded key to: {}",
                    field)
                # And we are done; give the decoded field back.
                return field

        # Not an Encodable (or none supplied as expected). Not sure what to do
        # past here, really... Use the string or error, and let the next guy
        # along update it (hello Future Me, probably).
        if isinstance(key, str):
            field = key
            self._log_data_processing(
                self.dotted,
                "decode_key:\n"
                "  Key is string; use as-is: {}",
                field)
        else:
            self._log_data_processing(
                self.dotted,
                "decode_key:\n"
                "  Key is un-decodable?\n"
                "  type: {}\n"
                "  key: {}",
                type(key),
                key)
            raise EncodableError(f"Don't know how to decode key: {key}",
                                 None,
                                 data={
                                     'key': key,
                                     'expected': expected,
                                 })

        return field

    def _decode_value(self,
                      value: Any,
                      expected: Iterable[Type[Encodable]] = None
                      ) -> str:
        '''
        Decode a mapping's value.

        Passes `expected` along for continuing the decoding.
        '''
        self._log_data_processing(
            self.dotted,
            "decode_value:\n"
            "  Decoding...\n"
            "  expecting: {}\n"
            "  value: {}",
            expected,
            value)

        node = self.decode(None, value,
                           map_expected=expected)
        self._log_data_processing(
            self.dotted,
            "decode_value:\n"
            "  Decoded value to:\n"
            "    {}",
            node)

        return node

    def _decode_basic_types(self,
                            value: Union[datetime, str, int, float]
                            ) -> SimpleTypes:
        '''
        'Decode' a basic type. Generally as itself.

        Returns the simple type or raises an EncodableError.
        '''
        self._log_data_processing(
            self.dotted,
            "decode_basic_types:\n"
            "  Decoding...\n"
            "    type: {}\n"
            "    value: {}",
            type(value),
            value)

        if time.deserialize_claim(value):
            decoded = time.deserialize(value)
            self._log_data_processing(
                self.dotted,
                "decode_basic_types:\n"
                "  Decoded via time."
                "    type: {}\n"
                "    decoded: {}",
                type(decoded),
                decoded)
            return decoded


        # Give numbers a shot at Decimals saved as strings before we deal with
        # other kinds of strings.
        try:
            decoded = numbers.deserialize(value)
            self._log_data_processing(
                self.dotted,
                "decode_basic_types:\n"
                "  Decoded via numbers."
                "    type: {}\n"
                "    decoded: {}",
                type(decoded),
                decoded)
            return decoded
        except Exception as error:
            self._log_exception(
                error,
                "decode_basic_types:\n"
                "  `numbers.deserialize()` raised exception on:"
                "    type: {}\n"
                "    decoded: {}",
                type(decoded),
                decoded)
            raise

        if decoded:
            return decoded

        if isinstance(value, str):
            decoded = value
            self._log_data_processing(
                self.dotted,
                "decode_basic_types:\n"
                "  Is a string; return as-is."
                "    type: {}\n"
                "    decoded: '{}'",
                type(decoded),
                decoded)
            return decoded

        self._log_data_processing(
            self.dotted,
            "decode_basic_types:\n"
            "  Unknown/unclaimed value; erroring."
            "    type: {}\n"
            "    value: {}",
            type(value),
            value)
        msg = (f"{self.__class__.__name__}.decode_basic_types: "
               f"'{type(value)}' is not a known 'basic' type "
               "and cannot be decoded.")
        error = EncodableError(msg, value)
        raise self._log_exception(error, msg)
