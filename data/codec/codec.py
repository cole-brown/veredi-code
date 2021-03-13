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
import enum
import re
from abc import abstractmethod


from veredi.logs                 import log
from veredi.logs.mixin           import LogMixin
from veredi.base                 import numbers
from veredi.base.const           import SimpleTypes, SimpleTypesTuple
from veredi.base.strings         import pretty
from veredi.base.registrar       import RegisterType
from veredi.base.strings         import label
from veredi.data                 import background
from veredi.data.context         import DataAction, DataOperation
from veredi.data.config.registry import register

from ..exceptions                import EncodableError
from .const                      import (EncodeNull,
                                         EncodeAsIs,
                                         EncodedComplex,
                                         EncodedSimple,
                                         EncodedEither,
                                         Encoding)
from .registry                   import EncodableRegistry
from .encodable                  import Encodable


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

EncodeInput = NewType('EncodeInput',
                      Union[EncodeNull,
                            EncodeAsIs,
                            Encodable,
                            Mapping,
                            enum.Enum])


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'codec', 'codec')
class Codec(LogMixin):
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
        self._name: str = None
        '''The name of the repository.'''

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
        self._name = (codec_name or 'codec').lower()

        # ---
        # Set-Up LogMixin before _configure() so we have logging.
        # ---
        self._log_config(self.dotted())
        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              f"Codec ({self.__class__.__name__}) init...")

        self._configure(config_context)
        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              f"Done with Codec init.")

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''
        Do whatever configuration we can as the base class; sub-classes should
        finish up whatever is needed to set up themselves.
        '''
        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              f"Codec ({self.__class__.__name__}) "
                              "configure...")

        # Set up our background for when it gets pulled in.
        self._make_background()

        self._log_group_multi(self._LOG_INIT,
                              self.dotted(),
                              "Done with Codec configuration.")

    # -------------------------------------------------------------------------
    # Codec Properties/Methods
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
            'dotted': self.dotted(),
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
               target:         EncodeInput,
               in_progress:    Optional[EncodedComplex] = None,
               with_reg_field: bool = True) -> EncodedEither:
        '''
        Encode `target`, depending on target's type and encoding settings. See
        typing of `target` for all encodable types.

        If target is Null or None:
          - returns None

        If target is an Encodable:
          - Encodes using Encodable functionality. See `_encode_encodable()`
            for details.

        If target is a Mapping:
          - Encodes as a dictionary.

        If target is a non-Encodable enum.Enum:
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

        if isinstance(target, Encodable):
            # Encode via its function.
            encoded = self._encode_encodable(target,
                                             in_progress,
                                             with_reg_field)

        elif isinstance(target, collections.abc.Mapping):
            # Encode via our map helper.
            encoded = self.encode_map(target)

        elif isinstance(target, enum.Enum):
            # Assume, if it's an enum.Enum (that isn't an Encodable), that just
            # value is fine. If that isn't fine, the enum can make itself an
            # Encodable.
            encoded = target.value

        elif isinstance(target, SimpleTypesTuple):
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
                          with_reg_field: bool = False) -> EncodedEither:
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
            - ENCODABLE_REG_FIELD: `target.dotted()`
            - ENCODABLE_PAYLOAD_FIELD: `target` encoded data

        Else returns:
          `target` encoded data
        '''
        encoded = None
        if null_or_none(target):
            # Null/None encode to None.
            return encoded

        encoding, encoded = target.encode(self)
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
                return in_progress

            return encoded

        # ---
        # Encoding.COMPLEX
        # ---

        # Put the type somewhere and return encoded data.
        if in_progress is not None:
            # Encode as a sub-field in the provided data.
            in_progress[target.type_field()] = encoded
            return in_progress
        encoded[target.TYPE_FIELD_NAME] = target.type_field()

        # Encode with reg/payload fields if requested.
        if with_reg_field:
            return {
                Encodable.ENCODABLE_REG_FIELD: target.dotted(),
                Encodable.ENCODABLE_PAYLOAD_FIELD: encoded,
            }
        # Or just return the encoded data.
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
        elif isinstance(key, enum.Enum):
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

        elif isinstance(value, Encodable):
            # Encode it with its registry field so we can
            # know what it was encoded as during decoding.
            node = self.encode(value, with_reg_field=True)

        elif isinstance(value, (enum.Enum, enum.IntEnum)):
            # Simple enum and aren't Encodables - just use value.
            node = value.value

        else:
            node = value

        # log.debug(f"\n\n   done._encode_value: {node}\n\n")
        return node

    # -------------------------------------------------------------------------
    # Decoding
    # -------------------------------------------------------------------------

    def decode(self,
               target:          Optional[Type['Encodable']],
               data:            EncodedEither,
               error_squelch:   bool                        = False,
               reg_find_dotted: Optional[str]               = None,
               reg_find_types:  Optional[Type[Encodable]]   = None,
               reg_fallback:    Optional[Type[Encodable]]   = None,
               map_expected:    Iterable[Type['Encodable']] = None
               ) -> Optional['Encodable']:
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
          - reg_fallback: Thing to return if no valid Encodable found for
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
            return None

        # ---
        # Decode target already known?
        # ---
        if target:
            return self._decode_encodable(target, data)

        # ---
        # Does the EncodableRegistry know about it?
        # ---
        try:
            target = self._decode_with_registry(data,
                                                dotted=reg_find_dotted,
                                                data_types=reg_find_types,
                                                error_squelch=error_squelch,
                                                fallback=reg_fallback)
            return target

        except (KeyError, ValueError):
            # Expected exceptions from `_decode_with_registry`...
            # Try more things?
            pass

        # ---
        # Mapping?
        # ---
        if isinstance(data, dict):
            # Decode via our map helper.
            decoded = self.decode_map(data, expected=map_expected)
            return decoded

        # ---
        # Something Simple?
        # ---
        try:
            decoded = self._decode_simple_types(data)
            return decoded
        except EncodableError:
            # Not this either...
            pass

        # ---
        # Ran out of options... Error out.
        # ---
        msg = (f"{self.__class__.__name__}.decode: unknown "
               f"type of data {type(data)}. Cannot decode.")
        error = EncodableError(msg,
                               data={
                                   'target': target,
                                   'data': data,
                                   'error_squelch': error_squelch,
                                   'reg_find_dotted': reg_find_dotted,
                                   'reg_find_types': reg_find_types,
                                   'reg_fallback': reg_fallback,
                               })
        raise self._log_exception(error, msg)

    def _decode_encodable(self,
                          target: Optional[Type['Encodable']],
                          data:   EncodedEither,
                          ) -> Optional['Encodable']:
        '''
        Decode simple or complex `data` input, using it to build an
        instance of the `target` class.

        If `target` is known, it is used to decode and return a new
        `target` instance or None.
        '''
        # ---
        # Wrong data for target?
        # ---
        target.error_for_claim(data)

        # ---
        # Decode it.
        # ---
        encoding, decoded = target.decode(data, self)

        # Right now, same from here on for SIMPLE vs COMPLEX.
        # Keeping split up for parity with `_encode_encodable`, clarity,
        # and such.

        # ---
        # Decode Simply?
        # ---
        if encoding == Encoding.SIMPLE:
            return decoded

        # ---
        # Decode Complexly?
        # ---
        return decoded

    def _decode_with_registry(self,
                              data:          EncodedComplex,
                              dotted:        Optional[str]             = None,
                              data_types:    Optional[Type[Encodable]] = None,
                              error_squelch: bool                      = False,
                              fallback:      Optional[Type[Encodable]] = None,
                              ) -> Optional['Encodable']:
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
                log.debug("decode_with_registry: data is None; using "
                          "fallback. data: {}, fallback: {}",
                          data, fallback)
                return fallback
            # `None` is an acceptable enough value for us... Lots of things are
            # optional. Errors for unexpectedly None things should happen in
            # the caller.
            return None

        # When no ENCODABLE_REG_FIELD, we can't do anything since we don't
        # know how to decode. But only deal with fallback case here. If they
        # don't have a fallback, let it error soon (but not here).
        if (fallback
                and Encodable.ENCODABLE_REG_FIELD not in data):
            # No hint as to what data is - use fallback.
            log.warning("decode_with_registry: No {} in data; using fallback. "
                        "data: {}, fallback: {}",
                        Encodable.ENCODABLE_REG_FIELD,
                        data, fallback)
            return fallback

        # ------------------------------
        # Better KeyError exceptions.
        # ------------------------------
        if not dotted:
            try:
                dotted = data[Encodable.ENCODABLE_REG_FIELD]
            except KeyError:

                # Now we error on the missing decoding hint.
                pretty_data = pretty.indented(data)
                msg = ("decode_with_registry: data has no "
                       f"'{Encodable.ENCODABLE_REG_FIELD}' key.")
                raise log.exception(KeyError(Encodable.ENCODABLE_REG_FIELD,
                                             msg,
                                             data),
                                    msg + " Cannot decode: {}",
                                    pretty_data)

        try:
            encoded_data = data[Encodable.ENCODABLE_PAYLOAD_FIELD]
        except KeyError:
            pretty_data = pretty.indented(data)
            msg = ("decode_with_registry: data has no "
                   f"'{Encodable.ENCODABLE_PAYLOAD_FIELD}' key. "
                   f"Cannot decode: {pretty_data}")
            raise log.exception(KeyError(Encodable.ENCODABLE_REG_FIELD,
                                         msg,
                                         data),
                                msg)

        # ------------------------------
        # Now decode it.
        # ------------------------------

        target = EncodableRegistry.get(encoded_data,
                                       dotted=dotted,
                                       data_type=data_types,
                                       error_squelch=error_squelch,
                                       fallback=fallback)
        return self._decode_encodable(target, data)

    def decode_map(self,
                   mapping: NullNoneOr[Mapping],
                   expected: Iterable[Type['Encodable']] = None
                   ) -> Mapping[str, Any]:
        '''
        Decode a mapping.
        '''
        # log.debug(f"\n\nlogging._decode_map {type(mapping)}: {mapping}\n\n")
        if null_or_none(mapping):
            return None

        # ---
        # Decode the Base Level
        # ---
        decoded = {}
        for key, value in mapping.items():
            field = self._decode_key(key, expected)
            node = self._decode_value(value, expected)
            decoded[field] = node

        # log.debug(f"\n\n   done._decode_map: {decoded}\n\n")
        return decoded

    def _decode_key(self,
                   key: Any,
                   expected: Iterable[Type['Encodable']] = None) -> str:
        '''
        Decode a mapping's key.

        Encodable is pretty stupid. string is only supported type. Override or
        smart-ify if you need support for more key types.
        '''
        # log.debug(f"\n\nlogging._decode_key {type(key)}: {key}\n\n")
        field = None

        # Can we decode to a specified Encodable?
        if expected:
            for encodable in expected:
                # Does this encodable want the key?
                claiming, claim, _ = encodable.claim(key)
                if not claiming:
                    continue
                # Yeah - get it to decode it then.
                field = self.decode(encodable, claim)
                # And we are done; give the decoded field back.
                return field

        # Not an Encodable (or none supplied as expected). Not sure what to do
        # past here, really... Use the string or error, and let the next guy
        # along update it (hello Future Me, probably).
        if isinstance(key, str):
            field = key
        else:
            raise EncodableError(f"Don't know how to decode key: {key}",
                                 None,
                                 data={
                                     'key': key,
                                     'expected': expected,
                                 })

        # log.debug(f"\n\n   done._decode_key: {field}\n\n")
        return field

    def _decode_value(self,
                      value: Any,
                      expected: Iterable[Type['Encodable']] = None
                      ) -> str:
        '''
        Decode a mapping's value.

        Passes `expected` along for continuing the decoding.
        '''
        # log.debug(f"\n\nlogging._decode_value {type(value)}: {value}\n\n")

        node = self.decode(None, value,
                           map_expected=expected)

        # log.debug(f"\n\n   done._decode_value: {node}\n\n")
        return node

    def _decode_simple_types(self,
                             value: Union[str, int, float]) -> SimpleTypes:
        '''
        Decode a simple type.

        Returns the simple type or raises an EncodableError.
        '''
        # Give numbers a shot at Decimals saved as strings before we deal with
        # other kinds of strings.
        encoded = numbers.deserialize(value)
        if encoded:
            return encoded

        elif isinstance(value, str):
            encoded = value
            return encoded

        msg = (f"{self.__class__.__name__}.decode_simple_types: "
               f"'{type(value)}' is not a member of "
               "SimpleTypes and cannot be decoded this way.")
        error = EncodableError(msg, value)
        raise log.exception(error, msg)
