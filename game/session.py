# coding: utf-8

'''
A session of a game/campaign.
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

# Session is:
#   in charge of everything happening/happened this session.
#     - players present
#     - rolls done
#     - monsters, loot....?
#
# should get:
#   campaign obj
#   player objs
#   mather/roller obj(s)?
#   ref to game for e.g. requesting saves/loads to/from repos?
#
# then...?
#   be ready to do shit?


# TODO delete this class until we actually use or need it?

class Session:
    def __init__(self, campaign, user_player_pairs, repository):
        self.campaign = campaign
        self.players = {}
        for each in user_player_pairs:
            user = each[0]
            player = each[1]
            data = repository.load_by_name(user, campaign, player)
            self.players[player] = data

        print(self.campaign, self.players)

    def roll(self, name, expression):
        print(f"todo: {name} wants to roll '{expression}'")
