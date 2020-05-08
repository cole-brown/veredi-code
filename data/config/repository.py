# coding: utf-8

'''
Helpers for turning structured data from config files into configuration.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.data.config.registry import register
from veredi.logger import log
from .. import exceptions

from veredi.data.repository import (manager,
                                    player)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------



# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


class ConfigRepo:

    def __init__(self, config_data):
        self.data_owner = config_data.owner
        self.data_campaign = config_data.campaign
        self.data_session = config_data.session
        self.data_player = config_data.player
        self._verify()
        self._set_up()

    def _verify(self):
        # TODO: better? assume verified because data loader should verify data?
        pass

    def _set_up(self):
        # TODO: this
        pass

    @classmethod
    def from_yaml(cls, loader, node):
        return loader.construct_yaml_object(node, cls)

    def __str__(self):
        return (f"{self.__class__.__name__}:\n"
                f"  owner:    {self.owner if hasattr(self, 'owner') else 'no own'}\n"
                f"  campaign: {self.campaign if hasattr(self, 'campaign') else 'no camp'}\n"
                f"  session:  {self.session if hasattr(self, 'session') else 'no sess'}\n"
                f"  player:   {self.player if hasattr(self, 'player') else 'no plr'}\n")
