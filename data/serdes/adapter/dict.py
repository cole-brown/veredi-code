# coding: utf-8

'''
Veredi's Adapter classes for interfacing specific serdes backends to
Veredi systems.

E.g. the YAML tag '!grouped' should have a Veredi class to be its face. So when
a DB or JSON comes along they can just implement to the same thing.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, Any, NewType, Mapping, Iterable, Tuple
from collections import abc

from veredi.logger import log
from veredi.data import exceptions
from veredi.base import vstring

from .group import KeyGroupMarker, KeyGroup


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

DDKey = NewType('DDKey', Union[str, 'KeyGroupMarker'])


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
        Normalizes a string. Returns non-strings unharmed.
        '''
        retval = input
        if isinstance(retval, str):
            retval = vstring.normalize(input)
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

        # Don't log - is a valid/normal exception for e.g.
        #   dd_obj.get('key', None)
        raise KeyError("Key is not in mapping or KeyGroups.", key)

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

        # # Don't eval all them args unless it'll be used...
        # if log.will_output(log.Level.DEBUG):
        #     log.debug("{} contains '{}'? {}",
        #               self.__class__.__name__,
        #               desired, retval)
        return retval

    # ---
    # To String
    # ---
    def __str__(self) -> str:
        return f"{type(self).__name__}({self._mapping})"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._mapping})"


# ------------------------------
# Iterator Helper
# ------------------------------

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
