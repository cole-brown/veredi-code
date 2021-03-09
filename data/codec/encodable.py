# coding: utf-8

'''
Encodable mixin class for customizing how a class is encoded/decoded to
basic Python values/structures (int, dict, etc).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING, Optional, Any, Iterable, Mapping, Tuple)
if TYPE_CHECKING:
    from .codec import Codec

from abc import abstractmethod
import re


from veredi.logs           import log
from veredi.base.strings   import pretty
from veredi.base.registrar import RegisterType
from veredi.data           import background

from ..exceptions          import EncodableError
from .const                import (EncodedComplex,
                                   EncodedSimple,
                                   EncodedEither,
                                   Encoding)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # ------------------------------
    # Imported
    # ------------------------------
    # Users of Encodable/EncodableRegistry want to use this a lot.
    # Export so they don't have to import from the base registrar.
    'RegisterType',

    # ------------------------------
    # File-Local
    # ------------------------------

    # ---
    # Types
    # ---
    'EncodedComplex',
    'EncodedSimple',
    'EncodedEither',

    # ---
    # Classes
    # ---
    'Encodable',
]


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Encodable Interface / Mixin
# -----------------------------------------------------------------------------

class Encodable:
    '''
    Mixin for classes that want to support encoding/decoding themselves.

    The class should convert its data to/from a mapping of strings to basic
    value-types (str, int, etc). If anything it (directly) contains also needs
    encoding/decoding, the class should ask it to during the encode/decode.

    Classes must implement if they only want to encode/decode
    to/from Encoding.SIMPLE:
      - encode_simple
      - _get_decode_rx, _get_decode_str_rx
        - Must return non-None.

    Classes must implement:
      - type_field
      - encode_simple, encode_complex
      - decode_simple, decode_complex
      - _get_decode_rx, _get_decode_str_rx
        - Can return None if no desire for Encoding.SIMPLE.

    Classes can/should use "error_for*" methods for validation.
    '''

    _DO_NOT_REGISTER: str = 'n/a'
    '''
    Use this as your 'dotted' param if you have a base class that should not be
    directly encoded/decoded (only children should be encoded/decoded).
    '''

    _TYPE_FIELD_NAME: str = 'encoded.type'
    '''
    Encodable's type_field() value must exist as either top-level key or as
    the value in this field.

    Examples for Jeff(Encodable, dotted='jeff.something') class:
    1) Jeff is a sub-field of the encoded data:
      data = {
        ...
        'jeff.something': {...},
        ...
      }

    2) Jeff is the encoded data:
      data = {
        ...
        'encoded.type': 'jeff.something',
        ...
      }
    '''

    _ENCODABLE_DOTTED: str = None
    '''
    Classes can just let __init_subclass__ fill this in.
    '''

    _ENCODABLE_REG_FIELD: str = 'v.codec'
    '''
    Key for help claiming things encoded with
    `Codec.encode()`. Munged down from:
    'veredi.data.codec.encodable'
    '''

    _ENCODABLE_PAYLOAD_FIELD: str = 'v.payload'
    '''
    Key for help claiming things encoded with
    `Codec.encode()`.
    '''

    # -------------------------------------------------------------------------
    # Class "Properties"
    # -------------------------------------------------------------------------

    @classmethod
    def dotted(klass: 'Encodable') -> str:
        '''
        Returns the dotted name used to register this Encodable.
        '''
        return klass._ENCODABLE_DOTTED

    # -------------------------------------------------------------------------
    # ABC-Lite
    # -------------------------------------------------------------------------

    # So... ABCs keep biting me when they an other classes both want enums and
    # fight and it's stupid annoying and doesn't even work in the case of e.g.
    # NodeType, which is a FlagEncodeNameMixin (which is an Encodable (which
    # was an ABC)), and also an enum.Flag. It wanted enum.EnumMeta and
    # abc.ABCMeta, but even when those classes were combined into a superclass,
    # the 'dotted' attribute I wanted for me went off into enum code and threw
    # an error before it got to me.
    #
    # And I can't make my code go first because enum makes you let it go first.
    # So fuck that. We'll just pretend to be an ABC.
    #
    # TODO: Is this klass or self?
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if getattr(self, "__abstractmethods__", None):
            msg = ("Can't instantiate abstract class "
                   f"{self.__class__.__name__} with abstract methods "
                   f"{set(self.__abstractmethods__)}")
            error = TypeError(msg, self, args, kwargs)
            raise log.exception(error, msg)

        return super().__call__(*args, **kwargs)

    # -------------------------------------------------------------------------
    # Encoding Method
    # -------------------------------------------------------------------------

    @classmethod
    def encoding(klass: 'Encodable') -> 'Encoding':
        '''
        Returns what type of encoding this Encodable supports.

        Default:
          return Encoding.COMPLEX
        '''
        return Encoding.COMPLEX

    @classmethod
    def encoded_as(klass: 'Encodable', data: EncodedEither) -> 'Encoding':
        '''
        Figure out what encoding type was used for the data when encoded
        (simple or complex).

        Returns EncodeType.SIMPLE if data satisfies EncodedSimple type hinting
        requirements.
        '''
        # ---
        # Simple?
        # ---
        # Currently just string, so this is easy:
        if isinstance(data, str):
            return Encoding.SIMPLE

        # ---
        # Not simple, therefor must be complex.
        # ---
        return Encoding.COMPLEX

    # -------------------------------------------------------------------------
    # Identity / Ownership
    # -------------------------------------------------------------------------

    @classmethod
    @abstractmethod
    def type_field(klass: 'Encodable') -> str:
        '''
        A short, unique name for encoding an instance into the field of a dict.

        E.g.: If an instance of whatever has a "Jeff" class instance with
        type_field() returning 'jeff' and instance vars of x=1, y=2 is encoded
        to json:
          {
            ...
            'jeff': { 'x': 1, 'y': 2 },
            ...
          }
        '''
        raise NotImplementedError(f"{klass.__name__} needs to implement "
                                  "type_field()")

    @classmethod
    def _get_type_field(klass: 'Encodable',
                        data:  Optional[EncodedEither]) -> Optional[str]:
        '''
        If data is not a mapping, returns None.

        Looks for _TYPE_FIELD_NAME as key in top level of data dictionary,
        returns it if found, else returns None.
        '''
        try:
            if klass._TYPE_FIELD_NAME in data:
                return data[klass._TYPE_FIELD_NAME]

        # TypeError: "x in data" didn't work.
        # KeyError: "data[x]" didn't work.
        # Don't care - we tried and are returning None.
        except (TypeError, KeyError):
            pass
        return None

    @classmethod
    def _is_type_field(klass: 'Encodable',
                       data:  Optional[EncodedEither]) -> bool:
        '''
        Returns False if `klass._get_type_field()` or `klass.type_field()`
        return None.

        Returns True if `data` has type field (via `klass._get_type_field()`)
        and it matches the expected type field (via `klass.type_field()`).

        Returns False otherwise.
        '''
        data_type_field = klass._get_type_field(data)
        if data_type_field is None:
            # This may be common for simply encoded stuff. Not sure. If so
            # change to debug level.
            log.warning("No type field in data. {}", data)
            return False

        class_type_field = klass.type_field()
        if class_type_field is None:
            msg = (f"Class {klass} returned 'None' from type_field(). "
                   "type_field() is a required function. Cannot determine "
                   f"type of data: {data}")
            error = EncodableError(msg, None, None, data)
            log.error(error, None, msg)
            return False

        return class_type_field == data_type_field

    @classmethod
    def _was_encoded_with_registry(klass: 'Encodable',
                                   data:  EncodedEither) -> bool:
        '''
        Returns True if `data` is not Encoding.SIMPLE and has
        klass._ENCODABLE_REG_FIELD key.
        '''
        if klass.encoded_as(data) == Encoding.SIMPLE:
            return False

        try:
            return Encodable._ENCODABLE_REG_FIELD in data

        # Think "x in data" is TypeError. Also catching KeyError just in case.
        except (TypeError, KeyError):
            return False

        # How are you here, though?
        return False

    @classmethod
    def claim(klass: 'Encodable',
              data:  EncodedEither
              ) -> Tuple[bool, Optional[EncodedEither], Optional[str]]:
        '''
        For simple encodings, looks for a match to the `klass._get_decode_rx()`
        regex.
          - Returns `data` as our claim.

        For complex encodings, looks for `klass.type_field()` in data. It
        should be one of these:
          - a top level key, with our encodable data as the key's value.
            - Returns `data[klass.type_field()]` as our claim.
        or
          - a top level 'claim' key, with our encodable data as all of `data`.
            - Returns `data` as our claim.

        Returns a tuple of:
          - bool: Can claim.
            - True if this Encodable class thinks it can/should decode this.
            - False otherwise.
          - EncodedEither:
            - Our claim of the data.
          - Optional[str]: Reason.
            - If can claim, this is None.
            - If cannot claim, this is a string describing why not.
        '''
        # ---
        # Simple?
        # ---
        # Is it EncodedSimple type and intended for this class?
        if klass.encoded_as(data) == Encoding.SIMPLE:
            # If it's a simple encode and we don't have a decode regex for
            # that, then... No; It can't be ours.
            decode_rx = klass._get_decode_rx()
            if not decode_rx:
                reason = (f"{klass.__name__} is (probably) encoded simply "
                          f"but has no {klass.__name__}._get_decode_rx(): "
                          f"rx: {decode_rx}, data: {data}")
                return False, None, reason

            # Check if decode_rx likes the data.
            claimed = bool(decode_rx.match(data))
            data_claim = data if claimed else None
            reason = (None if claimed else "No regex match.")
            return claimed, data_claim, None

        # Does this class only do simple encode/decode?
        if not klass.encoding().has(Encoding.COMPLEX):
            return (False,
                    None,
                    "Class only encodes simply and didn't match data.")

        # ---
        # Complex?
        # ---
        # Else it's EncodedComplex.

        # Are we a sub-field?
        if klass.type_field() in data:
            # Our type is a top level key, so our claim is the key's value.
            return True, data[klass.type_field()], None

        # Are we this whole thing?
        if klass._is_type_field(data):
            # Our type is in the 'type' field, so our claim is this whole
            # data thing.
            return True, data, None

        # ---
        # No Claim on Data.
        # ---
        # Doesn't have our type_field() value, so no.
        reason = (f"{klass.__name__} is (probably) encoded but doesn't have "
                  f"our type-field ('{klass.type_field()}') at top level or "
                  "as 'type' value.")

        # Debug output full data structure, but don't build the pretty string
        # unless we're actually logging it.
        if log.will_output(log.Level.DEBUG):
            log.debug(reason + " data:\n{}", pretty.indented(data))

        return False, None, reason

    # -------------------------------------------------------------------------
    # Encoding: Entry Functions
    # -------------------------------------------------------------------------

    @abstractmethod
    def encode_simple(self,
                      codec: 'Codec') -> EncodedSimple:
        '''
        Encode ourself as an EncodedSimple, return that value.
        '''
        ...

    @abstractmethod
    def encode_complex(self,
                       codec: 'Codec') -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        ...

    # -------------------------------------------------------------------------
    # Decoding: Entry Functions
    # -------------------------------------------------------------------------

    @classmethod
    @abstractmethod
    def decode_simple(klass: 'Encodable',
                      data:  EncodedSimple,
                      codec: 'Codec') -> 'Encodable':
        '''
        Decode ourself as an EncodedSimple, return a new instance of `klass` as
        the result of the decoding.
        '''
        ...

    @classmethod
    @abstractmethod
    def decode_complex(klass: 'Encodable',
                       data:  EncodedComplex,
                       codec: 'Codec') -> 'Encodable':
        '''
        Decode ourself as an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        ...

    # -------------------------------------------------------------------------
    # Encoding Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def _get_decode_str_rx(klass: 'Encodable') -> Optional[str]:
        '''
        Returns regex /string/ (not compiled regex) of what to look for to
        claim just a string as this class.

        For example, perhaps a UserId for 'jeff' has a normal decode of:
          {
            '_encodable': 'UserId',
            'uid': 'deadbeef-cafe-1337-1234-e1ec771cd00d',
          }
        And perhaps it has str() of 'uid:deadbeef-cafe-1337-1234-e1ec771cd00d'

        This would expect an rx string for the str.

        Default implementation:
          return None

        For classes that don't support simple encoding/decoding, just return
        None.
        '''
        return None

    @classmethod
    def _get_decode_rx(klass: 'Encodable') -> Optional[re.Pattern]:
        '''
        Returns /compiled/ regex (not regex string) of what to look for to
        claim just a string as this class.

        For example, perhaps a UserId for 'jeff' has a normal decode of:
          {
            '_encodable': 'UserId',
            'uid': 'deadbeef-cafe-1337-1234-e1ec771cd00d',
          }
        And perhaps it has str() of 'uid:deadbeef-cafe-1337-1234-e1ec771cd00d'

        This would expect an rx string for the str.

        Default implementation:
          return None

        For classes that don't support simple encoding/decoding, just return
        None.
        '''
        return None

    # -------------------------------------------------------------------------
    # Helpers: Validation / Error
    # -------------------------------------------------------------------------

    @classmethod
    def error_for_claim(klass: 'Encodable',
                        data: EncodedEither) -> None:
        '''
        Raises an EncodableError if claim() returns false.
        '''
        claiming, _, reason = klass.claim(data)
        if not claiming:
            msg = f"Cannot claim for {klass.__name__}: {reason}."
            error = EncodableError(msg, None,
                                   data={
                                       'data': data,
                                   })
            raise log.exception(error, msg + ' data: {}', data)

    @classmethod
    def error_for_key(klass: 'Encodable',
                      key:   str,
                      data:  EncodedComplex) -> None:
        '''
        Raises an EncodableError if supplied `key` is not in `mapping`.
        '''
        if key not in data:
            msg = f"Cannot decode to {klass.__name__}: {data}"
            error = EncodableError(msg, None,
                                   data={
                                       'key': key,
                                       'data': data,
                                   })
            raise log.exception(error, msg)

    @classmethod
    def error_for_value(klass: 'Encodable',
                        key:   str,
                        value: Any,
                        data:  EncodedComplex) -> None:
        '''
        Raises an EncodableError if `key` value in `data` is not equal to
        supplied `value`.

        Assumes `error_for_key()` has been called for the key.
        '''
        if data[key] != value:
            msg = (
                f"Cannot decode to {klass.__name__}. "
                f"Value of '{key}' is incorrect. "
                f"Expected '{value}'; got '{data[key]}"
                f": {data}",
                None
            )
            error = EncodableError(msg, None,
                                   data={
                                       'key': key,
                                       'value': value,
                                       'data': data,
                                   })
            raise log.exception(error, msg)

    @classmethod
    def error_for(klass:  'Encodable',
                  data:   EncodedComplex,
                  keys:   Iterable[str]     = [],
                  values: Mapping[str, Any] = {}) -> None:
        '''
        Runs:
          - error_for_claim()
          - error_for_key() on all `keys`
          - error_for_value() on all key/value pairs in `values`.
        '''
        klass.error_for_claim(data)

        for key in keys:
            klass.error_for_key(key, data)

        for key in values:
            klass.error_for_value(key, values[key], data)

