# coding: utf-8

'''
Helper classes for managing contexts for events, error messages, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type,
                    MutableMapping, Dict, Tuple, Literal)
if TYPE_CHECKING:
    from unittest import TestCase

from veredi.base.null import Null, Nullable, NullNoneOr
import enum
import uuid


from veredi.logs         import log
from veredi.base.strings import label
from .exceptions         import ContextError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


@enum.unique
class Conflict(enum.Flag):
    '''
    Indicates which way a conflict should be resolved.
    '''

    SENDER_WINS = enum.auto()
    '''Sender's key/value overwrites receiver's.'''

    RECEIVER_WINS = enum.auto()
    '''Sender's key/value gets dropped.'''

    SENDER_MUNGED = enum.auto()
    '''Sender's key gets munged by random postfix, then munged-key/value are
    added to receiver.'''

    RECEIVER_MUNGED = enum.auto()
    '''Receiver's key gets munged by random postfix, then sender's key/value
    are added to receiver.'''

    QUIET = enum.auto()
    '''Do not log conflicts.'''


# -----------------------------------------------------------------------------
# Dotted Descriptor for Contexts
# -----------------------------------------------------------------------------

class ContextDottedDescriptor:
    '''
    Veredi label.DotStr provided via descriptor for contexts. Does not hold on
    to the dotted string itself - references the context's data instead.
    '''

    _KEY = 'dotted'

    def __init__(self,
                 name_descriptor: str = None) -> None:
        self.name: str = name_descriptor
        '''
        Optional name of this descriptor.
        '''

    def _get_from_ctx(self,
                      instance: Optional['VerediContext']
                      ) -> Tuple[Dict[Any, Any], Tuple]:
        '''
        Returns a tuple of: (<context data>, <dotted keys>)
        '''
        if not instance:
            return None, None

        data = instance.data
        keys = instance.dotted_keys()
        return data, keys

    def __get__(self,
                instance: Optional[Any],
                owner:    Type[Any]) -> Optional[label.DotStr]:
        '''
        Returns the dotted label value if present in context's data.
        '''
        if not instance:
            return None

        data, keys = self._get_from_ctx(instance)
        # Walk into dict using keys to find dotted.
        for key in keys:
            data = data.get(key, None)
            # Give up early?
            if not data:
                return data

        # Where we ended up is dotted, hopefully.
        return data

    def __set__(self,
                instance: Optional[Any],
                dotted:   Optional[label.LabelInput]) -> None:
        '''
        Setter for context's dotted label.
        '''
        if not instance:
            return

        # Walk into context dict using keys to find dotted.
        # Don't go to final key. We'll use that to set it.
        data, keys = self._get_from_ctx(instance)
        for key in keys[:-1]:
            # What to do with an empty key in data?.. Not exactly expected but
            # I guess set to an empty dict.
            data = data.setdefault(key, {})
            if not data:
                return

        # Found the dict sub-entry that will hold our dotted label.
        if not dotted:
            # It might have a dotted already. Try to clear it out.
            data.pop(keys[-1], None)
        else:
            # Normalize and set the dotted string now.
            data[keys[-1]] = label.normalize(dotted)

    def __set_name__(self, owner: Type[Any], name: str) -> None:
        '''
        Save our descriptor variable's name in its owner's class.
        '''
        self.name = name


# -----------------------------------------------------------------------------
# Base Context
# -----------------------------------------------------------------------------

class VerediContext:
    '''
    Base Context. You do not want this one. You want either want:
      - The background (veredi.data.background).
      - A PersistentContext or an EphemerealContext
        - Or a subclass of one of these.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    _KEY_DOTTED = 'dotted'
    _KEYS_DOTTED_DEFAULT = (_KEY_DOTTED, )

    # -------------------------------------------------------------------------
    # Descriptors
    # -------------------------------------------------------------------------

    dotted: ContextDottedDescriptor = ContextDottedDescriptor()

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        self.data: Dict[Any, Any] = {}
        '''
        The data that makes up this context. Since it means so much but in a
        context-sensitive way (it /is/ the context, essentially), we'll leave
        it 'public' (sans underscore(s)).
        '''

        self._dotted_keys: Optional[Tuple[Any]] = None
        '''
        The keys requried to find the Veredi Dotted Label in the context data.
        Will use self._KEYS_DOTTED_DEFAULT if this is None.
        '''

        self._key: str = None
        '''
        The context's main sub-context's name string.

        E.g. a ConfigContext uses 'configuration' as its key and
        `self._data['configuration']` holds its config-specific context data.
        '''

    def __init__(self,
                 dotted: str,
                 key: str) -> None:
        self._define_vars()

        self._dotted = dotted
        self._key  = key

    def dotted_keys(self) -> Tuple[Any]:
        '''
        Return the keys needed to get our dotted label from our context data.
        '''
        if self._dotted_keys:
            return self._dotted_keys
        return self._KEYS_DOTTED_DEFAULT

    @property
    def key(self) -> str:
        '''
        Returns our context's key (aka the context dict key for our subcontext
        data dict).
        '''
        return self._key

    @key.setter
    def key(self, value: str) -> None:
        '''
        Sets our context's key (aka the context dict key for our subcontext
        data dict).
        '''
        context = self._get()
        sub_context = context.pop(self._key, None)
        self._key = value
        context[self._key] = sub_context
        self.data = context

    # -------------------------------------------------------------------------
    # Square Brackets! (context['key'] accessors)
    # -------------------------------------------------------------------------

    def __contains__(self, key: str) -> bool:
        return key in self.data

    def __getitem__(self, key):
        '''
        General, top level `context[key]`. Not the specific sub-context!
        '''
        return self.data[key]

    def __setitem__(self,
                    key: str,
                    value: str):
        '''
        General, top level `context[key] = value`.
        Not the specific sub-context!
        '''
        self.data[key] = value

    # -------------------------------------------------------------------------
    # Sub-Context Square Brackets! (context.sub['hi'])
    # -------------------------------------------------------------------------
    # Also just for, like, getting at the sub-context data.

    @property
    def sub(self) -> Dict[str, Any]:
        '''
        Returns my specific subcontext. Creates if it doesn't exist yet.
        '''
        return self._ensure()

    # -------------------------------------------------------------------------
    # Stuff / Things
    # -------------------------------------------------------------------------

    def add(self,
            key: Any,
            value: Any) -> bool:
        '''
        Adds to /our/ sub-context.

        That is, this is a shortcut for:
          self.sub[key] = value
        with added checks.

        Returns success/failure bool.
        '''
        sub = self.sub
        if key in sub:
            log.error("Skipping add key '{}' to our sub-context - the key "
                      "already exists. desired value: {}, current value: {}, "
                      "subcontext: {}",
                      key, value, sub[key],
                      sub)
            return False
        sub[key] = value
        return True

    # TODO: sub_add() and add() are the same thing? Pick one. Or make add() be
    # (optionally) top-level?
    # def sub_add(self,
    #             sub_key: Any,
    #             value: Any) -> bool:
    #     '''
    #     Adds to /our/ `ctx_key` sub-context, creating it if it doesn't exist.

    #     That is, this is a shortcut for:
    #       context[ctx_key][sub_key] = value
    #     or:
    #       context.sub[sub_key] = value
    #     with added checks.

    #     Returns success/failure bool.
    #     '''
    #     sub = self.sub
    #     if sub_key in sub:
    #         log.error("Skipping add key '{}' to the '{}' sub-context - "
    #                   "the key already exists. desired value: {}, "
    #                   "current value: {}, subcontext: {}",
    #                   sub_key, self._key, value, sub[sub_key], sub)
    #         return False

    #     sub[sub_key] = value
    #     return True

    def sub_get(self,
                field:   Union[str, enum.Enum],
                default: NullNoneOr[Any] = Null()) -> Nullable[Any]:
        '''
        Gets this context's sub-context, then gets and returns value
        of `field`.

        Returns Null if sub-context or field does not exist in this
        context, unless a `default` is provided.
        '''
        return self._sub_get(self._key, field, default)

    def sub_set(self,
                field: Union[str, enum.Enum],
                value: NullNoneOr[Any]) -> None:
        '''
        Gets this context's sub-context, then sets `field` to `value`. Pops
        `field` out of sub-context if `value` is None.

        Pops `ctx_key` out of context if it is empty after set/pop of field is
        done.
        '''
        return self._sub_set(self._key, field, value)

    def _sub_get(self,
                 ctx_key: str,
                 field: Union[str, enum.Enum],
                 default: NullNoneOr[Any] = Null()) -> Nullable[Any]:
        '''
        Gets `ctx_key` sub-context, then gets and returns value of `field`.

        Returns Null if ctx_key or field does not exist in this context, unless
        a `default` is provided.
        '''
        default = default or Null()
        full_ctx = self._get(False)
        sub_ctx = full_ctx.get(ctx_key, Null())
        return sub_ctx.get(field, Null()) or default

    def _sub_set(self,
                 ctx_key: str,
                 field: Union[str, enum.Enum],
                 value: Any) -> None:
        '''
        Gets `ctx_key` sub-context, then sets `field` to `value`. Pops `field`
        out of sub-context if `value` is None.

        Pops `ctx_key` (sub-context) out of context if it is empty after
        set/pop of field is done.
        '''
        # Get sub-context.
        sub_ctx = self._get_sub(ctx_key, False)
        if not sub_ctx:
            # No current sub-context. Check for early exits or make one.

            # Early exits: no value to set and no sub-context. Ok; done.
            if not value:
                return

            # Otherwise, ensure sub-context exists.
            else:
                sub_ctx = self._get_sub(ctx_key, True)

        # Set/pop field.
        if value is None:
            sub_ctx.pop(field, None)

        else:
            # Re-get to ensure the subcontext exists.
            sub_ctx = self._get_sub(ctx_key, True)
            sub_ctx[field] = value

        # And make sure the context is up to date.
        if not sub_ctx:
            # Remove it if it's empty now.
            self.data.pop(ctx_key, None)
        else:
            # Make sure it's updated if some action replaced the sub_ctx
            # dictionary here but not in the context.
            self.data[ctx_key] = sub_ctx

    # -------------------------------------------------------------------------
    # Getters / Mergers
    # -------------------------------------------------------------------------

    def _ensure(self, top_key: Any = None) -> Dict[str, Any]:
        '''
        Make sure our subcontext exists (and by extension, our context).
        Returns our subcontext entry of the context dict.

        if top_key is None, ensures our subcontext (self._key) exists.
        '''
        if not top_key:
            top_key = self._key

        self.data = self.data or {}
        sub_context = self.data.setdefault(top_key, {})
        # TODO: a way to ensure a dotted name is present in the subcontext?
        # if not self.dotted:
        #     self.dotted_keys = ???
        #     self.dotted = ???
        return sub_context

    # TODO: rename to _get_full?
    def _get(self, ensure_sub_existance: bool = True) -> Dict[Any, Any]:
        '''
        Returns our /entire/ context dictionary. If it doesn't exist, creates
        it with our bare sub-entry.
        '''
        if ensure_sub_existance:
            self._ensure()
        return self.data

    def _set_sub(self,
                 key:       str,
                 sub_ctx:   NullNoneOr[Dict[Any, Any]] = None,
                 overwrite: bool                       = False) -> None:
        '''
        Sets the /specified/ sub-context dictionary.

        If `sub_ctx` is Null, None, or otherwise Falsy: pop the sub out of
        existance.

        If `overwrite` is False and `key` already exists, raises a KeyError.
        '''
        full_ctx = self._get(False)

        # Remove sub-context?
        if not sub_ctx:
            full_ctx.pop(key, None)
            # Done
            return

        # Overwrite check.
        if not overwrite and key in full_ctx:
            msg = (f"Cannot set sub-context. Key '{key}' already exists "
                   "in context and `overwrite` is not set.")
            error = KeyError(key, msg, full_ctx, sub_ctx)
            raise log.exception(error, msg)

        # Set the sub-context.
        full_ctx[key] = sub_ctx

    def _get_sub(self,
                 key: str,
                 ensure_sub_existance: bool = True) -> Nullable[Dict[Any, Any]]:
        '''
        Gets the /specified/ sub-context dictionary.

        If `ensure_sub_existance`, make sure it exists before returning it
        (create it with our bare entry if needed).

        Can return Null.
        '''
        full_ctx = None
        sub_ctx = None
        if ensure_sub_existance:
            sub_ctx = self._ensure(key)
            full_ctx = self._get(False)
        else:
            full_ctx = self._get(False)
            if not full_ctx:
                return Null()

        key = key or self._key
        sub_ctx = self.data.get(key, Null())
        return sub_ctx

    def push(self,
             other: Optional['VerediContext'],
             resolution: Conflict = Conflict.SENDER_MUNGED) -> 'VerediContext':
        '''
        Push our context into 'other'. Merges all our top-level keys, not just
        our subcontext.

        Assignment/shallow copy.

        Returns `other`.
        '''
        if not isinstance(resolution, Conflict):
            raise TypeError(resolution, "Unknown conflict resolution type.")
        self._merge(self, other, resolution, 'push', 'to')
        return other

    def pull(self,
             other: Optional['VerediContext'],
             resolution: Conflict = Conflict.SENDER_MUNGED) -> 'VerediContext':
        '''
        Pulls the other's context into our's. Merges all of other's top-level
        keys, not just their subcontext.

        Assignment/shallow copy.

        Returns `self`.
        '''
        self._merge(other, self, resolution, 'pull', 'from')

    def pull_to_sub(self,
                    other: Union['VerediContext', Dict[str, Any], None],
                    resolution: Conflict = Conflict.SENDER_MUNGED) -> None:
        '''
        Pulls another context into our /sub/-context.

        Not a deep copy, currently. Could be - used to be.

        Returns self.
        '''
        d_from = None
        if other is None:
            return
        elif isinstance(other, dict):
            d_from = other
        else:
            d_from = other._get()

        self._merge_dicts(d_from,
                          self.sub,
                          resolution,
                          'sub-pull',
                          'from')

        return other

    def _merge(self,
               m_from:      Optional['VerediContext'],
               m_to:        Optional['VerediContext'],
               resolution:    Conflict,
               verb:        str,
               preposition: str) -> None:
        '''
        Merge 'from' context into 'to' context.

        Assignment/shallow copy (not deep copy, currently).
        '''
        if m_from is None or m_to is None:
            msg = f"Cannot {verb} a 'None' context. from: {m_from}, to: {m_to}"
            error = ContextError(msg,
                                 context=self,
                                 data={
                                     'm_from': m_from,
                                     'm_to': m_to,
                                     'resolution': resolution,
                                 })
            raise log.exception(error, msg, context=self)

        elif m_to is m_from:
            msg = (f"Cannot {verb} something with itself. "
                   f"from: {m_from}, to: {m_to}")
            error = ContextError(msg,
                                 context=self,
                                 data={
                                     'm_from': m_from,
                                     'm_to': m_to,
                                     'resolution': resolution,
                                 })
            raise log.exception(error, msg, context=self)

        elif isinstance(m_to, PersistentContext):
            msg = (f"Cannot {verb} {preposition} a PersistentContext. "
                   f"from: {m_from}, to: {m_to}")
            error = ContextError(msg,
                                 context=self,
                                 data={
                                     'm_from': m_from,
                                     'm_to': m_to,
                                     'resolution': resolution,
                                 })
            raise log.exception(error, msg, context=self)

        elif isinstance(m_from, dict) or isinstance(m_to, dict):
            # This was for catching any "a context is a dict" places that still
            # existed back when VerediContext was created. It can probably be
            # deleted someday.
            raise TypeError('Context needs to merge with Context, not dict. ',
                            m_from, m_to)

        d_from = m_from._get()
        d_to   = m_to._get()
        self._merge_dicts(d_from, d_to, resolution, verb, preposition)

    def _merge_dicts(self,
                     d_from:      Dict[str, Any],
                     d_to:        Dict[str, Any],
                     resolution:  Conflict,
                     verb:        str,
                     preposition: str) -> None:

        # Turn view of keys into list so we can change dictionary as we go.
        for key in d_from:
            if key in d_to:
                self._deflict(resolution, d_to, key, d_from[key],
                              verb, preposition)
            else:
                d_to[key] = d_from[key]

    def _deflict(self,
                 resolution:   Conflict,
                 d_to:         Dict[str, Any],
                 key_sender:   str,
                 value_sender: Any,
                 verb:         str,
                 preposition:  str) -> None:

        quiet = (resolution & Conflict.QUIET) == Conflict.QUIET
        resolution = resolution & ~Conflict.QUIET

        # Overwrite options are easy enough.
        if resolution == Conflict.SENDER_WINS:
            if not quiet:
                log.warning(
                    "{}({}): Sender and Receiver have same key: {}. "
                    "De-conflicting keys by overwriting receiver's value. "
                    "Values before overwrite: currently: {}, overwrite-to: {}",
                    verb, resolution, key_sender,
                    d_to[key_sender], value_sender,
                    context=self)
            d_to[key_sender] = value_sender
            return

        elif resolution == Conflict.RECEIVER_WINS:
            if not quiet:
                log.warning(
                    "{}({}): Sender and Receiver have same key: {}. "
                    "De-conflicting keys by ignoring sender's value. "
                    "Values: currently: {}, ignoring: {}",
                    verb, resolution, key_sender,
                    d_to[key_sender], value_sender,
                    context=self)
            return

        # Munging options still to do - can only do those to strings.
        if not isinstance(key_sender, str):
            msg = "Cannot munge-to-deconflict keys that are not strings."
            error = ContextError(
                msg,
                context=self,
                data={
                    'd_to': d_to,
                    'resolution': resolution,
                    'key_sender': key_sender,
                    'value_sender': value_sender,
                    'd_to[key_sender]': d_to[key_sender],
                })
            raise log.exception(error,
                                msg,
                                context=self)

        if resolution == Conflict.SENDER_MUNGED:
            if not quiet:
                log.warning(
                    "{}({}): Sender and Receiver have same key: {}. "
                    "Sender's key will get random string appended to "
                    "de-conflict, but this could cause issues further along. "
                    "sender[{}] = {}, vs receiver[{}] = {}",
                    verb, resolution, key_sender,
                    key_sender, value_sender, key_sender, d_to[key_sender],
                    context=self)

            key_munged = key_sender + '-' + uuid.uuid4().hex[:6]
            # Add sender's value to munged key.
            d_to[key_munged] = value_sender

        elif resolution == Conflict.SENDER_MUNGED:
            if not quiet:
                log.warning(
                    "{}({}): Sender and Receiver have same key: {}. "
                    "Receiver's key will get random string appended to "
                    "de-conflict, but this could cause issues further along. "
                    "sender[{}] = {}, vs receiver[{}] = {}",
                    verb, resolution, key_sender,
                    key_sender, value_sender, key_sender, d_to[key_sender],
                    context=self)

            key_munged = key_sender + '-' + uuid.uuid4().hex[:6]
            # Move receiver's value to munged key.
            old_value = d_to.pop(key_sender)
            d_to[key_munged] = old_value
            # Add sender to original key.
            d_to[key_sender] = value_sender

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def _pretty(self):
        from veredi.base.strings import pretty
        from pprint import pformat
        return pretty.indented(f"{self.__class__.__name__}:\n"
                               + pformat(self._get()))

    def __str__(self):
        return f"{self.__class__.__name__}: {str(self._get())}"

    def __repr_name__(self):
        return self.__class__.__name__[:1] + 'Ctx'

    def __repr__(self):
        return f"<{self.__repr_name__()}: {str(self._get())}>"


# -----------------------------------------------------------------------------
# Short-Term Context
# -----------------------------------------------------------------------------
class EphemerealContext(VerediContext):
    ...


# -----------------------------------------------------------------------------
# Unit-Testing Context
# -----------------------------------------------------------------------------

class UnitTestContext(EphemerealContext):
    def __init__(self,
                 test_case:        'TestCase',
                 test_name:        Optional[str]            = None,
                 data:             MutableMapping[str, Any] = {},
                 starting_context: MutableMapping[str, Any] = None) -> None:
        '''
        Initialize Context with test class/name. e.g.:

        context = UnitTestContext(self,
                                  'test_something',
                                  data={...})
        '''
        dotted = (test_case.dotted
                  if not test_name else
                  label.normalize(test_case.dotted, test_name)
        super().__init__(test_case.dotted,
                         'unit-testing')

        # Set starting context.
        if starting_context:
            self.data = starting_context
        else:
            self.data = {}

        self.dotted = test_case.dotted

        # Ensure our sub-context and ingest the provided data.
        sub = self._ensure()
        # Munge any starting_context/defaults with what was specifically
        # supplied as the subcontext data.
        self._merge_dicts(data,
                          sub,
                          Conflict.RECEIVER_MUNGED,
                          'UnitTestContext.init.pull',
                          'from')

    def __repr_name__(self):
        return 'UTCtx'


# -----------------------------------------------------------------------------
# Long-Term Context
# -----------------------------------------------------------------------------

class PersistentContext(VerediContext):
    '''
    This is for e.g. systems and other things that are persistent/long lived
    but have context and want to send it to errors or merge it with events or
    what have you.

    PersistentContexts cannot pull() from other contexts - pull() only raises
    an exception.
    '''

    def pull(self,
             other: Optional['VerediContext']) -> 'VerediContext':
        '''
        Not allowed for PersistentContexts!
        '''
        raise TypeError("PersistentContexts do not support 'pull()'. "
                        "Try pull_to_sub() instead?",
                        self, other)

    def spawn(self,
              other_class:  Optional[Type['VerediContext']],
              spawned_name: str,
              spawned_key:  Optional[str],
              *args:        Any,
              **kwargs:     Any) -> None:
        '''
        Makes a new instance of the passed in type w/ our context pushed to its
        own.

        Not a deep copy, currently. Could be - used to be.

        Returns spawned context.
        '''
        log.debug("Spawning: {} with name: {}, key: {}, args: {}, kwargs: {}",
                  other_class, spawned_name, spawned_key, args, kwargs,
                  context=self)
        other = other_class(spawned_name, spawned_key,
                            *args,
                            **kwargs)

        if other.key == self._key:
            other.pull_to_sub(self.sub, Conflict.RECEIVER_MUNGED)
            other.pull(self, Conflict.RECEIVER_MUNGED | Conflict.QUIET)
        else:
            other.pull(self, Conflict.RECEIVER_MUNGED)

        return other

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __str__(self):
        return f"{self.__class__.__name__}: {str(self._get())}"

    def __repr_name__(self):
        return self.__class__.__name__[:3] + 'Ctx'

    def __repr__(self):
        return f"<{self.__repr_name__()}: {str(self._get())}>"
