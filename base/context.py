# coding: utf-8

'''
Helper classes for managing contexts for events, error messages, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, Type, MutableMapping, Dict, List
import enum
import uuid
import copy

from veredi.logger import log
from .exceptions import ContextError

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


@enum.unique
class CodeKey(enum.Enum):
    '''
    Code systems that want to tuck things into contexts can use these as their
    top-level key.
    '''

    REPO = enum.auto()
    '''RepoSystem or Repo itself can store things here. e.g. data stream from
    deserializing data.'''

    CODEC = enum.auto()
    '''CodecSystem or Codec itself can store things here. e.g. data
    object(s) from decoding.'''


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
    '''Receiver's key gets munged by random postfix, then sender's key/value are
    added to receiver.'''

    QUIET = enum.auto()
    '''Do not log conflicts.'''


# -----------------------------------------------------------------------------
# Base Context
# -----------------------------------------------------------------------------

class VerediContext:
    '''
    Base Context. You do not want this one. You want a PersistentContext or an
    EphemerealContext, which are the two main subclasses.
    '''

    _KEY_NAME = 'name'

    def __init__(self,
                 name: str,
                 key: str) -> None:
        self.data  = {}
        self._name = name
        self._key  = key

    def _ensure(self, top_key: Any = None) -> Dict[str, Any]:
        '''
        Make sure our subcontext exists (and by extension, our context).
        Returns our subcontext entry of the context dict.

        if top_key is None, ensures our subcontext (self.key) exists.
        '''
        if not top_key:
            top_key = self.key

        self.data = self.data or {}
        sub_context = self.data.setdefault(top_key, {})
        # Ensure our name if we're ensuring our subcontext.
        if (top_key is self.key
                and self._KEY_NAME not in sub_context):
            sub_context[self._KEY_NAME] = self.name
        return sub_context

    @property
    def name(self) -> str:
        '''
        Returns our context's name (e.g. "YamlCodec" context name is "yaml").
        '''
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        '''
        Sets our context's name (e.g. "YamlCodec" context name is "yaml").
        '''
        if self.data:
            self.data.setdefault(self.key, {})[self._KEY_NAME] = value
        self._name = value

    @property
    def key(self) -> str:
        '''
        Returns our context's key (aka the context dict key for our subcontext
        data dict) (e.g. "YamlCodec" context key is "codec").
        '''
        return self._key

    @key.setter
    def key(self, value: str) -> None:
        '''
        Sets our context's key (aka the context dict key for our subcontext
        data dict) (e.g. "YamlCodec" context key is "codec").
        '''
        context = self._get()
        sub_context = context.pop(self._key, None)
        self._key = value
        context[self._key] = sub_context
        self.data = context

    # --------------------------------------------------------------------------
    # Square Brackets! (context['key'] accessors)
    # --------------------------------------------------------------------------

    def __getitem__(self, key):
        '''
        General, top level `context[key]`. Not the specific sub-context!
        '''
        return self.data[key]

    def __setitem__(self,
                    key: str,
                    value: str):
        '''
        General, top level `context[key] = value`. Not the specific sub-context!
        '''
        self.data[key] = value

    # --------------------------------------------------------------------------
    # Sub-Context Square Brackets! (context.sub['hi'])
    # --------------------------------------------------------------------------
    # Also just for, like, getting at the sub-context data.

    @property
    def sub(self) -> Dict[str, Any]:
        '''
        Returns my specific subcontext. Creates if it doesn't exist yet.
        '''
        return self._ensure()

    def code(self, key: CodeKey):
        '''
        Returns a specific CodeKey subcontext. Creates if it doesn't exist yet.
        '''
        return self._ensure(key)

    # --------------------------------------------------------------------------
    # Stuff / Things
    # --------------------------------------------------------------------------

    def add(self,
            key: Any,
            value: Any) -> None:
        '''
        Adds to our sub-context.

        That is, this is a shortcut for:
          self.sub[key] = value
        with added checks.
        '''
        sub = self.sub
        if key in sub:
            log.error("Skipping add key '{}' to our sub-context - the key "
                      "already exists. desired value: {}, current value: {}, "
                      "subcontext: {}",
                      key, value, sub[key],
                      sub)
            return
        sub[key] = value

    def sub_add(self,
                ctx_key: Any,
                sub_key: Any,
                value: Any) -> None:
        '''
        Adds to a sub-context.

        That is, this is a shortcut for:
          context[ctx_key][sub_key] = value
        with added checks.
        '''
        ctx = self._get()
        if ctx_key not in ctx:
            log.error("Skipping sub_add for keys '{}', '{}' to context - "
                      "the key '{}' does not exists in the context. desired value: {}."
                      "context: {}",
                      ctx_key, sub_key, ctx_key, value, ctx)
            return

        sub = ctx[ctx_key]
        if sub_key in sub:
            log.error("Skipping add key '{}' to the '{}' sub-context - the key "
                      "already exists. desired value: {}, current value: {}, "
                      "subcontext: {}",
                      sub_key, ctx_key, value, sub[sub_key], sub)
            return
        sub[key] = value

    # --------------------------------------------------------------------------
    # Getters / Mergers
    # --------------------------------------------------------------------------

    def _get(self) -> Dict[str, str]:
        '''
        Returns our context dictionary. If it doesn't exist, creates it with
        our bare sub-entry.
        '''
        sub_context = self._ensure()
        return self.data

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
            raise TypeError("nope.")
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
            raise log.exception(
                None,
                ContextError,
                "Cannot {} a 'None' context. from: {}, to: {}",
                verb, m_from, m_to,
                context=self)
        elif m_to is m_from:
            raise log.exception(
                None,
                ContextError,
                "Cannot {} something with itself. from: {}, to: {}",
                verb, m_from, m_to,
                context=self)
        elif isinstance(m_to, PersistentContext):
            raise log.exception(
                None,
                ContextError,
                "Cannot {} {} a PersistentContext. from: {}, to: {}",
                verb, preposition, m_from, m_to,
                context=self)
        elif isinstance(m_from, dict) or isinstance(m_to, dict):
            # This was for catching any "a context is a dict" places that still
            # existed back when VerediContext was created. It can probably be
            # deleted someday.
            raise TypeError('Context needs to merge with Context, not dict. ',
                            m_from, m_other)

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
                self._deflict(resolution, d_to, key, d_from[key], verb, preposition)
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
            log.warning(
                "{}({}): Sender and Receiver have same key: {}. "
                "De-conflicting keys by ignoring sender's value. "
                "Values: currently: {}, ignoring: {}",
                verb, resolution, key_sender, d_to[key_sender], value_sender,
                context=self)
            return

        # Munging options still to do - can only do those to strings.
        if not isinstance(key_sender, str):
            raise log.exception(
                TypeError(
                    "Cannot munge-to-deconflict keys that are not strings.",
                    key_sender),
                ContextError,
                "{}({}): Cannot munge-to-deconflict keys that are not strings. "
                "sender[{}] = {}, vs receiver[{}] = {}",
                verb, resolution, key_sender, value_sender, key_sender,
                d_to[key_sender], context=self)

        if resolution == Conflict.SENDER_MUNGED:
            log.warning(
                "{}({}): Sender and Receiver have same key: {}. "
                "Sender's key will get random string appended to de-conflict, "
                "but this could cause issues further along. "
                "sender[{}] = {}, vs receiver[{}] = {}",
                verb, resolution, key_sender,
                key_sender, value_sender, key_sender, d_to[key_sender],
                context=self)

            key_munged = key_sender + '-' + uuid.uuid4().hex[:6]
            # Add sender's value to munged key.
            d_to[key_munged] = value_sender

        elif resolution == Conflict.SENDER_MUNGED:
            log.warning(
                "{}({}): Sender and Receiver have same key: {}. "
                "Receiver's key will get random string appended to de-conflict,"
                "but this could cause issues further along. "
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

    # --------------------------------------------------------------------------
    # To String
    # --------------------------------------------------------------------------

    def _pretty(self):
        from veredi.logger import pretty
        return pretty.indented(f"{self.__class__.__name__}:\n"
                               + pprint.pformat(self._get()))

    def __str__(self):
        return f"{self.__class__.__name__}: {str(self._get())}"

    def __repr_name__(self):
        return self.__class__.__name__[:1] + 'Ctx'

    def __repr__(self):
        return f"<{self.__repr_name__()}: {str(self._get())}>"


# ------------------------------------------------------------------------------
# Short-Term Context
# ------------------------------------------------------------------------------
class EphemerealContext(VerediContext):
    pass


# ------------------------------------------------------------------------------
# Unit-Testing Context
# ------------------------------------------------------------------------------

class UnitTestContext(EphemerealContext):
    def __init__(self,
                 test_class:       str,
                 test_name:        str,
                 data:             MutableMapping[str, Any],
                 starting_context: MutableMapping[str, Any] = None) -> None:
        '''
        Initialize Context with test class/name.
        '''
        super().__init__(test_class + '.' + test_name,
                         'unit-testing')

        # Set starting context.
        if starting_context:
            self.data = starting_context
        else:
            self.data = {}

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
    This is for e.g. systems and other things that are persistent/long lived but
    have context and want to send it to errors or merge it with events or what
    have you.

    PersistentContexts cannot pull() from other contexts - pull() only raises an
    exception.
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

        if other.key == self.key:
            other.pull_to_sub(self.sub, Conflict.RECEIVER_MUNGED)
            other.pull(self, Conflict.RECEIVER_MUNGED | Conflict.QUIET)
        else:
            other.pull(self, Conflict.RECEIVER_MUNGED)

        return other

    # --------------------------------------------------------------------------
    # To String
    # --------------------------------------------------------------------------

    def __str__(self):
        return f"{self.__class__.__name__}: {str(self._get())}"

    def __repr_name__(self):
        return self.__class__.__name__[:3] + 'Ctx'

    def __repr__(self):
        return f"<{self.__repr_name__()}: {str(self._get())}>"
