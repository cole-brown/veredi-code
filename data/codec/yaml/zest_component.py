# coding: utf-8

'''
Unit tests for reading a component from yaml data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest
import os

from veredi.logger import log
from veredi.logger import pretty
from veredi.data import exceptions

# from . import component
# from ...repository.template.template import default_root
# from .codec import YamlCodec

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


# class Test_Component(unittest.TestCase):
#     def setUp(self):
#         # d:/Users/spydez/Dropbox/share-work/idea-dice/veredi/veredi/data/repository/template/template.py
#
#         self.data_root = os.path.join(default_root(),
#                                       'd20', 'component')
#         self.path = os.path.join(self.data_root,
#                                  'component.health.yaml')
#
#         self.data_codec = YamlCodec()
#
#     def tearDown(self):
#         self.data_root = None
#         self.path = None
#         self.data_codec = None
#
#     # --------------------------------------------------------------------------
#     # Read file?
#     # --------------------------------------------------------------------------
#
#     def test_load(self):
#         self.load()
#         # self.assertTrue(conf)
#         # self.assertIsInstance(conf.repository, manager.Manager)
#         # self.assertIsInstance(conf.repository.player, player.PlayerRepository)
#         # self.assertIsInstance(conf.repository.player, player.PlayerFileTree)
#         #
#         # self.assertEqual(conf.repository.player.root,
#         #                  os.path.abspath("test/owner/repository/player/"))
#
#     def load(self):
#         '''Raises LoadError'''
#         with open(self.path, 'r') as file_obj:
#             # Can raise an error - we'll let it.
#             try:
#                 log.debug(f"data codec: {self.data_codec}")
#                 generator = self.data_codec._load_all(file_obj,
#                                                       {"unit-testing":"Test_Component.load"})
#                 for each in generator:
#                     log.debug("loading doc: {}", each)
#                     self.load_doc(each)
#             except exceptions.LoadError:
#                 # Let this one bubble up as-is.
#                 data = None
#                 raise
#             except Exception as error:
#                 # Complain that we found an exception we don't handle.
#                 # ...then let it bubble up as-is.
#                 log.exception(error, "Unhandled exception! type: {}, str: {}",
#                               type(error), str(error))
#                 data = None
#                 raise
#
#     def load_doc(self, document):
#         # print(f"loaded doc: {pretty.to_str(document.__dict__)}")
#         pass
#         # # if isinstance(document, codec_yaml.DocMetadata):
#         # #     self.data_meta = document
#         # # elif isinstance(document, config_yaml.DocRepository):
#         # #     self.data_repo = document
#         # # else:
#         # #     log.error("Unknown document while loading! {}: {}",
#         # #               type(document),
#         # #               str(document))
#         # #     raise exceptions.LoadError(f"Unknown document while loading! "
#         # #                                f"{type(document)}: {str(document)}",
#         # #                                None,
#         # #                                self.to_context(document=document))
#
#
#
# # --------------------------------Unit Testing----------------------------------
# # --                      Main Command Line Entry Point                       --
# # ------------------------------------------------------------------------------
#
# if __name__ == '__main__':
#     # log.set_level(log.Level.DEBUG)
#     unittest.main()
