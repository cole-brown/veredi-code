# coding: utf-8

'''
Helper classes for managing contexts for events, error messages, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, Type, MutableMapping, Dict, List
import enum
import uuid
import copy

from veredi.logger import log
from .exceptions import ContextError

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# §-TODO-§ [2020-05-31]:
# Move more specific contexts (e.g. DataContexts out to a more specific place?)

# §-TODO-§ [2020-05-31]:   - context rework?
# §-TODO-§ [2020-05-31]:   - what do PersistentContexts pull from context that is used to create them?
# §-TODO-§ [2020-05-31]:   - Only pass around context - stuff construction data into it?
#    - Remove *args, **kwargs from my classes entirely?
#    - Leave in things passing along or creating things blindly (e.g. registry.create)


# -----------------------------------------------------------------------------
# Actual Contexts
# -----------------------------------------------------------------------------

class VerediContext:

    _KEY_NAME = 'name'

    def __init__(self,
                 name: str,
                 key: str,
                 starting_context: Optional[MutableMapping[str, Any]] = None) -> None:
        if starting_context:
            self.data = starting_context
        else:
            self.data = {}
        self._name = name
        self._key  = key

    def _ensure(self) -> Dict[str, Any]:
        '''
        Make sure our subcontext exists (and by extension, our context).
        Returns our subcontext entry of the context dict.
        '''
        self.data = self.data or {}
        sub_context = self.data.setdefault(self.key, {})
        if self._KEY_NAME not in sub_context:
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
        My specific subcontext. Creates if it doesn't exist yet.
        '''
        return self._ensure()

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
             other: Optional['VerediContext']) -> 'VerediContext':
        '''
        Push our context into 'other'. Merges all our top-level keys, not just
        our subcontext.

        Assignment/shallow copy.

        Returns `other`.
        '''
        self._merge(self, other, 'push', 'to')
        return other

    def pull(self,
             other: Optional['VerediContext']) -> 'VerediContext':
        '''
        Pulls the other's context into our's. Merges all of other's top-level
        keys, not just their subcontext.

        Assignment/shallow copy.

        Returns `self`.
        '''
        self._merge(other, self, 'pull', 'from')

    def _merge(self,
               m_from:      Optional['VerediContext'],
               m_to:        Optional['VerediContext'],
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
        self._merge_dicts(d_from, d_to, verb, preposition)

    def _merge_dicts(self,
                     d_from:      Dict[str, Any],
                     d_to:        Dict[str, Any],
                     verb:        str,
                     preposition: str) -> None:

        # Turn view of keys into list so we can change dictionary as we go.
        for key in d_from:
            merge_key = key
            if key in d_to:
                log.error(
                    "Key conflict in context '{}' operation. "
                    "Source key will get random string appended to de-conflict,"
                    "but this could cause issues further along."
                    "from: {}, to: {}",
                    verb, d_from, d_to,
                    context=self)
                merge_key += '-' + uuid.uuid4().hex[:6]
            d_to[merge_key] = d_from[key]

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
# Unit-Testing Context
# ------------------------------------------------------------------------------

class UnitTestContext(VerediContext):
    def __init__(self,
                 test_class:       str,
                 test_name:        str,
                 data:             MutableMapping[str, Any],
                 starting_context: MutableMapping[str, Any] = None) -> None:
        '''
        Initialize Context with test class/name.
        '''
        super().__init__(test_class + '.' + test_name,
                         'unit-testing',
                         starting_context)
        # Set our sub-context to the provided data.
        ctx = self._get()
        ctx[self.key] = data

    def __repr_name__(self):
        return 'UTCtx'


# -----------------------------------------------------------------------------
# Context Mimic / Interface
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

    def pull_to_sub(self,
                    other: Optional['VerediContext']) -> None:
        '''
        Pulls another context into our /sub/-context.

        /Is/ a deepcopy.

        Returns self.
        '''
        d_from = None
        if other is None:
            return
        elif isinstance(other, dict):
            # This was for catching any "a context is a dict" places that still
            # existed back when VerediContext was created. It can probably be
            # deleted someday.
            raise TypeError('Context needs to pull from another Context, '
                            'not dict.',
                            m_from, m_other)
        else:
            d_from = other._get()

        self._merge_dicts(copy.deepcopy(d_from),
                          self.sub,
                          'sub-pull',
                          'from')

        return other

    def spawn(self,
              other_class:  Optional[Type['VerediContext']],
              spawned_name: str,
              spawned_key:  str,
              *args:        Any,
              **kwargs:     Any) -> None:
        '''
        Makes a new instance of the passed in type w/ a deep copy of our context
        overwriting its own.

        Returns spawned context.
        '''
        other = other_class(spawned_name, spawned_key,
                            *args,
                            starting_context=copy.deepcopy(self._get()),
                            **kwargs)

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
