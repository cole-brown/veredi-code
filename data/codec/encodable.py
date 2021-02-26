# coding: utf-8

'''
Encodable mixin class for customizing how a class is encoded/decoded to
basic Python values/structures (int, dict, etc).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (Optional, Union, Any, Type, NewType,
                    Iterable, Mapping, Dict, Tuple)
from veredi.base.null import Null, null_to_none, null_or_none

from abc import abstractmethod
import enum
import re


from veredi                import log
from veredi.base.strings   import pretty
from veredi.base.registrar import CallRegistrar, RegisterType
from veredi.base.strings   import label
from veredi.base           import numbers

from ..exceptions          import EncodableError
from .const                import EncodedComplex, EncodedSimple, EncodedEither

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
    'EncodableRegistry',
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
    to/from EncodedSimple:
      - _encode_simple
      - _get_decode_rx, _get_decode_str_rx
        - Must return non-None.

    Classes must implement:
      - _type_field
      - _encode_simple, _encode_complex
      - _decode_simple, _decode_complex
      - _get_decode_rx, _get_decode_str_rx
        - Can return None if no desire for EncodedSimple.

    Classes can/should use "error_for*" methods for validation.
    '''

    _DO_NOT_REGISTER = 'n/a'
    '''
    Use this as your 'dotted' param if you have a base class that should not be
    directly encoded/decoded (only children should be encoded/decoded).
    '''

    _TYPE_FIELD_NAME = 'encoded.type'
    '''
    Encodable's _type_field() value must exist as either top-level key or as
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
    `Encodable.encode_with_registry()`. Munged down from:
    'veredi.data.codec.encodable'
    '''

    _ENCODABLE_PAYLOAD_FIELD: str = 'v.payload'
    '''
    Key for help claiming things encoded with
    `Encodable.encode_with_registry()`.
    '''

    # -------------------------------------------------------------------------
    # Dotted Name
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
    def __call__(klass, *args, **kwargs):
        if getattr(klass, "__abstractmethods__", None):
            msg = ("Can't instantiate abstract class "
                   f"{klass.__name__} with frozen methods "
                   f"{set(klass.__abstractmethods__)}")
            error = TypeError(msg, klass, args, kwargs)
            raise log.exception(error, msg)

        return super().__call__(*args, **kwargs)

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def __init_subclass__(klass:    'Encodable',
                          dotted:   Optional[str] = None,
                          **kwargs: Any) -> None:
        '''
        Auto-register our subclasses.

        NOTE: If you're an enum. Shit's fucked up, yo. See
        veredi.enum.FlagEncodeNameMixin and veredi.math.parser.NodeType
        for assistance.
        '''
        log.debug(f"\nEncodable.__init_subclass__: {dotted}, "
                  f"other kwargs: {kwargs}\n")

        # ---
        # Parents
        # ---
        # We've pulled dotted off of keyword args by naming it, so pass the
        # rest to our parents.
        super().__init_subclass__(**kwargs)

        # ---
        # Special Case
        # ---
        if issubclass(klass, enum.Enum):
            log.debug(f"Ignoring enum '{klass}'. I can't figure out how to "
                      "propogate 'dotted' properly to not cause a bunch of "
                      "errors... Use <EncodableSubclass>.register_manually() "
                      "instead.")
            return

        # ---
        # Sanity
        # ---
        if not dotted:
            # No dotted string is an error.
            msg = (f"This ({klass}) Encodable sub-class must be "
                   "created with a `dotted` parameter (or registered "
                   "manually). e.g.: Jeffory(Encodable, dotted="
                   f"'veredi.jeff.jeffory'). Got: {klass.__name__}(..., "
                   f"dotted='{dotted}', kwargs={{}})")
            error = ValueError(msg, klass, dotted, kwargs)
            raise log.exception(error, msg, kwargs)

        elif dotted == klass._DO_NOT_REGISTER:
            # A 'do not register' dotted string probably means a base class is
            # encodable but shouldn't exist on its own; subclasses should
            # register themselves.
            log.debug(f"{klass.__name__}.__init_subclass__: "
                      f"Ignoring sub-class {klass}. "
                      "Marked as 'do not register'.")
            return

        # ---
        # Register
        # ---
        # We've pulled off the `dotted` keyword arg by naming it as our
        # expected arg...

        # So we can set their _ENCODABLE_DOTTED attribute.
        klass._ENCODABLE_DOTTED = dotted

        # And also use it to register the sub-class (or error).
        klass._register(dotted)
        log.debug(f"{klass.__name__}.__init_subclass__: "
                  f"Registered sub-class {klass} as: {dotted}, "
                  f"{klass._ENCODABLE_DOTTED}, ",
                  f"{klass.dotted()}")

    @classmethod
    def _register(klass:  'Encodable',
                  dotted: Optional[label.LabelInput] = None) -> None:
        '''
        Register the `klass` with the `dotted` string to our registry.
        '''
        # ---
        # Sanity
        # ---
        if not dotted:
            # No dotted string is an error.
            msg = ("Encodable sub-classes must be registered with a `dotted` "
                   f"parameter. Got: '{dotted}'")
            error = ValueError(msg, klass, dotted)
            raise log.exception(error, msg)

        elif dotted == klass._DO_NOT_REGISTER:
            # A 'do not register' dotted string probably means a base class is
            # encodable but shouldn't exist on its own; subclasses should
            # register themselves.
            log.debug(f"Ignoring sub-class {klass}. "
                      "Marked as 'do not register'.")
            return

        # ---
        # Register
        # ---
        dotted_args = label.regularize(dotted)
        EncodableRegistry.register(klass, *dotted_args)

    @classmethod
    def register_manually(klass: 'Encodable',
                          dotted: Optional[str] = None
                          ) -> None:
        '''
        Some classes fuck up everything. Looking at you, 'enum' module.
        For them, we have this manual registration function.
        '''
        # ---
        # Sanity
        # ---
        if not dotted:
            try:
                dotted = klass.dotted()
            except AttributeError as error:
                msg = (f"{klass.__name__}.register_manually(): Encodable "
                       "tried to register manually, but did not provide a "
                       "dotted string and also did not have a 'dotted()' "
                       "class function.")
                log.exception(error, msg)
                raise

            if not dotted:
                msg = (f"{klass.__name__}.register_manually(): Encodable "
                       "tried to register manually, but did not provide a "
                       "dotted string and also did not return a string from "
                       f"its 'dotted()' class function. Got: '{dotted}'")
                error = ValueError(msg, dotted, klass)
                raise log.exception(error, msg)

        log.debug(f"{klass.__name__}.register_manually: {dotted}")
        # ---
        # Register
        # ---
        # Got past checks, register it.
        klass._register(dotted)

    # -------------------------------------------------------------------------
    # Encoding Method
    # -------------------------------------------------------------------------

    @classmethod
    def _encode_simple_only(klass: 'Encodable') -> bool:
        '''
        Returns True if this class only encodes/decodes to EncodedSimple.

        Default implementation:
          return False
        '''
        return False

    @classmethod
    def _encoded_simply(klass: 'Encodable', data: EncodedEither) -> bool:
        '''
        Returns true if data satisfies EncodedSimple type hinting requirements.
        '''
        # Currently just string, so this is easy:
        return isinstance(data, str)

    # -------------------------------------------------------------------------
    # Identity / Ownership
    # -------------------------------------------------------------------------

    @classmethod
    @abstractmethod
    def _type_field(klass: 'Encodable') -> str:
        '''
        A short, unique name for encoding an instance into the field of a dict.

        E.g.: If an instance of whatever has a "Jeff" class instance with
        _type_field() returning 'jeff' and instance vars of x=1, y=2 is encoded
        to json:
          {
            ...
            'jeff': { 'x': 1, 'y': 2 },
            ...
          }
        '''
        raise NotImplementedError(f"{klass.__name__} needs to implement "
                                  "_type_field()")

    @classmethod
    def _get_type_field(klass: 'Encodable',
                        data: Optional[EncodedEither]) -> Optional[str]:
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
                       data: Optional[EncodedEither]) -> bool:
        '''
        Returns False if `klass._get_type_field()` or `klass._type_field()`
        return None.

        Returns True if `data` has type field (via `klass._get_type_field()`)
        and it matches the expected type field (via `klass._type_field()`).

        Returns False otherwise.
        '''
        data_type_field = klass._get_type_field(data)
        if data_type_field is None:
            # This may be common for simply encoded stuff. Not sure. If so
            # change to debug level.
            log.warning("No type field in data. {}", data)
            return False

        class_type_field = klass._type_field()
        if class_type_field is None:
            msg = (f"Class {klass} returned 'None' from _type_field(). "
                   "_type_field() is a required function. Cannot determine "
                   f"type of data: {data}")
            error = EncodableError(msg, None, None, data)
            log.error(error, None, msg)
            return False

        return class_type_field == data_type_field

    @classmethod
    def _was_encoded_with_registry(klass: 'Encodable',
                                   data:  EncodedEither) -> bool:
        '''
        Returns True if `data` is not `klass._encoded_simply()` type and has
        klass._ENCODABLE_REG_FIELD key.
        '''
        if klass._encoded_simply(data):
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

        For complex encodings, looks for `klass._type_field()` in data. It
        should be one of these:
          - a top level key, with our encodable data as the key's value.
            - Returns `data[klass._type_field()]` as our claim.
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
        if klass._encoded_simply(data):
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
        if klass._encode_simple_only():
            return (False,
                    None,
                    "Class only encodes simply and didn't match data.")

        # ---
        # Complex?
        # ---
        # Else it's EncodedComplex.

        # Are we a sub-field?
        if klass._type_field() in data:
            # Our type is a top level key, so our claim is the key's value.
            return True, data[klass._type_field()], None

        # Are we this whole thing?
        if klass._is_type_field(data):
            # Our type is in the 'type' field, so our claim is this whole
            # data thing.
            return True, data, None

        # ---
        # No Claim on Data.
        # ---
        # Doesn't have our _type_field() value, so no.
        reason = (f"{klass.__name__} is (probably) encoded but doesn't have "
                  f"our type-field ('{klass._type_field()}') at top level or "
                  "as 'type' value.")

        # Debug output full data structure, but don't build the pretty string
        # unless we're actually logging it.
        if log.will_output(log.Level.DEBUG):
            log.debug(reason + " data:\n{}", pretty.indented(data))

        return False, None, reason

    # -------------------------------------------------------------------------
    # API for encoding/decoding.
    # -------------------------------------------------------------------------

    def encode(self,
               encode_in_progress: Optional[EncodedComplex]) -> EncodedEither:
        '''
        Encode self as a simple or complex encoding, depending on
        self._encode_simple_only().

        If self._encode_simple_only(), encodes to a string..

        If not self._encode_simple_only():
          - If `encode_in_progress` is provided, encodes this to a sub-field
            under self._type_field().
          - Else encodes this to a dict and provides self._type_field() as the
            value of self._TYPE_FIELD_NAME.
        '''
        # TODO: if encode_in_progress is not None:
        # and if encode simple, instead encode as:
        #   encode_in_progress[type_field] = simple_value

        # Should we encode simply by default?
        if self._encode_simple_only():
            # Yes. Do that thing.
            simple = self._encode_simple()

            # If there's an encode_in_progress that's been pass in, and we just
            # encoded ourself to a string... That's a bit awkward. But I guess
            # do this. Will make weird-ish looking stuff like:
            # 'v.mid': 'v.mid:1'
            if encode_in_progress is not None:
                encode_in_progress[self._type_field()] = simple
                return encode_in_progress

            return simple

        # No. Encode everything we know...
        # ...which as the base class isn't much.
        encoded = self._encode_complex()

        # Put the type somewhere and return encoded data.
        if encode_in_progress is not None:
            # Encode as a sub-field in the provided data.
            encode_in_progress[self._type_field()] = encoded
            return encode_in_progress

        # Encode as a base-level dict.
        encoded[self._TYPE_FIELD_NAME] = self._type_field()
        return encoded

    # TODO [2020-11-06]: Change encode() to a classmethod so we can combine
    # the "or none" into it?
    @classmethod
    def encode_or_none(klass: 'Encodable',
                       encodable: Optional['Encodable'],
                       encode_in_progress: Optional[EncodedComplex] = None
                       ) -> EncodedEither:
        '''
        If `encodable` is None or Null, returns None.
        Otherwise, returns `encodable.encode(encode_in_progress)`.

        The equivalent function for decoding is just `decode()`.
        '''
        encoded = None
        if not null_or_none(encodable):
            encoded = encodable.encode(encode_in_progress)
        return encoded

    def encode_with_registry(self) -> EncodedComplex:
        '''
        Creates an output dict with keys: _ENCODABLE_REG_FIELD
        and _ENCODABLE_PAYLOAD_FIELD.

        Returns the output dict:
          output[_ENCODABLE_REG_FIELD]: result of `self.dotted()`
          output[_ENCODABLE_PAYLOAD_FIELD]: result of `self.encode()`
        '''
        return {
            Encodable._ENCODABLE_REG_FIELD: self.dotted(),
            Encodable._ENCODABLE_PAYLOAD_FIELD: self.encode(None),
        }

    @classmethod
    def decode(klass: 'Encodable',
               data: EncodedEither) -> Optional['Encodable']:
        '''
        Decode simple or complex `data` input, using it to build an
        instance of this class.

        Return a new `klass` instance.
        '''
        # ---
        # Decode at all?
        # ---
        if data is None:
            # Can't decode nothing; return nothing.
            return None

        # ---
        # Decode Simply?
        # ---
        if klass._encoded_simply(data):
            # Yes. Do that thing.
            return klass._decode_simple(data)

        # Does this class only do simple encode/decode?
        if klass._encode_simple_only():
            msg = (f"Cannot decode data to '{klass.__name__}'. "
                   "Class only encodes simply and didn't match data")
            error = TypeError(data, msg)
            raise log.exception(error,
                                msg + ' data: {}',
                                data)

        # ---
        # Decode Complexly?
        # ---
        # Maybe; try claiming it to see if it has our type field in the right
        # place?
        klass.error_for_claim(data)

        # Ok; yes. Get our field out of data and pass on to
        # self._decode_complex().
        _, claim, _ = klass.claim(data)
        return klass._decode_complex(claim)

    @classmethod
    def decode_with_registry(klass:    'Encodable',
                             data:     EncodedComplex,
                             **kwargs: Any) -> Optional['Encodable']:
        '''
        Input `data` must have keys:
          - Encodable._ENCODABLE_REG_FIELD
          - Encodable._ENCODABLE_PAYLOAD_FIELD
        Raises KeyError if not present.

        Takes EncodedComplex `data` input, and uses
        `Encodable._ENCODABLE_REG_FIELD` key to find registered Encodable to
        decode `data[Encodable._ENCODABLE_PAYLOAD_FIELD]`.

        Any kwargs supplied (except 'dotted' - will be ignored) are forwarded
        to EncodableRegistry.decode() (e.g. 'fallback').

        Return a new `klass` instance.
        '''
        # ------------------------------
        # Fallback early.
        # ------------------------------
        if data is None:
            # No data at all. Use either fallback or None.
            if 'fallback' in kwargs:
                log.debug("decode_with_registry: data is None; using "
                          "fallback. data: {}, fallback: {}",
                          data, kwargs['fallback'])
                return kwargs['fallback']
            # `None` is an acceptable enough value for us... Lots of things are
            # optional. Errors for unexpectedly None things should happen in
            # the caller.
            return None

        # When no _ENCODABLE_REG_FIELD, we can't do anything since we don't
        # know how to decode. But only deal with fallback case here. If they
        # don't have a fallback, let it error soon (but not here).
        if ('fallback' in kwargs
                and Encodable._ENCODABLE_REG_FIELD not in data):
            # No hint as to what data is - use fallback.
            log.warning("decode_with_registry: No {} in data; using fallback. "
                        "data: {}, fallback: {}",
                        Encodable._ENCODABLE_REG_FIELD,
                        data, kwargs['fallback'])
            return kwargs['fallback']

        # ------------------------------
        # Better KeyError exceptions.
        # ------------------------------
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

        # Don't let 'dotted' be passed in... We already have a 'dotted' kwarg
        # to send to EncodableRegistry.decode().
        kwargs.pop('dotted', None)

        decoded = EncodableRegistry.decode(encoded_data,
                                           dotted=dotted,
                                           **kwargs)
        return decoded

    # -------------------------------------------------------------------------
    # Encoding: Entry Functions
    # -------------------------------------------------------------------------

    @abstractmethod
    def _encode_simple(self) -> EncodedSimple:
        '''
        Encode ourself as an EncodedSimple, return that value.
        '''
        ...

    @abstractmethod
    def _encode_complex(self) -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        ...

    # -------------------------------------------------------------------------
    # Decoding: Entry Functions
    # -------------------------------------------------------------------------

    @classmethod
    @abstractmethod
    def _decode_simple(klass: 'Encodable',
                       data: EncodedSimple) -> 'Encodable':
        '''
        Decode ourself as an EncodedSimple, return a new instance of `klass` as
        the result of the decoding.
        '''
        ...

    @classmethod
    @abstractmethod
    def _decode_complex(klass: 'Encodable',
                        data: EncodedComplex) -> 'Encodable':
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
                      key: str,
                      data: EncodedComplex) -> None:
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
    def error_for_value(klass:   'Encodable',
                        key:     str,
                        value:   Any,
                        data: EncodedComplex) -> None:
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
    def error_for(klass:   'Encodable',
                  data:    EncodedComplex,
                  keys:    Iterable[str]     = [],
                  values:  Mapping[str, Any] = {}) -> None:
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

    # -------------------------------------------------------------------------
    # Helpers: Encoding
    # -------------------------------------------------------------------------

    def encode_any(klass: 'Encodable',
                   data:  Any) -> EncodedEither:
        '''
        Tries to encode `data`.

        If `data` is:
          - dict or encodable: Step in to them for encoding.
          - enum: Use the enum's value.

        Else assume it is already encoded and return as-is.
        '''
        # log.debug(f"{klass.__name__}.encode_any: {data}")

        encoded = None
        if isinstance(data, Encodable):
            # Encode via its function.
            encoded = data.encode(None)

        elif isinstance(data, dict):
            # Encode via our map helper.
            encoded = klass._encode_map(data)

        elif isinstance(data, enum.Enum):
            # Assume if it's an enum.Enum (which isn't Encodable) that just
            # value is fine. If that isn't fine, the enum can make itself an
            # Encodable.
            encoded = data.value

        else:
            # Assume that whatever it is, it is decoded.
            if not isinstance(data, (str, int, float)):
                log.warning(f"{klass.__name__}.encode_any: unknown "
                            f"type of data {type(data)}. Assuming it's "
                            "decoded already or doesn't need to be. {}",
                            data)
            encoded = data

        # log.debug(f"{klass.__name__}.encode_any: Done. {encoded}")
        return encoded

    def _encode_map(self,
                    encode_from: Mapping,
                    encode_to:   Optional[Mapping] = None,
                    ) -> Mapping[str, Union[str, int, float, None]]:
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
            field = self._encode_key(key)
            node = self._encode_value(value)
            encode_to[field] = node

        # log.debug(f"\n\n   done._encode_map: {encode_to}\n\n")
        return encode_to

    def _encode_key(self, key: Any) -> str:
        '''
        Encode a dict key.
        '''
        # log.debug(f"\n\nlogging._encode_key: {key}\n\n")
        field = None

        # If key is an encodable, can it encode into a key?
        if isinstance(key, Encodable):
            if key._encode_simple():
                field = key.encode(None)
            else:
                msg = (f"{self.__class__.__name__}._encode_key: Encodable "
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
            node = self._encode_map(value)

        elif isinstance(value, Encodable):
            # Encode via its function. Use `encode_with_registry` so we can
            # know what it was encoded as during _decode_map().
            node = value.encode_with_registry()

        elif isinstance(value, (enum.Enum, enum.IntEnum)):
            node = value.value

        else:
            node = value

        # log.debug(f"\n\n   done._encode_value: {node}\n\n")
        return node

    # -------------------------------------------------------------------------
    # Helpers: Decoding
    # -------------------------------------------------------------------------

    @classmethod
    def decode_any(klass: 'Encodable',
                   data:  EncodedComplex,
                   expected_keys: Iterable[Type['Encodable']] = None) -> Any:
        '''
        Tries to decode `data`.

        If `data` is:
          - encodable: Must be registered to EncodableRegistry in order to
            decode properly.
          - dict: Decode with _decode_map() using `expected_keys`. Returns
            another dict!

        Else assume it is already decoded or is basic data and returns it
        as-is.
        '''
        # log.debug(f"{klass.__name__}.decode_any: {data}")

        # First... is it a registered Encodable?
        decoded = None
        try:
            # Don't want this to log the exception if it happens. We're ok with
            # it happening.
            decoded = EncodableRegistry.decode(data,
                                               squelch_error=True)
            return decoded

        except ValueError:
            # Nope. But that's fine. Try other things.
            pass

        # Next... dict?
        if isinstance(data, dict):
            # Decode via our map helper.
            decoded = klass._decode_map(data, expected_keys)

        # Finally... I dunno. Leave as-is?
        else:
            # Warn if not a type we've thought about.
            if (not isinstance(data, numbers.NumberTypesTuple)
                    and not isinstance(data, str)):
                log.warning(f"{klass.__name__}.decode_any: unknown "
                            f"type of data {type(data)}. Assuming it's "
                            "decoded already or doesn't need to be. {}",
                            data)
            # Assume that whatever it is, it is decoded.
            decoded = data

        # log.debug(f"{klass.__name__}.decode_any: Done. {decoded}")
        return decoded

    @classmethod
    def _decode_map(klass: 'Encodable',
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
        if klass._was_encoded_with_registry(mapping):
            return klass.decode_with_registry(mapping)

        # ---
        # Decode the Base Level
        # ---
        decoded = {}
        for key, value in mapping.items():
            field = klass._decode_key(key, expected_keys)
            node = klass._decode_value(value, expected_keys)
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

    @classmethod
    def _decode_key(klass: 'Encodable',
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
            for klass in expected_keys:
                # Does this klass want the key?
                claiming, claim, _ = klass.claim(key)
                if not claiming:
                    continue
                # Yeah - get it to decode it then.
                field = klass.decode(claim)
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

    @classmethod
    def _decode_value(klass: 'Encodable',
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
            node = klass._decode_map(value, expected_keys)

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


# -----------------------------------------------------------------------------
# Encodables Registry
# -----------------------------------------------------------------------------

class EncodableRegistry(CallRegistrar):
    '''
    Registry for all the encodable types.
    '''

    @classmethod
    def dotted(klass: 'EncodableRegistry') -> str:
        '''
        Returns this registrar's dotted name.
        '''
        return 'veredi.data.codec.encodable.registry'

    @classmethod
    def _init_register(klass:     'EncodableRegistry',
                       encodable: Type['Encodable'],
                       reg_args:  Iterable[str]) -> bool:
        '''
        This is called before anything happens in `register()`.

        Raise an error if a non-Encodable class tries to register.
        '''
        if not issubclass(encodable, Encodable):
            msg = ("EncodableRegistry only accepts Encodable subclasses for "
                   "registration. Got: {encodable}")
            error = ValueError(msg, encodable, reg_args)
            raise log.exception(error, msg)

        return True

    @classmethod
    def _register(klass:      'EncodableRegistry',
                  encodable:  Type['Encodable'],
                  # *args passed into register()
                  reg_args:   Iterable[str],
                  # final key in `reg_args`
                  leaf_key:   str,
                  # A sub-tree of our registration dict, at the correct node
                  # for registering this encodable.
                  reg_ours:   Dict,
                  # A sub-tree of the background registration dict, at the
                  # correct node for registering this encodable.
                  reg_bg:     Dict) -> None:
        '''
        We want to register to the background with:
          { leaf_key: Encodable._type_field() }

        `reg_args` is the Iterable of args passed into `register()`.
        `reg_ours` is the place in klass._REGISTRY we placed this registration.
        `reg_bg` is the place in the background we placed this registration.
        '''
        # Get it's type field name.
        try:
            name = encodable._type_field()
        except NotImplementedError as error:
            msg = (f"{klass.__name__}._register: '{type(encodable)}' "
                   f"(\"{label.regularize(*reg_args)}\") needs to "
                   "implement _type_field() function.")
            log.exception(error, msg)
            # Let error through. Just want more info.
            raise

        # Set as registered cls/func.
        reg_ours[leaf_key] = encodable

        # Save to the background as a thing that has been registered at this
        # level.
        bg_list = reg_bg.setdefault('.', [])
        bg_list.append({leaf_key: name})

    @classmethod
    def decode(klass:         'EncodableRegistry',
               data:          Optional[EncodedEither],
               dotted:        Optional[str]         = None,
               data_type:     Optional['Encodable'] = None,
               squelch_error: bool                  = False,
               **kwargs:      Any) -> 'Encodable':
        '''
        Decode `data` into an Encodable subclass, if any of our registered
        classes match 'dotted' field in data, or claim() the `data`.

        If `data` is None, returns None.

        Return "registered_class.decode(data)" from the class chosen to decode
        the data.

        If `dotted` is supplied, try to get that Encodable from our registry.
        Use it or raise RegistryError if not found.

        If `data_type` is supplied, will restrict search for registered
        Encodable to just that class or its subclasses.

        `squelch_error` will only raise the exception, instead of raising it
        through log.exception().

        If nothing registered can/will decode the data:
          - If the `fallback` keyword arg is supplied, will return that.
          - Else will raise a ValueError.
        '''
        # None decodes to None.
        if data is None:
            return None

        log.debug(f"EncodableRegistry.decode: data: {type(data)}, "
                  f"dotted: {dotted}, data_type: {data_type}")

        registree = None

        # ---
        # Too simple?
        # ---
        if isinstance(data, numbers.NumberTypesTuple):
            # A number just decodes to itself.
            return data

        # ---
        # Use dotted name?
        # ---
        if dotted:
            registree = klass.get_dotted(dotted, None)

        # ---
        # Search for registered Encodable.
        # ---
        else:
            registry = klass._get()
            data_dotted = label.from_map(data, squelch_error=True)
            registree = klass._search(registry,
                                      data_dotted,
                                      data,
                                      data_type=data_type)

        # ---
        # Decode if found.
        # ---
        if registree:
            # Find by claim?
            claiming, claim, _ = registree.claim(data)
            if claiming:
                return registree.decode(claim)

        # ---
        # Not Found: Fallback if provided?
        # ---
        if 'fallback' in kwargs:
            return kwargs['fallback']

        # ---
        # No Fallback: Error out.
        # ---
        msg = (f"{klass.__name__}: No registered Encodable found for "
               f"data. data_dotted: {data_dotted}")
        extra = (", \n"
                 "registry:\n"
                 "{}\n\n"
                 "data:\n"
                 "{}\n\n")
        error = ValueError(msg, data, registree)
        if squelch_error:
            raise error
        else:
            raise log.exception(error, msg + extra,
                                pretty.indented(registry),
                                pretty.indented(data))

    @classmethod
    def _search(klass:     'EncodableRegistry',
                place:     Dict[str, Any],
                dotted:    label.DotStr,
                data:      EncodedEither,
                data_type: Type['Encodable']) -> Optional['Encodable']:
        '''
        Provide `self._get()` as starting point of search.

        Searches the registry.

        If 'data_type' is supplied, will restrict search for registered
        Encodable to use to just that or subclasses.

        If `dotted` is provided, walks that keypath and
        returns whatever is registered to that.

        Otherwise, recursively walk our registry dict to find something that
        will claim() `data`.

        Returns registree or None.
        '''
        # Set data_type to any Encodable if not supplied.
        if data_type is None:
            data_type = Encodable

        # ---
        # Provided with a dotted key. Use that for explicit search.
        # ---
        # More like 'get' than search...
        if label.is_dotstr(dotted):
            keys = label.regularize(dotted)
            # Path shouldn't be long. Just let Null-pattern pretend to be a
            # dict if we hit a 'Does Not Exist'.
            for key in keys:
                place = place.get(key, Null())
            # Done, return either the registree or None.
            place = null_to_none(place)
            # Place must be:
            #   - An Encodable.
            #   - The same class or a subclass of data_type.
            if (not place
                    or (type(place) != data_type
                        and not issubclass(place, data_type))):
                # Don't return some random halfway point in the registry tree.
                place = None
            return place

        # ---
        # Search for a claimer...
        # ---
        for key in place:
            node = place[key]
            # If we got a sub-tree/branch, recurse into it.
            if isinstance(node, dict):
                result = klass._search(node, dotted, data, data_type)
                # Did that find it?
                if result:
                    # Yes; return decoded result.
                    return result
                else:
                    # No; done with this - go to next node.
                    continue

            # If we got a leaf node, check it.
            if not issubclass(node, Encodable):
                log.warning("Unexpected node in registry... expect either "
                            f"strings or Encodables, got: {node}")
                continue

            # Do they claim this?
            # claiming, _, _ = node.claim(data)
            claiming, claim, reason = node.claim(data)
            if claiming:
                # Yes; return decoded result.
                return node

            # Else, not this; continue looking.

        # ---
        # Nothing found.
        # ---
        return None
