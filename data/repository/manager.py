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


# Â§-TODO-Â§ [2020-05-26]: delete this file?




# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class RepositoryManager:
    '''Manages a collection of repos that, combined, will be used in a
    game/session.

    '''

    # Â§-TODO-Â§ [2020-05-26]: Take in config data, not already-constructed repos.
    def __init__(self,
                 repositories: Iterable[BaseRepository]):
        '''
        Takes an iterable of repositories. Creates and
        manages those repositories.
        '''
        self._repositories = {}
#         for each in repositories:
#             self._repositories[] = each[1]()
#
#
#
#
#         # TODO: Do we need to mediate to make this easier on the game/session?
#         # e.g. let session say
#         #   "manager.mediate(player1)"
#         # or
#         #   "manager.save(player1)"
#         # or whatever. Then let this figure out any special cases or complicated
#         # interactions... See 'mediator design pattern'.
#
#     def context(self, other: VerediContext):
#         '''
#         Get correct context from correct repository base on other's
#         passed-in context.
#         '''
#         return -1
#
