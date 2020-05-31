# coding: utf-8

'''
Helper class for managing context dicts for e.g. error messages.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Dict, Optional, Any, List, Type
import enum
import uuid
import copy

from veredi.logger import log

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Actual Contexts
# -----------------------------------------------------------------------------

class VerediContext:

    _KEY_NAME = 'name'

    def __init__(self,
                 name: str,
                 key: str,
                 starting_context: Optional[Dict[str, Any]] = None) -> None:
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
        context = self.get()
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
    # Sub-Context Square Brackets!
    # --------------------------------------------------------------------------

    @property
    def sub(self) -> Dict[str, Any]:
        '''
        My specific subcontext. Creates if it doesn't exist yet.
        '''
        return self._ensure()

    # --------------------------------------------------------------------------
    # Getters / Mergers
    # --------------------------------------------------------------------------

    def subcontext(self, key=None) -> Optional[Dict[str, Any]]:
        '''
        Returns context[key], or if key is None, returns our subcontext.
        '''
        if key is None:
            key = self.key

        context = self.get()
        return context.get(key, None)

    def get(self) -> Dict[str, str]:
        '''
        Returns our context dictionary. If it doesn't exist, creates it with
        our bare sub-entry.
        '''
        sub_context = self._ensure()
        return self.data

    def merge(self,
              other: Optional['VerediContext']) -> 'VerediContext':
        '''
        Merge our context into other's context, then set our's to their's
        (not a deep copy, currently).
        '''
        if other is None:
            merge_with = {}
        elif isinstance(other, dict):
            raise TypeError('Context needs to merge with Context, not dict. '
                            f'{str(self)} merge with: {str(other)}')
        else:
            merge_with = other.get()

        context = self.get()
        # Turn view of keys into list so we can change dictionary as we go.
        for key in list(context.keys()):
            merge_key = key
            if key in merge_with:
                log.error(
                    "Merging dictionaries with key conflict: mine: {context}, "
                    "merge_with: {merge_with}. My keys will get random values "
                    "appended to de-conflict, but this could cause issues "
                    "further along.",
                    context=context,
                    merge_with=merge_with)
                merge_key += '-' + uuid.uuid4().hex[:6]
            merge_with[merge_key] = context[key]

        self.data = merge_with
        return self

    # --------------------------------------------------------------------------
    # To String
    # --------------------------------------------------------------------------

    def __str__(self):
        return f"{self.__class__.__name__}: {str(self.get())}"

    def __repr_name__(self):
        return self.__class__.__name__[:1] + 'Ctx'

    def __repr__(self):
        return f"<{self.__repr_name__()}: {str(self.get())}>"


# ------------------------------------------------------------------------------
# Data Context
# ------------------------------------------------------------------------------

class BaseDataContext(VerediContext):
    def __repr_name__(self):
        return 'DataCtx'


class DataBareContext(BaseDataContext):
    def __init__(self,
                 name: str,
                 key:  str,
                 load: Optional[List[Any]] = None,
                 starting_context: Optional[Dict[str, Any]] = None) -> None:
        '''
        Initialize DataBareContext with name, key, and some list called 'load'.
        '''
        super().__init__(name, key, starting_context)
        self._load = load
        self.sub['load'] = load

    @property
    def load(self):
        return self._load

    def __repr_name__(self):
        return 'DBareCtx'


# §-TODO-§ [2020-05-30]: Move these to game folder?
class DataGameContext(BaseDataContext):

    @enum.unique
    class Type(enum.Enum):
        PLAYER  = 'player'
        MONSTER = 'monster'
        NPC     = 'npc'
        ITEM    = 'item'
        # etc...

        def __str__(self):
            return str(self.value).lower()

    REQUEST_LOAD = 'load-request'
    REQUEST_SAVE = 'save-request'

    REQUEST_TYPE = 'type'
    REQUEST_CAMPAIGN = 'campaign'
    REQUEST_KEYS = {
        Type.PLAYER:  [ 'user',     'player'  ],
        Type.MONSTER: [ 'family',   'monster' ],
        Type.NPC:     [ 'family',   'npc'     ],
        Type.ITEM:    [ 'category', 'item'    ],
    }

    def __init__(self,
                 name:     str,
                 key:      str,
                 type:     'DataGameContext.Type',
                 campaign: str,
                 starting_context: Optional[Dict[str, Any]] = None) -> None:
        '''
        Initialize DataGameContext with name, key, and type.
        '''
        super().__init__(name, key, starting_context)
        self._type = type

        # Save our request type, request keys into our context.
        ctx = self.subcontext()
        for key in self.data_keys:
            ctx[key] = None

        ctx[self.REQUEST_TYPE] = str(type)
        ctx[self.REQUEST_CAMPAIGN] = campaign

    @property
    def type(self) -> 'DataGameContext.Type':
        return self._type

    @property
    def campaign(self) -> str:
        return self.sub[self.REQUEST_CAMPAIGN]

    @property
    def data_keys(self) -> List[str]:
        return self.REQUEST_KEYS[self.type]

    @property
    def data_values(self) -> List[str]:
        return [self.sub.get(key, None) for key in self.data_keys]


class DataLoadContext(DataGameContext):
    def __init__(self,
                 name:     str,
                 type:     'DataGameContext.Type',
                 campaign: str,
                 starting_context: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name, self.REQUEST_LOAD,
                         type, campaign, starting_context)

    def __repr_name__(self):
        return 'DLCtx'



class DataSaveContext(DataGameContext):
    def __init__(self,
                 name:     str,
                 type:     'DataGameContext.Type',
                 campaign: str,
                 starting_context: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name, self.REQUEST_SAVE,
                         type, campaign, starting_context)

    def __repr_name__(self):
        return 'DSCtx'


# ------------------------------------------------------------------------------
# Unit-Testing Context
# ------------------------------------------------------------------------------

class UnitTestContext(VerediContext):
    def __init__(self, test_class, test_name,
                 data, starting_context = None) -> None:
        '''
        Initialize Context with test name.
        '''
        super().__init__((test_class
                          if not test_name else
                          test_name + '.' + test_name),
                         'unit-testing',
                         starting_context)
        ctx_data = self.get()
        ctx_data[self.key] = data

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

    This class should always let the other context 'win' the merge. So e.g. a
    DataLoadContext merged with this should be a DataLoadContext. And this
    merged with a DataLoadContext should also be a DataLoadContext.

    Also, this should not take on its merged cousin's context. It is not really
    a merge but a put.
    '''

    def merge(self,
              other: Optional['VerediContext']) -> 'VerediContext':
        '''
        Not really a merge for PersistentContext!!!

        Put our context into other's context.
        '''
        if other is None:
            copy_to = {}
        elif isinstance(other, dict):
            raise TypeError('Context needs to copy-to with Context, not dict. '
                            f'{str(self)} copy-to: {str(other)}')
        else:
            copy_to = other.get()

        context = self.get()
        for key in context:
            copy_key = key
            if key in copy_to:
                log.error(
                    "Merging dictionaries with key conflict: mine: {context}, "
                    "copy_to: {copy_to}. My keys will get random values "
                    "appended to de-conflict, but this could cause issues "
                    "further along.",
                    context=context,
                    copy_to=copy_to)
                copy_key += '-' + uuid.uuid4().hex[:6]
            copy_to[copy_key] = context[key]

        # Do not set ours to theirs. Leave us as-is for the next
        # ephemeral context.
        # self.data = copy_to

        # Also do not return ourself. Return the other one as it may have
        # sub-class specific stuff it still needs to do.
        return other

    def import_to_sub(self,
                      other: Optional['VerediContext']) -> None:
        '''
        Pulls another context into our /sub/-context.
        '''
        import_from = None
        if other is None:
            return
        elif isinstance(other, dict):
            raise TypeError('Context needs to import from another '
                            'Context, not dict. '
                            f'{str(self)} other: {str(other)}')
        else:
            import_from = other.get()

        context = self.get()
        for key in import_from:
            copy_key = key
            if key in context:
                log.error(
                    "Merging dictionaries with key conflict: mine: {context}, "
                    "import_from: {import_from}. Import key will get random "
                    "values appended to de-conflict, but this could cause "
                    "issues further along.",
                    context=context,
                    import_from=import_from)
                copy_key += '-' + uuid.uuid4().hex[:6]
            context[copy_key] = copy.deepcopy(import_from[key])

    def spawn(self,
              other_class: Optional[Type['VerediContext']],
              *args: Any,
              **kwargs: Any) -> None:
        '''
        Makes a new instance of the passed in type w/ our context overwriting
        its own.
        '''
        other = other_class(self.name, self.key,
                            *args,
                            starting_context=copy.deepcopy(self.get()),
                            **kwargs)

        return other

    # --------------------------------------------------------------------------
    # To String
    # --------------------------------------------------------------------------

    def __str__(self):
        return f"{self.__class__.__name__}: {str(self.get())}"

    def __repr_name__(self):
        return self.__class__.__name__[:3] + 'Ctx'

    def __repr__(self):
        return f"<{self.__repr_name__()}: {str(self.get())}>"
