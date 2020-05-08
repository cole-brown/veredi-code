# coding: utf-8

'''
YAML Format Reader / Writer
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import yaml


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------



# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


class DocRepository(yaml.YAMLObject):
    yaml_loader = yaml.SafeLoader
    yaml_tag = '!repository'

    @classmethod
    def from_yaml(cls, loader, node):
        return loader.construct_yaml_object(node, cls)

    def __str__(self):
        return (f"{self.__class__.__name__}:\n"
                f"  owner:    {self.owner if hasattr(self, 'owner') else 'no own'}\n"
                f"  campaign: {self.campaign if hasattr(self, 'campaign') else 'no camp'}\n"
                f"  session:  {self.session if hasattr(self, 'session') else 'no sess'}\n"
                f"  player:   {self.player if hasattr(self, 'player') else 'no plr'}\n")
