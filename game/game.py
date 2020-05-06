# coding: utf-8

'''
A game of something or other.
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

# Game is:
#   manager of whole shebang
#
# game should get:
#   campaign info (name, owner?, system?, ...)
#   repo... types?
#
# game should then:
#   load campaign from repo into Campaign obj
#   get player infos (user & player names, ...)
#   load players
#
# then...?
#   make or load Session
#     w/ campaign, players, etc?
#
# then...?
#   be ready to do shit?


class Game:
    def __init__(self, owner, campaign, repo_manager):
        self.repo = repo_manager
        self.owner = owner
        self.campaign = campaign


# TODO: config file for initial setup - like repo types, locations?
