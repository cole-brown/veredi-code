# coding: utf-8

'''
Manages a collection of repos that, combined, will be used in a game/session.
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

class Manager:
    '''Manages a collection of repos that, combined, will be used in a
    game/session.

    '''
    def __init__(self, campaign, session, player):  # ...monster, item, etc...)
        self.campaign = campaign
        self.session = session
        self.player = player

        # TODO: Do we need to mediate to make this easier on the game/session?
        # e.g. let session say
        #   "manager.mediate(player1)"
        # or
        #   "manager.save(player1)"
        # or whatever. Then let this figure out any special cases or complicated
        # interactions... See 'mediator design pattern'.
