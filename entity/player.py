# coding: utf-8

'''
Player Entity
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
# import datetime

# Framework

# Our Stuff


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Entity:
    '''Base class for all players, NPCs, monsters, mayhem,
    shark-based tornados...'''
    def __init__(self, data):
        self.data = data

class Player(Entity):

    def get_var(*names):
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


# -----------------------------------Veredi------------------------------------
# --                     Main Command Line Entry Point                       --
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    print("hello...")
