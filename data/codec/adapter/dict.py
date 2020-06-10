# coding: utf-8

'''
Veredi's Adapter classes for interfacing specific codec backends to
Veredi systems.

E.g. the YAML tag '!grouped' should have a Veredi class to be its face. So when
a DB or JSON comes along they can just implement to the same thing.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, NewType, Mapping, Dict, Iterable, Tuple
from collections import abc
import re

from veredi.logger import log
from veredi.data import exceptions


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

DDKey = NewType('DDKey', Union[str, 'KeyGroupMarker'])

_KG_HASH = 'KeyGroup'
_UD_HASH = 'UserDefined'


# §-TODO-§ [2020-06-08]: Do I want python errors or VerediErrors raised here?


# -----------------------------------------------------------------------------
# Keys
# -----------------------------------------------------------------------------

# ---
# Grouping
# ---

class KeyGroupMarker(abc.Hashable):
    '''
    Placeholder for folks who want to build their data like, say:
    {
      'shenanigans': {...},
      'knowledge': {
        'weird stuff': {...},
      },
    }

    They can parse/translate 'knowledge' into this diet class, and DataDict
    will finish up for them:
    {
      'shenanigans': {...},
      KeyGroupMarker('knowledge'): {
        'weird stuff': {...}
      }
    }

    Pass that into a DataDict and it will pull the marker-key and its value out
    and turn them into a KeyGroup proper.
    '''

    def __init__(self, key: str) -> None:
        self._name: str = key
        self._hash: Tuple[str, str] = (_KG_HASH, self._name)

    @property
    def name(self) -> str:
        return self._name

    # ---
    # Hashable / Dict/Set Key Interface
    # ---
    def __hash__(self):
        # We'll hash out to our key's name plus
        return hash(self._hash)

    def __eq__(self, other):
        '''
        Define equality by hash in order to compare KeyGroupMarkers to
        KeyGroups and vice versa.
        '''
        return hash(self) == hash(other)

    # ---
    # To String
    # ---
    def __str__(self) -> str:
        return (f"{type(self).__name__}({self._name})")

    def __repr__(self) -> str:
        return (f"<{type(self).__name__}({self._name})>")


class KeyGroup(abc.MutableMapping, abc.Hashable):
    '''
    A list of elements with something in common has been grouped up. E.g.:
      - Knowledge skills.
    '''

    RE_FLAGS = re.IGNORECASE
    '''
    Don't care about case in our data.
    '''

    RE_SUB_KEY_FMT = r'^({name}).*?(\w[\w\d\s:\'"-]*\w).*?$'
    '''
    Matches:
      - start of string
      - group 0, who cares:
        - name
      - any number of anything, lazy
      - OUR GROUP!
        - something alphanumeric
        - any number of something printable-ish
        - something alphanumeric
      - who cares, lazy
      - end of string
    '''

    FULL_NAME_PAREN_FMT = '{name} ({sub_name})'
    '''Full Names with sub-name in parenthesis.
    E.g. "Knowledge (Weird Stuff)"'''
    FULL_NAME_COLON_FMT = '{name}: {sub_name}'
    '''Full Names with sub-name in parenthesis.
    E.g. "Profession: Weirdologist"'''

    def __init__(self,
                 name: Union[KeyGroupMarker, str],
                 values: Mapping[str, Any] = {},
                 re_claim: Union[re.Pattern, str, None] = None,
                 re_sub_key: Union[re.Pattern, str, None] = None,
                 full_name_fmt: Optional[str] = None) -> None:
        '''
        `name` is for our name/key. E.g. for the "Knowledge (Weird Things),
        Knowledge(Etc)" group, that would be "Knowledge."

        NOTE: `re_claim` that are re.Patterns should kindly use (or bitwise or
        into their own flags) the KeyGroup.RE_FLAGS.
        If no `re_claim`, the claim will be:
            '^' + name + '.*$'

        NOTE: `re_sub_key` that are re.Patterns should kindly use (or bitwise
        or into their own flags) the KeyGroup.RE_FLAGS.
        If no `re_sub_key`, the pattern will be:
            KeyGroup.RE_SUB_KEY_FMT.format(name=name)

          SUB-NOTE: Sub-key's match is in the second group! First group
          contains key's name!
        '''

        self._name: str = (name.name
                           if isinstance(name, KeyGroupMarker) else
                           name)
        '''
        Our name/key. E.g. for the "Knowledge (Weird Things), Knowledge(Etc)"
        group, that would be "Knowledge."
        '''

        self._hash: Tuple[str, str] = (_KG_HASH, self._name)
        '''Our values we care about for hashing purposes - shouldn't change
        during lifetime of object.'''

        self._mapping: Dict[str, Any] = {}
        '''Our group of sub-name/keys and their values.'''

        self._re_claim: re.Pattern = None
        '''Our re.Pattern for matching a full name & sub-name to us.'''

        self._re_sub_key: re.Pattern = None
        '''Our re.Pattern for matching a full name & sub-name to us.'''

        self._name_fmt: str = full_name_fmt or self.FULL_NAME_PAREN_FMT

        self._init_regex(re_claim, re_sub_key)

        # Want our regexes initialized before setting our _mapping based on
        # input values.
        self.update(values)

    def _init_regex(self,
                    re_claim:   Union[re.Pattern, str, None] = None,
                    re_sub_key: Union[re.Pattern, str, None] = None) -> None:
        '''
        Sets self._claim to an re.Pattern based on input.
        '''
        # ---
        # re_claim
        # ---
        if isinstance(re_claim, str):
            self._re_claim = re.compile(re_claim,
                                        re.IGNORECASE)
        elif isinstance(re_claim, re.Pattern):
            self._re_claim = re_claim
        else:
            self._re_claim = re.compile('^' + self._name + r'.*$',
                                        re.IGNORECASE)

        # ---
        # re_sub_key
        # ---
        if isinstance(re_sub_key, str):
            self._re_sub_key = re.compile(re_sub_key,
                                          re.IGNORECASE)
        elif isinstance(re_sub_key, re.Pattern):
            self._re_sub_key = re_sub_key
        else:
            match_str = self.RE_SUB_KEY_FMT.format(name=self._name)
            self._re_sub_key = re.compile(match_str,
                                          re.IGNORECASE)

    # ---
    # Full-Name / Full-Key
    # ---
    def full_name(self, sub_key: str) -> str:
        '''
        Turn a sub-key into a full-key / full-name.
        E.g. 'weird stuff' -> 'knowledge (weird stuff)'
        '''
        return self._name_fmt.format(self._name, sub_key)

    # ---
    # Name / Key
    # ---
    def matches(self, key: str) -> bool:
        '''
        Returns true if this key matches us.
        E.g. if we are 'knowledge' and key is too, yes.
        '''
        return self.normalize(self._name) == self.normalize(key)

    # ---
    # Sub-Key
    # ---
    def sub_key(self, full_name: Union[str, 'UserDefinedMarker']) -> str:
        '''
        Get a sub-key out of the `full_name`.
        E.g. for full_name == "Knowledge (Weird Stuff)":
          sub-key: "Weird Stuff"
        NOTE:
          Sub-key group should be group 2 according to re.Match.group()!
        '''
        if isinstance(full_name, (UserDefinedMarker,
                                  KeyGroupMarker,
                                  KeyGroup)):
            full_name = full_name.name

        retval = None
        result = self._re_sub_key.match(full_name)
        if result:
            # Group 0 is whole thing, group 1 is KeyGroup name, group 2
            # is sub-key.
            retval = result.group(2)
            if retval:
                retval = self.normalize(retval)
        else:
            # Couldn't match our full-name regex to get a sub-key out... assume
            # that we were given a sub-key instead?
            retval = self.normalize(full_name)

        return retval

    def normalize(self, input: str) -> str:
        '''
        Normalizes a string. Mostly just for lowercasing when KeyGroup.RE_FLAGS
        contains re.IGNORECASE.
        '''
        retval = input
        if (self.RE_FLAGS & re.IGNORECASE) == re.IGNORECASE:
            retval = retval.lower()

        return retval

    def claims(self, full_name: str):
        '''
        Returns true if this KeyGroup will claim `full_name` as a
        groupie of itself.
        '''
        match = self._re_claim.match(full_name)
        return bool(match)

    # ---
    # abc.MutableMapping
    # ---
    def __getitem__(self, key: str) -> Any:
        # Gotta turn full-name key into our sub-key, then check for it.
        subkey = self.sub_key(key)
        return self._mapping[subkey]

    def __delitem__(self, key: str) -> Any:
        subkey = self.sub_key(key)
        del self._mapping[subkey]

    def __setitem__(self, key: str, value: Any) -> None:
        subkey = self.sub_key(key)
        self._mapping[subkey] = value

    def __iter__(self) -> Iterable:
        return iter(self._mapping)

    def __len__(self) -> int:
        return len(self._mapping)

    # ---
    # abc.Container
    # ---
    def __contains__(self, key: str) -> bool:
        subkey = self.sub_key(key)
        return subkey in self._mapping

    # ---
    # abc.Hashable: Dict/Set Key Interface
    # ---
    def __hash__(self):
        # We'll hash out to our key's name plus
        return hash(self._hash)

    def __eq__(self, other):
        '''
        Define equality by hash in order to compare KeyGroupMarkers to
        KeyGroups and vice versa.
        '''
        return hash(self) == hash(other)

    # ---
    # To String
    # ---
    def __str__(self) -> str:
        return (f"{type(self).__name__}({self._name}, {self._mapping}, "
                f"{self._re_claim}, {self._re_sub_key})")

    def __repr__(self) -> str:
        return (f"{type(self).__name__}({self._name}, {self._mapping}, "
                f"{self._re_claim}, {self._re_sub_key})")


class UserDefinedMarker(abc.Hashable):
    '''
    An element that usually has a rule/data-defined name should instead have
    one defined by user in this instance. E.g.:
      - Profession skills can have the specific profession defined by user.
    '''

    def __init__(self, key: str) -> None:
        self._name: str = key
        self._hash: Tuple[str, str] = (_UD_HASH, self._name)

    @property
    def name(self) -> str:
        return self._name

    # ---
    # Hashable / Dict/Set Key Interface
    # ---
    def __hash__(self):
        # We'll hash out to our key's name plus
        return hash(self._hash)

    def __eq__(self, other):
        '''
        Define equality by hash in order to compare UserDefinedMarker to
        UserDefined and vice versa.
        '''
        return hash(self) == hash(other)

    # ---
    # To String
    # ---
    def __str__(self) -> str:
        return (f"{type(self).__name__}({self._name})")

    def __repr__(self) -> str:
        return (f"<{type(self).__name__}({self._name})>")


# -----------------------------------------------------------------------------
# Mappings
# -----------------------------------------------------------------------------

class DataDict(abc.MutableMapping):
    '''
    Custom dictionary class to deal with some oddities like key groups. A
    KeyGroup of e.g. 'knowledge' should know what it contains, and should
    answer "Yep." if the dictionary says, "Hey, any 'knowledge (weird things)'
    in me?"

    So to do this, the dictionary should know what keys to just check cuz
    they're e.g. strings and what to prod a little deeper into.
    '''

    def __init__(self,
                 data: Mapping[DDKey, Any] = {}) -> None:
        self._mapping = {}
        self._grouping = set()
        self.update_all(data)

    def normalize(self, input: str) -> str:
        '''
        Normalizes a string. Mostly just for lowercasing when KeyGroup.RE_FLAGS
        contains re.IGNORECASE.
        '''
        retval = input
        if isinstance(retval, str):
            retval = retval.lower()
        return retval

    # ---
    # abc.MutableMapping
    # ---
    def __getitem__(self, key: DDKey) -> Any:
        key = self.normalize(key)
        if key in self._mapping:
            return self._mapping[key]

        # Not in our map - check the KeyGroups.
        for each in self._grouping:
            if key in each:
                return each[key]

        raise log.exception(KeyError("Key is not in mapping or KeyGroups.",
                                     key),
                            exceptions.LoadError,
                            "Key {} is not in mapping or KeyGroups. "
                            "map: {}, groups: {}",
                            key, self._mapping, self._grouping)

    def __delitem__(self, key: DDKey) -> Any:
        del self._mapping[key]

    def __setitem__(self, key: DDKey, value: Any) -> None:
        if isinstance(key, KeyGroupMarker):
            key = key.name
            self.update_group(key, value)
        elif isinstance(key, str):
            self.update_map(key, value)

    def __iter__(self) -> Iterable:
        '''
        Iterates dict keys first, then iterates each KeyGroup's subkeys.
        '''
        return DataDictIterator(self._mapping, self._grouping)

    def __len__(self) -> int:
        # TOOD: len of each grouping, or is this right?
        return len(self._mapping) + len(self._grouping)

    # ---
    # abc.MutableMapping
    # ---
    def _update_get_kv(self,
                       key: Union[str, Tuple[str, Any]],
                       data: Union[Mapping, Iterable]) -> DDKey:
        '''
        Gets value from either:
          - `key` Tuple of (actually_the_key, value)
          - `data[key]`

        Normalizes returned key before returning it.
        '''
        if isinstance(data, abc.Mapping):
            return self.normalize(key), data[key]
        elif isinstance(key, abc.Sequence):
            return self.normalize(key[0]), key[1]
        else:
            raise log.exception(TypeError("Can't get kv from unknown source.",
                                          key, data),
                                exceptions.LoadError,
                                "Key is not tuple and data is not a map, so "
                                "no idea where to get value from.",
                                key, data)

    def update_all(self, data: Union[Mapping, Iterable]) -> None:
        '''
        Update our mapping/groups with data.
        '''
        for each in data:
            key, value = self._update_get_kv(each, data)
            if isinstance(key, KeyGroupMarker):
                self.update_group(key, value)
            else:
                self.update_map(key, value)

    def update_group(self,
                     key: KeyGroupMarker,
                     value: Mapping[str, Any]) -> None:
        # Find any existing group and remove...
        # Can do this because of how hash/eq is implement in
        # KeyGroups and KeyGroupMarkers.
        if key in self._grouping:
            self._grouping.discard(key)

        # Then add this one.
        self._grouping.add(KeyGroup(key, value))

    def update_map(self,
                   key: str,
                   value: Any) -> None:
        self._mapping[key] = value

    # ---
    # abc.Container
    # ---
    def __contains__(self, desired: DDKey) -> bool:
        '''
        A more complicated 'x in here' check than iterating keys
        looking for ==.

        If no exact match, but a KeyGroup says they have an exact match,
        use that.
        '''
        retval = False
        if desired in self._mapping:
            retval = self._mapping[desired]

        for group in self._grouping:
            if desired in group:
                retval = group[desired]
                break

        # Don't eval all them args unless it'll be used...
        if log.will_output(log.Level.DEBUG):
            log.debug("{}('{}') contains '{}'? {}",
                      self.__class__.__name__,
                      self._name,
                      desired, retval)
        return retval

    # ---
    # To String
    # ---
    def __str__(self) -> str:
        return f"{type(self).__name__}({self._mapping})"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._mapping})"


class DataDictIterator(abc.Iterable):

    def __init__(self, mapping, grouping):
        self._map_iter = iter(mapping)
        self._group_iter = None
        self._group = grouping
        self._group_index = 0
        self._group_len = len(grouping)
        if self._group_len > 0:
            self._group_iter = iter(grouping[0])

    # ---
    # abc.Iterator
    # ---
    def __iter__(self):
        return self

    def __next__(self):
        '''
        Returns next item in iteration.
        '''
        if self._map_iter:
            try:
                return next(self._map_iter)
            except StopIteration:
                # Done with iterating the map; move on to groups.
                self._map_iter = None

        if not self._group_iter:
            self._group_index += 1
            if self._group_index < self._group_len:
                self._group_iter = iter(self._group[self._group_index])
            else:
                self._group_iter = None

        if self._group_iter:
            try:
                return next(self._group_iter)
            except StopIteration:
                # Done with iterating this group; move on to the next group.
                self._group_iter = None
                return self.__next__()

        # Falling through to here means we're all done.
        raise StopIteration
