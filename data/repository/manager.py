# coding: utf-8

'''
Manages a collection of repos that, combined, will be used in a game/session.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Iterable, Tuple

from .base import BaseRepository

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class RepositoryManager:
    '''Manages a collection of repos that, combined, will be used in a
    game/session.

    '''
    def __init__(self,
                 repositories: Iterable[Tuple[int, BaseRepository]]):
        '''
        Takes an iterable of tuples of (type_id, repository_type). Creates and
        manages those repositories.
        '''
        self._repositories = {}
#         for each in repositories:
#             print("hi", "manager: {each}")
#             self._repositories[each[0]] = each[1]()

        # TODO: Do we need to mediate to make this easier on the game/session?
        # e.g. let session say
        #   "manager.mediate(player1)"
        # or
        #   "manager.save(player1)"
        # or whatever. Then let this figure out any special cases or complicated
        # interactions... See 'mediator design pattern'.
