# coding: utf-8

'''
d20 Player Entity
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
from abc import ABC, abstractmethod

# Framework

# Our Stuff
from veredi.logger import log

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

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

    def get(*names):
        '''Returns var defined by names.
           e.g. get_var('ability', 'strength') -> 12

        Returns:
          value or None
        '''
        value = self.data
        for each in names:
            value = value.get(each, None)
            if value is None:
                return None

        return value

    def recalculate():
        '''Recalculate all player fields that are not constant.'''
        log.error("TODO: implement this.")

# ${variable.name}
# $function(arg0, ...argN)


# -----------------------------------Veredi------------------------------------
# --                     Main Command Line Entry Point                       --
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    print("hello...")
