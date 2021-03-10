# coding: utf-8

'''
Class for Encoding/Decoding the Encodables.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type, Dict, List,
                    Iterable, Mapping, Tuple)
from veredi.base.null import null_or_none
if TYPE_CHECKING:
    from veredi.base.context        import VerediContext
    from veredi.data.config.context import ConfigContext

from abc import abstractmethod
import enum
import re


from veredi.logs                 import log
from veredi.logs.mixin           import LogMixin
from veredi.base                 import numbers
from veredi.base.strings         import pretty
from veredi.base.registrar       import RegisterType
from veredi.base.strings         import label
from veredi.data                 import background
from veredi.data.context         import DataAction, DataOperation
from veredi.data.config.registry import register

from ..exceptions                import EncodableError
from .const                      import (EncodedComplex,
                                         EncodedSimple,
                                         EncodedEither,
                                         Encoding)
from .registry                   import EncodableRegistry
from .encodable                  import Encodable


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


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

    def encode_data(self,
                    data:  Any) -> Optional[EncodedEither]:
        '''
        Tries to encode `data`.

        If `data` is:
          - dict or encodable: Step in to them for encoding.
          - enum: Use the enum's value.

        Else assume it is already encoded and return as-is.
        '''
        # log.debug(f"{self.__class__.__name__}.encode_any: {data}")

        encoded = None
        if isinstance(data, Encodable):
            # Encode via its function.
            encoded = self.encode(data, None)  # TODO: with_reg_field=False?

        elif isinstance(data, dict):
            # Encode via our map helper.
            encoded = self.encode_map(data)

        elif isinstance(data, enum.Enum):
            # Assume, if it's an enum.Enum (that isn't an Encodable), that just
            # value is fine. If that isn't fine, the enum can make itself an
            # Encodable.
            encoded = data.value

        else:
            # Assume that whatever it is, it is decoded.
            if not isinstance(data, (str, numbers.NumberTypesTuple)):
                log.warning(f"{self.__class__.__name__}.encode_any: unknown "
                            f"type of data {type(data)}. Assuming it's "
                            "decoded already or doesn't need to be. {}",
                            data)
            encoded = data

        # log.debug(f"{self.__class__.__name__}.encode_any: Done. {encoded}")
        return encoded

    def encode(self,
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
            the value of `target._TYPE_FIELD_NAME`.

        If `with_reg_field` is True, returns:
          An output dict with key/values:
            - _ENCODABLE_REG_FIELD: `target.dotted()`
            - _ENCODABLE_PAYLOAD_FIELD: `target` encoded data

        Else returns:
          `target` encoded data
        '''
        encoded = None
        if null_or_none(target):
            # Null/None encode to None.
            return encoded

        # TODO: if in_progress is not None:
        # and if encode simple, instead encode as:
        #   encode_in_progress[type_field] = simple_value

        # Should we encode simply by default?
        if target.encoding().has(Encoding.SIMPLE):
            # Yes. Do that thing.
            simple = target.encode_simple()

            # If there's an in_progress that's been pass in, and we just
            # encoded ourtarget to a string... That's a bit awkward. But I
            # guess do this. Will make weird-ish looking stuff like: 'v.mid':
            # 'v.mid:1'
            if in_progress is not None:
                in_progress[target.type_field()] = simple
                return in_progress

            return simple

        # No. Encode everything we know...
        # ...which as the base class isn't much.
        encoded = target.encode_complex()

        # Put the type somewhere and return encoded data.
        if in_progress is not None:
            # Encode as a sub-field in the provided data.
            in_progress[target.type_field()] = encoded
            return in_progress

        # Encode as a base-level dict.
        encoded[target._TYPE_FIELD_NAME] = target.type_field()
        if with_reg_field:
            return {
                Encodable._ENCODABLE_REG_FIELD: target.dotted(),
                Encodable._ENCODABLE_PAYLOAD_FIELD: target.encode(None),
            }
        else:
            return encoded

    # def encode_or_none(...):
    #     TODO: SWITCH TO JUST `encode()`

    # def encode_with_registry(self) -> EncodedComplex:
    #     TODO: SWITCH TO JUST `encode()`

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
        if encode_to is None:
            encode_to = {}

        # log.debug(f"\n\nlogging._encode_map: {encode_from}\n\n")
        for key, value in encode_from.items():
            field = self.encode_key(key)
            node = self.encode_value(value)
            encode_to[field] = node

        # log.debug(f"\n\n   done._encode_map: {encode_to}\n\n")
        return encode_to

    def encode_key(self, key: Any) -> str:
        '''
        Encode a dict key.
        '''
        # log.debug(f"\n\nlogging._encode_key: {key}\n\n")
        field = None

        # If key is an encodable, can it encode into a key?
        if isinstance(key, Encodable):
            if key.encode_simple():
                field = key.encode(None)
            else:
                msg = (f"{self.__class__.__name__}.encode_key: Encodable "
                       f"'{key}' cannot be encoded into a key value for "
                       "a dict.")
                error = AttributeError(msg, key, self)
                raise log.exception(error, msg)

        # If key is a str, just use it.
        elif isinstance(key, str):
            field = key

        # If key is an enum that is not an Encodable, use it's value, I guess?
        elif isinstance(key, enum.Enum):
            field = key.value

        # Final guess: stringify it.
        else:
            field = str(key)

        # log.debug(f"\n\n   done._encode_key: {field}\n\n")
        return field

    def encode_value(self, value: Any) -> str:
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

    # def decode_with_registry(self) -> EncodedComplex:
    #     TODO: SWITCH TO JUST `decode()`

    def decode(self,
               target:          Optional[Type['Encodable']],
               data:            EncodedEither,
               error_squelch:   bool                      = False,
               reg_find_dotted: Optional[str]             = None,
               reg_find_types:  Optional[Type[Encodable]] = None,
               reg_fallback:    Optional[Type[Encodable]] = None,
               ) -> Optional['Encodable']:
        '''
        Decode simple or complex `data` input, using it to build an
        instance of the `target` class.

        If `target` is known, it is used to decode and return a new
        `target` instance or None.

        If `target` is unknown (and therefore None), `data` must exist and
        have keys:
          - Encodable._ENCODABLE_REG_FIELD
          - Encodable._ENCODABLE_PAYLOAD_FIELD
        Raises KeyError if not present.

        Takes EncodedComplex `data` input, and uses
        `Encodable._ENCODABLE_REG_FIELD` key to find registered Encodable to
        decode `data[Encodable._ENCODABLE_PAYLOAD_FIELD]`.

        These keyword args are used for getting Encodables from the
        EncodableRegistry:
          - reg_find_dotted: Encodable's dotted registry string to use for
            searching for the encodable that can decode the data.
          - reg_find_types: Search for Encodables of this class or its
            subclasses that can decode the data.
          - reg_fallback: Thing to return if no valid Encodable found for
            decoding.

        `error_squelch` will try to only raise the exception, instead of
        raising it through log.exception().
        '''
        # ---
        # Decode at all?
        # ---
        if data is None:
            # Can't decode nothing; return nothing.
            return None

        # ---
        # Decode target known?
        # ---
        if target is not None:
            return self._decode_with_target(target, data, error_squelch)

        # ---
        # Decode with registry?
        # ---
        return self._decode_with_registry(data,
                                          dotted=reg_find_dotted,
                                          data_types=reg_find_types,
                                          error_squelch=error_squelch,
                                          fallback=reg_fallback)

    def _decode_any(self,
                    data:  EncodedComplex,
                    expected_keys: Iterable[Type['Encodable']] = None) -> Any:
        '''
        Tries to decode `data`.

        If `data` is:
          - encodable: Must be registered to EncodableRegistry in order to
            decode properly.
          - dict: Decode with decode_map() using `expected_keys`. Returns
            another dict!

        Else assume it is already decoded or is basic data and returns it
        as-is.
        '''
        # log.debug(f"{self.__class__.__name__}.decode_any: {data}")

        # First... is it a registered Encodable?
        decoded = None
        try:
            # Don't want this to log the exception if it happens. We're ok with
            # it happening.
            decoded = EncodableRegistry.get(data,
                                            error_squelch=True)
            return decoded

        except ValueError:
            # Nope. But that's fine. Try other things.
            pass

        # Next... dict?
        if isinstance(data, dict):
            # Decode via our map helper.
            decoded = self.decode_map(data, expected_keys)

        # Finally... I dunno. Leave as-is?
        else:
            # Warn if not a type we've thought about.
            if (not isinstance(data, numbers.NumberTypesTuple)
                    and not isinstance(data, str)):
                log.warning(f"{self.__class__.__name__}.decode_any: unknown "
                            f"type of data {type(data)}. Assuming it's "
                            "decoded already or doesn't need to be. {}",
                            data)
            # Assume that whatever it is, it is decoded.
            decoded = data

        # log.debug(f"{self.__class__.__name__}.decode_any: Done. {decoded}")
        return decoded

    def _decode_with_target(self,
                            target: Optional[Type['Encodable']],
                            data:   EncodedEither,
                            error_squerch: bool) -> Optional['Encodable']:
        '''
        Decode simple or complex `data` input, using it to build an
        instance of the `target` class.

        If `target` is known, it is used to decode and return a new
        `target` instance or None.
        '''
        # ---
        # Decode Simply?
        # ---
        if target.encoded_as(data) == Encoding.SIMPLE:
            # Yes. Do that thing.
            return target.decode_simple(data)

        # Does this class only do simple encode/decode?
        if not target.encoding().has(Encoding.COMPLEX):
            msg = (f"Cannot decode data to '{target.__name__}'. "
                   "Class only encodes simply and didn't match data.")
            error = TypeError(data, msg)
            if error_squerch:
                raise error
            else:
                raise log.exception(error,
                                    msg + ' data: {}',
                                    data)

        # ---
        # Decode Complexly?
        # ---
        # Maybe; try claiming it to see if it has our type field in the right
        # place?
        target.error_for_claim(data)

        # Ok; yes. Get our field out of data and pass on to
        # self.decode_complex().
        _, claim, _ = target.claim(data)
        return target.decode_complex(claim)

    def _decode_with_registry(self,
                              data:          EncodedComplex,
                              dotted:        Optional[str]             = None,
                              data_types:    Optional[Type[Encodable]] = None,
                              error_squelch: bool                      = False,
                              fallback:      Optional[Type[Encodable]] = None,
                              ) -> Optional['Encodable']:
        '''
        Input `data` must have keys:
          - Encodable._ENCODABLE_REG_FIELD
          - Encodable._ENCODABLE_PAYLOAD_FIELD
        Raises KeyError if not present.

        Takes EncodedComplex `data` input, and uses
        `Encodable._ENCODABLE_REG_FIELD` key to find registered Encodable to
        decode `data[Encodable._ENCODABLE_PAYLOAD_FIELD]`.

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

        # When no _ENCODABLE_REG_FIELD, we can't do anything since we don't
        # know how to decode. But only deal with fallback case here. If they
        # don't have a fallback, let it error soon (but not here).
        if (fallback
                and Encodable._ENCODABLE_REG_FIELD not in data):
            # No hint as to what data is - use fallback.
            log.warning("decode_with_registry: No {} in data; using fallback. "
                        "data: {}, fallback: {}",
                        Encodable._ENCODABLE_REG_FIELD,
                        data, fallback)
            return fallback

        # ------------------------------
        # Better KeyError exceptions.
        # ------------------------------
        if not dotted:
            try:
                dotted = data[Encodable._ENCODABLE_REG_FIELD]
            except KeyError:

                # Now we error on the missing decoding hint.
                pretty_data = pretty.indented(data)
                msg = ("decode_with_registry: data has no "
                       f"'{Encodable._ENCODABLE_REG_FIELD}' key.")
                raise log.exception(KeyError(Encodable._ENCODABLE_REG_FIELD,
                                             msg,
                                             data),
                                    msg + " Cannot decode: {}",
                                    pretty_data)

        try:
            encoded_data = data[Encodable._ENCODABLE_PAYLOAD_FIELD]
        except KeyError:
            pretty_data = pretty.indented(data)
            msg = ("decode_with_registry: data has no "
                   f"'{Encodable._ENCODABLE_PAYLOAD_FIELD}' key. "
                   f"Cannot decode: {pretty_data}")
            raise log.exception(KeyError(Encodable._ENCODABLE_REG_FIELD,
                                         msg,
                                         data),
                                msg)

        # ------------------------------
        # Now decode it.
        # ------------------------------

        decoded = EncodableRegistry.get(encoded_data,
                                        dotted=dotted,
                                        data_type=data_types,
                                        error_squelch=error_squelch,
                                        fallback=fallback)
        return decoded

    def decode_map(self,
                   target: Encodable,
                   mapping: Mapping,
                   expected_keys: Iterable[Type['Encodable']] = None
                   ) -> Mapping[str, Any]:
        '''
        Decode a mapping.
        '''
        # log.debug(f"\n\nlogging._decode_map {type(mapping)}: {mapping}\n\n")

        # ---
        # Can we decode the whole dict as something?
        # ---
        if target._was_encoded_with_registry(mapping):
            return self.decode(target, mapping)

        # ---
        # Decode the Base Level
        # ---
        decoded = {}
        for key, value in mapping.items():
            field = self.decode_key(key, expected_keys)
            node = self.decode_value(value, expected_keys)
            decoded[field] = node

        # ---
        # Is It Anything Special?
        # ---
        # Sub-classes could check in about this spot in their override...
        # claiming, claim, reason = AnythingSpecial.claim(decoded)
        # if claiming:
        #     decoded = AnythingSpecial.decode(claim)

        # log.debug(f"\n\n   done._decode_map: {decoded}\n\n")
        return decoded

    def decode_key(self,
                   key: Any,
                   expected_keys: Iterable[Type['Encodable']] = None) -> str:
        '''
        Decode a mapping's key.

        Encodable is pretty stupid. string is only supported type. Override or
        smart-ify if you need support for more key types.
        '''
        # log.debug(f"\n\nlogging._decode_key {type(key)}: {key}\n\n")
        field = None

        # Can we decode to a specified Encodable?
        if expected_keys:
            for encodable in expected_keys:
                # Does this encodable want the key?
                claiming, claim, _ = encodable.claim(key)
                if not claiming:
                    continue
                # Yeah - get it to decode it then.
                field = encodable.decode(claim)
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
                                     'expected_keys': expected_keys,
                                 })

        # log.debug(f"\n\n   done._decode_key: {field}\n\n")
        return field

    def decode_value(self,
                     target: Encodable,
                     value: Any,
                     expected_keys: Iterable[Type['Encodable']] = None
                     ) -> str:
        '''
        Decode a mapping's value.

        Passes `expected_keys` along to _decode_map() if value is a dict.

        Encodable is pretty stupid. dict and Encodable are further decoded -
        everything else is just assumed to be decoded alreday. Override or
        smart-ify if you need support for more/better assumptions.
        '''

        # log.debug(f"\n\nlogging._decode_value {type(value)}: {value}\n\n")
        node = None
        if isinstance(value, dict):
            node = self.decode_map(target, value, expected_keys)

        # You... this... How can I be this stupid sometimes, really...
        # *facepalm* We're decoding something. It /really/ shouldn't be an
        # Encodable right now...
        # elif isinstance(value, Encodable):
        #     # Decode via its function.
        #     node = value.decode_with_registry()

        else:
            # Simple value like int, str? Hopefully?
            node = value

        # log.debug(f"\n\n   done._decode_value: {node}\n\n")
        return node
