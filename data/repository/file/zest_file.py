# coding: utf-8

'''
Tests for the FileTreeRepository.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional


import os
import enum


from veredi.zest                  import zpath
from veredi.zest                  import zmake
from veredi.zest.base.unit        import ZestBase


from veredi.logger                import log
from veredi.base                  import paths

from veredi.data.exceptions       import LoadError
from veredi.data.config.hierarchy import Document
from veredi.data.config.context   import ConfigContext
from veredi.data.context          import (DataAction,
                                          DataLoadContext,
                                          DataSaveContext)
from veredi.data.records          import DataType


from .file                        import FileTreeRepository
from .taxon                       import Taxon, SavedTaxon
from veredi.rules.d20.pf2.game    import PF2Rank, PF2SavedTaxon


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_FileTreeRepo(ZestBase):

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    @enum.unique
    class TestLoad(enum.Enum):
        '''
        Enum for context_load().
        '''

        PLAYER  = [PF2Rank.Phylum.PLAYER,  ['u/jeff', 'Sir Jeffsmith']]
        MONSTER = [PF2Rank.Phylum.MONSTER, ['dragon', 'aluminum dragon']]
        NPC     = [PF2Rank.Phylum.NPC,     ['Townville', 'Sword Merchant']]
        ITEM    = [PF2Rank.Phylum.ITEM,    ['weapon', 'Sword, Ok']]

    # -------------------------------------------------------------------------
    # Set-Up
    # -------------------------------------------------------------------------

    def set_up(self) -> None:
        self.path = zpath.repository_file_tree()
        self.config = zmake.config()
        self.context = ConfigContext(self.path,
                                     'veredi.data.repository.zest_file',
                                     id=zpath.config_id(self._TEST_TYPE, None))

        # Finish set-up. Inject stuff repo needs to init proper.
        self.config.ut_inject(self.path,
                              Document.CONFIG,
                              'data',
                              'repository',
                              'directory')

        # TODO [2020-06-01]: Register these, have config read dotted and
        # get from registry.
        self.config.ut_inject('veredi.sanitize.human.path-safe',
                              Document.CONFIG,
                              'data',
                              'repository',
                              'sanitize')

        # Should be enough info to make our repo now.
        self.repo = FileTreeRepository(self.context)

    # -------------------------------------------------------------------------
    # Tear-Down
    # -------------------------------------------------------------------------

    def tear_down(self) -> None:
        self.repo = None
        self.path = None

    # -------------------------------------------------------------------------
    # Load Helpers
    # -------------------------------------------------------------------------

    def context_load(self,
                     load:   Optional['Test_FileTreeRepo.TestLoad'] = None
                     ) -> DataLoadContext:
        '''
        Create a DataLoadContext given `taxonomy` OR `by_enum`.
        '''
        # ------------------------------
        # Get values from `load` enum.
        # ------------------------------
        phylum = load.value[0]
        taxonomy = load.value[1]

        # ------------------------------
        # Create the context.
        # ------------------------------
        context = None
        with log.LoggingManager.on_or_off(self.debugging):
            taxon = PF2SavedTaxon(phylum, *taxonomy)
            context = DataLoadContext(self.dotted(__file__),
                                      taxon)

        return context

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_init(self) -> None:
        self.assertTrue(self.repo)
        self.assertTrue(self.path)
        self.assertTrue(os.path.isdir(self.path))

    def do_load_test(self,
                     load:   Optional['Test_FileTreeRepo.TestLoad'] = None
                     ) -> None:
        with log.LoggingManager.on_or_off(self.debugging):
            context = self.context_load(load)

        # Did we get something?
        self.assertTrue(context)
        self.assertIsInstance(context, DataLoadContext)

        self.assertTrue(context.taxon)
        self.assertIsInstance(context.taxon, Taxon)
        self.assertIsInstance(context.taxon, SavedTaxon)

        self.assertTrue(context.dotted())
        self.assertEqual(context.dotted(), self.dotted(__file__))

        self.assertTrue(context.action)
        self.assertIsInstance(context.action, DataAction)
        self.assertEqual(context.action, DataAction.LOAD)

        # Shouldn't have repo context yet - haven't given it to repo yet.
        repo_ctx = context.repo_data
        self.assertFalse(repo_ctx)

        # Ok; give to repo to load...
        loaded_stream = self.repo.load(context)
        self.assertIsNotNone(loaded_stream)

        # And now the repo context should be there.
        repo_ctx = context.repo_data
        self.assertTrue(repo_ctx)
        self.assertTrue(repo_ctx['meta'])
        self.assertTrue(repo_ctx['path'])
        path = paths.cast(repo_ctx['path'])
        self.assertTrue(path)

        # read file directly, assert contents are same.
        with path.open(mode='r') as file_stream:
            self.assertIsNotNone(file_stream)

            file_data = file_stream.read(None)
            repo_data = loaded_stream.read(None)
            self.assertIsNotNone(file_data)
            self.assertIsNotNone(repo_data)
            self.assertEqual(repo_data, file_data)

    def test_load_player(self) -> None:
        self.do_load_test(self.TestLoad.PLAYER)

    def test_load_monster(self) -> None:
        self.do_load_test(self.TestLoad.MONSTER)

    def test_load_npc(self) -> None:
        self.do_load_test(self.TestLoad.NPC)

    def test_load_item(self) -> None:
        self.do_load_test(self.TestLoad.ITEM)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.data.repository.zest_file

if __name__ == '__main__':
    import unittest
    unittest.main()
