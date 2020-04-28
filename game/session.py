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

class Session:
    def __init__(self, campaign, user_player_pairs, loader):
        self.campaign = campaign
        self.players = {}
        for each in user_player_pairs:
            user = each[0]
            player = each[1]
            data = loader.get_by_name(user, campaign, player)
            self.players[player] = data

        print(self.campaign, self.players)

    def roll(self, name, expression):
        print(f"todo: {name} wants to roll '{expression}'")
