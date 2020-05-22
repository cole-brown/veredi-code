# coding: utf-8

'''
d20 Player Entity
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
from abc import ABC, abstractmethod
from collections.abc import Iterable
import enum

# Framework

# Our Stuff
from veredi.logger import log
from veredi.thesaurus.d20 import thesaurus
from .. import exceptions
from veredi.base.exceptions import KeyError

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Context:
    def __init__(self, keys, value):
        self._keys = keys
        self._value = value

    @property
    def keys(self):
        return self._keys

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value


class Entity(ABC):
    '''Base class for all players, NPCs, monsters, mayhem,
    shark-based tornados...'''
    def __init__(self, data):
        self.data = data

    def create(self, *templates):
        for each in templates:
            self._apply(each)
            self._verify(each)

    def apply(self, template):
        log.error("TODO: implement this.")

    def verify(self, template):
        log.error("TODO: implement this.")


class Player(Entity):

    def __init__(self, data):
        self._data = data.get('player', {})
        self._data_user = data.get('user', {})
        self._data_campaign = data.get('campaign', {})

    # --------------------------------------------------------------------------
    # API
    # --------------------------------------------------------------------------

    def get(self, *names):
        '''Returns var defined by names, enums, aliases, etc.
        Checks/replaces in var for known additional keys to replace.

        Example for data:
          {'ability': {
            'charisma': {
              'score': 14,
              'modifier': '(${this.score} - 10) // 2'
              }}}

          character.get_raw('ability', 'charisma', 'modifier')
          -> '(${this.score} - 10) // 2'

          character.get('ability', 'charisma', 'modifier')
          -> '(14 - 10) // 2'
        '''
        value = self._data
        keys = self._get_keys(*names)
        for each in keys:
            value = value.get(each, None)
            if value is None:
                break

        # This will give us a context in case we just returned e.g.:
        #   '(${this.score} - 10) // 2'
        # We're gonna be asked what 'this.score' is soon and need them to
        # remember what 'this' is...
        return Context(keys, value)

    def get_raw(self, *names):
        '''Returns var defined by names, enums, aliases, etc
        examples:
          get('ability', 'strength') -> 12
          get(ability.strength) -> 12
          get('str') -> 12
          get(str) -> 12

        Returns:
          value or None
        '''
        value = self._data
        keys = self._get_keys(*names)
        for each in keys:
            value = value.get(each, None)
            if value is None:
                return None

        return value

    # def recalculate(self):
    #     '''Recalculate all player fields that are not constant.'''
    #     log.error("TODO: implement this.")
    #     # Do we want a full recalc on call, or do we want to lazy recalc just
    #     # whatever we need when we need it?

    # --------------------------------------------------------------------------
    # Keys
    # --------------------------------------------------------------------------

    def _get_keys(self, *names):
        keyring = []
        for each in names:
            keys = self._to_keys(each)
            if isinstance(keys, Iterable) and not isinstance(keys, str):
                keyring.extend(keys)
            else:
                keyring.append(keys)
        return keyring

    def _to_keys(self, name):
        key = self._to_keys_direct(name)
        if key:
            return key
        key = self._to_keys_value(name)
        if key:
            return key
        key = self._to_keys_dotted(name)
        if key:
            return key
        key = self._to_keys_str(name)
        if key:
            return key

        raise KeyError(
            f"Failed to translate key {name} into key string.",
            None,
            None)  # TODO: Make context? player name, campaign, user name?

    def _to_keys_direct(self, name):
        try:
            # 0) Check for a direct key (from e.g. enum).
            if name.key:
                return name.key
        except AttributeError:
            pass
        return None

    def _to_keys_value(self, name):
        try:
            # 1) Check for a value (from e.g. enum).
            if name.value:
                return name.value
        except AttributeError:
            pass
        return None

    def _to_keys_dotted(self, name):
        # 2) Check for a string of keys separated by dots.
        try:
            dotted_gen = self._dotted_split(name)
            if dotted_gen:
                return [each for each in dotted_gen]
        except AttributeError:
            pass
        return None

    def _to_keys_str(self, name):
        # 3) Finally, is it a (single) key itself?
        return str(name)

    def _dotted_split(self, name):
        start = 0
        while True:
            index = name.find('.', start)
            if index == -1:
                break
            yield name[start:index]
            start = index + 1


# -----------------------------------Veredi------------------------------------
# --                     Main Command Line Entry Point                       --
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    print("hello...")
