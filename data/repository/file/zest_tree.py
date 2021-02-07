# coding: utf-8

'''
Tests for the FileTreeRepository.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional


import shutil
import enum
from io import TextIOBase


from veredi.zest                  import zpath
from veredi.zest                  import zmake
from veredi.zest.base.unit        import ZestBase


from veredi.logger                import log
from veredi.base                  import paths

from veredi.base.exceptions       import VerediError
from veredi.data.exceptions       import LoadError, SaveError
from veredi.zest.exceptions       import UnitTestError

from veredi.data.config.hierarchy import Document
from veredi.data.config.context   import ConfigContext
from veredi.data.context          import (DataAction,
                                          DataLoadContext,
                                          DataSaveContext)

from .tree                        import FileTreeRepository
from ..taxon                      import Taxon, SavedTaxon
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
    class TaxonCtx(enum.Enum):
        '''
        Enum for context_load().
        '''
        GAME    = None  # Use PF2SavedTaxon.game().
        PLAYER  = [PF2Rank.Phylum.PLAYER,  ['u/jeff', 'Sir Jeffsmith']]
        MONSTER = [PF2Rank.Phylum.MONSTER, ['dragon', 'aluminum dragon']]
        NPC     = [PF2Rank.Phylum.NPC,     ['Townville', 'Sword Merchant']]
        ITEM    = [PF2Rank.Phylum.ITEM,    ['weapon', 'Sword, Ok']]

    # -------------------------------------------------------------------------
    # Set-Up
    # -------------------------------------------------------------------------

    def set_up(self) -> None:
        # ---
        # Paths
        # ---
        self.root = zpath.repository_file_tree()
        self.root_temp = None

        self.filename = 'saved.yaml'
        self.path_rel = paths.cast('saved', 'test-campaign', 'game')
        self.path_file = paths.cast(self.root, self.path_rel, self.filename)
        self.path_temp = None
        self.path_temp_file = None

        # ---
        # Create a Repo.
        # ---
        self.config = zmake.config()
        self.context = ConfigContext(self.root,
                                     self.dotted(__file__),
                                     id=zpath.config_id(self._TEST_TYPE, None))

        # Finish set-up. Inject stuff repo needs to init proper - force them to
        # be this for this test.
        self.config.ut_inject(self.root,
                              Document.CONFIG,
                              'data',
                              'repository',
                              'directory')
        self.config.ut_inject('veredi.paths.sanitize.human',
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
        # ---
        # Delete temp dir if needed.
        # ---
        if not self.root:
            self.root = zpath.repository_file_tree()
        if not self.repo.root():
            self.repo._root = self.root
        if not self.root_temp:
            self.root_temp = self.repo._path_temp()
        if self.root_temp.exists():
            self._tear_down_repo()

        # ---
        # Clear out our vars...
        # ---
        self.repo           = None
        self.context        = None
        self.config         = None

        self.path_temp_file = None
        self.path_temp      = None
        self.path_file      = None
        self.path_rel       = None
        self.filename       = None
        self.root_temp      = None
        self.root           = None

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _set_temp_paths(self):
        # We need a root.
        self.assertTrue(self.repo.root())
        self.assertEqual(self.repo.root(), self.root)

        # Set test's `root_temp` and make sure it doesn't exist yet.
        self.root_temp = self.repo.root(True)
        self.assertTrue(self.root_temp)
        self.assertFalse(self.root_temp.exists(),
                         f"Delete temp repo dir please: {self.root_temp}")

        # Set test's `path_temp_file`. Can't exist yet.
        self.path_temp_file = self.repo._path_temp(self.path_file)
        self.path_temp = self.path_temp_file.parent
        expected = self.root_temp / self.path_rel / self.filename
        self.assertTrue(self.path_temp_file, expected)
        self.assertFalse(self.path_temp_file.exists())

    def _set_up_repo(self):
        '''
        Call our set-up helpers:
          - _set_temp_paths()
          - repo._ut_set_up()
        '''
        # Need it to have a root for the set-up to work.
        self.assertTrue(self.repo.root())
        self.assertEqual(self.repo.root(), self.root)

        # Get all set up...
        self._set_temp_paths()
        self.repo._ut_set_up()

        # Now our temp dir should exist.
        self.assertTrue(self.root_temp.exists())

    def _tear_down_repo(self):
        '''
        Call our tear-down helpers:
          - repo._ut_tear_down()
        '''
        self.repo._ut_tear_down()

        # Now our temp dir should not exist.
        if self.root_temp.exists():
            self.fail(f"temp exists... root is: {self.repo.root()}")
        self.assertFalse(self.root_temp.exists())

    def context_load(self,
                     load: Optional['Test_FileTreeRepo.TaxonCtx'] = None
                     ) -> DataLoadContext:
        '''
        Create a DataLoadContext given `load` taxonomy.
        '''
        taxon = None
        context = None

        # ------------------------------
        # GAME has a shortcut...
        # ------------------------------
        if load == self.TaxonCtx.GAME:
            taxon = PF2SavedTaxon.game()

        # ------------------------------
        # Everyone else: act normal!
        # ------------------------------
        else:
            # ------------------------------
            # Get values from TaxonCtx enum.
            # ------------------------------
            phylum = load.value[0]
            taxonomy = load.value[1]
            taxon = PF2SavedTaxon(phylum, *taxonomy)

        # ------------------------------
        # Create the context.
        # ------------------------------
        context = None
        with log.LoggingManager.on_or_off(self.debugging):
            context = DataLoadContext(self.dotted(__file__),
                                      taxon)

        return context

    def context_save(self,
                     save: 'Test_FileTreeRepo.TaxonCtx',
                     temp: bool) -> DataLoadContext:
        '''
        Create a DataSaveContext given `save` taxonomy and `temp` flag.
        '''
        taxon = None
        context = None

        # ------------------------------
        # GAME has a shortcut...
        # ------------------------------
        if save == self.TaxonCtx.GAME:
            taxon = PF2SavedTaxon.game()

        # ------------------------------
        # Everyone else: act normal!
        # ------------------------------
        else:
            # ------------------------------
            # Get values from TaxonCtx enum.
            # ------------------------------
            phylum = save.value[0]
            taxonomy = save.value[1]
            taxon = PF2SavedTaxon(phylum, *taxonomy)

        # ------------------------------
        # Create the context.
        # ------------------------------
        with log.LoggingManager.on_or_off(self.debugging):
            context = DataSaveContext(self.dotted(__file__),
                                      taxon,
                                      temp)

        return context

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_init(self) -> None:
        # ---
        # Paths
        # ---
        self.assertTrue(self.root)
        self.assertIsInstance(self.root, paths.Path)
        # self.root_temp isn't set until `_set_up_repo()`.
        self.assertFalse(self.root_temp)
        # self.path_file should be pointing to a real file already.

        self.assertTrue(self.path_file)
        self.assertIsInstance(self.path_file, paths.Path)
        self.assertTrue(self.path_file.exists())
        self.assertTrue(self.path_file.is_file())

        # ---
        # The Repo
        # ---
        self.assertTrue(self.repo)
        self.assertEqual(self.repo.root(), self.root)
        self.assertTrue(self.root.exists())
        self.assertTrue(self.root.is_dir())

        # repo's temp dir shouldn't exist until `_set_up_repo()`.
        temp_dir = self.repo.root(temp=True)
        self.assertTrue(temp_dir)
        self.assertIsInstance(temp_dir, paths.Path)
        self.assertFalse(temp_dir.exists())
        # ...but its parent should be the root.
        self.assertTrue(temp_dir.parent, self.root)
        self.assertTrue(temp_dir.parent.exists())

    def test_glob(self) -> None:
        # These should be the same result just different inputs.
        globbed_full = self.repo._ext_glob(self.path_file)

        self.assertNotEqual(globbed_full, self.path_file)
        self.assertNotEqual(globbed_full.suffix, self.path_file.suffix)
        self.assertEqual(globbed_full.suffix, '.*')
        self.assertEqual(globbed_full.stem, self.path_file.stem)

    def test_path_temp(self) -> None:
        # Test out our FileTreeRepository._path_temp() function that we'll be
        # using in test_save().
        self.assertTrue(self.repo)

        # Temp paths shouldn't be set-up just yet...
        self.assertFalse(self.root_temp)
        self.assertFalse(self.path_temp_file)
        self.assertFalse(self.path_temp)

        # So set the up.
        self._set_temp_paths()
        self.assertTrue(self.root_temp)
        self.assertTrue(self.path_temp_file)
        self.assertTrue(self.path_temp)

        # Don't care about this file name... Anything will do.
        path_in = "jeff.file-does-not-exist.txt"

        # Tree repo does have a root to start with now, and it should be our
        # root.
        self.assertTrue(self.repo.root())
        self.assertEqual(self.repo.root(), self.root)

        # ------------------------------
        # Success Cases: Rooted
        # ------------------------------

        # ---
        # The more expected use-case: when the repo actually has a root.
        # ---

        # Ask for the temp dir.
        temp_path = self.repo._path_temp()
        expected_path = self.root / self.repo._TEMP_PATH
        self.assertEqual(temp_path, expected_path)

        # Ask for a path to be converted.
        temp_path = self.repo._path_temp(path_in)
        expected_path = self.root / self.repo._TEMP_PATH / path_in
        self.assertEqual(temp_path, expected_path)

        # Ask for a temp path when you happen to already have one.
        path_in_temp = paths.cast(self.repo._TEMP_PATH) / path_in
        temp_path = self.repo._path_temp(path_in_temp)
        self.assertEqual(temp_path, expected_path)

        # ---
        # `test_save()` troubles check:
        # ---
        # Ask for temp paths that were giving us trouble in `test_save()`.

        # Was getting ".../<temp_dir>/<temp_dir>/..."
        path_in_temp = self.repo._path_temp(self.filename)
        no_inception_path = self.repo._path_temp(path_in_temp)
        # Already in temp, so shouldn't've been changed.
        self.assertEqual(path_in_temp, no_inception_path)

        # Was getting non-temp filepath when asking to save non-temp filepath
        # as temp.
        path_in_repo = self.path_file
        # Expect it to be redirected to temp.
        expected = self.root_temp / path_in_repo.relative_to(self.root)
        path_in_temp = self.repo._path_temp(path_in_repo)
        self.assertNotEqual(path_in_repo, path_in_temp)
        self.assertEqual(path_in_temp, expected)

        # ------------------------------
        # Success Cases: NO ROOT!
        # ------------------------------

        # Tree repo does have a root...
        # But we want to pretend it doesn't for some error cases.
        self.assertTrue(self.repo.root())
        self.assertEqual(self.repo.root(), self.root)
        self.repo._root = None

        # An absolute path that just so happens to have some directory named
        # the right thing? Ok...
        root_in = paths.cast("/somewhere/with/a", self.repo._TEMP_PATH, "dir")
        temp_path = self.repo._path_temp(root_in / path_in)
        self.assertEqual(temp_path, root_in / path_in)

        # ------------------------------
        # Error Cases: NO ROOT!
        # ------------------------------

        # Don't print all the log exceptions, please.
        with log.LoggingManager.disabled():
            with self.assertRaises((VerediError, LoadError, SaveError)):
                # No root, no input... yes exception.
                self.repo._path_temp()

            with self.assertRaises((VerediError, LoadError, SaveError)):
                # No root, not absolute - exception
                self.repo._path_temp(path_in)

            with self.assertRaises((VerediError, LoadError, SaveError)):
                # No root, absolute w/o temp-dir in it - exception
                root_in = paths.cast("/no/dir/which/shall/not/be/named")
                self.repo._path_temp(root_in / path_in)

    def test_set_up(self) -> None:
        # Test that FileTreeRepository does its `_ut_set_up()`.

        # We should /not/ be set up yet.
        self.assertFalse(self.root_temp)

        # Should fail set-up if it has no root...
        self.assertTrue(self.repo.root())
        self.assertEqual(self.repo.root(), self.root)
        self.repo._root = None

        with log.LoggingManager.disabled():
            with self.assertRaises(UnitTestError):
                self.repo._ut_set_up()

        # Revert root to what it was.
        self.repo._root = self.root

        # Now get all set-up and ready for... uh... doing set-up...?
        self._set_temp_paths()

        # We should (still) /not/ be set-up yet.
        self.assertTrue(self.root_temp)
        self.assertFalse(self.root_temp.exists())

        # ---
        # Do the thing, finally.
        # ---
        self.repo._ut_set_up()

        # Now our temp dir should exist.
        self.assertTrue(self.root_temp.exists())

        # ---
        # Do the clean-up.
        # ---
        # We don't test it here... but try to do it anyways.
        self._tear_down_repo()

    def test_tear_down(self) -> None:
        # Test that FileTreeRepository does its `_ut_tear_down()`.

        # Get all set up...
        self._set_up_repo()

        # Now our temp dir should exist.
        self.assertTrue(self.root_temp.exists())

        # ---
        # Do the tear-down
        # ---
        self.repo._ut_tear_down()

        # Make sure our temp dir is gone now.
        self.assertFalse(self.root_temp.exists())

        # Set up again!
        self._set_up_repo()
        self.assertTrue(self.root_temp.exists())

        # Add a temp file?
        self.assertTrue(self.path_file)
        self.assertTrue(self.path_file.exists())
        # This 'path_temp_file' is layers deep like 'path_file', so make sure
        # the layers exist.
        self.path_temp_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.path_file, self.path_temp_file)
        # Original and new exist.
        self.assertTrue(self.path_file)
        self.assertTrue(self.path_file.exists())
        self.assertTrue(self.path_temp_file)
        self.assertTrue(self.path_temp_file.exists())

        # Tear down again.
        self.repo._ut_tear_down()

        # Make sure tear-down deleted non-empty dir.
        self.assertFalse(self.root_temp.exists())

    def test_ensure(self) -> None:
        # Test that `_ensure` can create a needed parent.
        self._set_up_repo()

        # Shouldn't exist yet.
        self.assertFalse(self.path_temp.exists())

        # Now we'll ensure it exists... Ensure only ensures the path's parent,
        # so in this case it ensures `self.path_temp` exists, not
        # `self.path_temp_file`.
        self.repo._path_ensure(self.path_temp_file)
        # ...so the directory should exist now.
        self.assertTrue(self.path_temp.exists())

        self._tear_down_repo()

    def test_path_safed(self) -> None:
        # Test... that path can be safed?
        self._set_up_repo()

        # Does this safe a path? Very basic test...
        unsafe = 'user/name'
        expected = paths.cast('user_name')
        safe = self.repo._path_safed(unsafe)
        self.assertNotEqual(unsafe, safe)
        self.assertEqual(safe, expected)

        self._tear_down_repo()

    def _helper_test_path(self,
                          *unsafe:  str,
                          expected: str             = None,
                          context:  DataSaveContext = None,
                          ensure:   bool            = False,
                          glob:     bool            = False) -> paths.Path:
        '''
        Do the test for repo._path() in a subTest() based on input params.
        Returns safe'd path.
        '''
        with self.subTest(unsafe=unsafe,
                          expected=expected,
                          action=context.action,
                          ensure=ensure,
                          glob=glob):
            expected = paths.cast(expected)
            preexisting = expected.parent.exists()
            safe = None

            # ------------------------------
            # If it's a SAVE, then it should throw on glob=TRUE
            # ------------------------------
            # Does this safe a path?
            if glob and context.action == DataAction.SAVE:
                with log.LoggingManager.disabled():
                    with self.assertRaises(SaveError):
                        safe = self.repo._path(*unsafe,
                                               context=context,
                                               ensure=ensure,
                                               glob=glob)

            # ------------------------------
            # If it's a LOAD or non-glob SAVE, it should just be ok.
            # ------------------------------
            else:
                safe = self.repo._path(*unsafe,
                                       context=context,
                                       ensure=ensure,
                                       glob=glob)

                self.assertNotEqual(unsafe, safe)
                self.assertEqual(safe, expected)

                # Did it ensure the parent(s) exist if it was asked to?
                if ensure and context.action == DataAction.SAVE:
                    self.assertTrue(expected.parent.exists())
                    self.assertTrue(safe.parent.exists())
                    self.assertFalse(preexisting,
                                     "Cannot ensure parent's creation if "
                                     "parent already exists... "
                                     f"parent: {safe.parent}")

            return safe
        return None

    def test_path_save(self) -> None:
        # Test that `_path()` returns a safe path (globbed if needed, ensured
        # if needed).
        self._set_up_repo()

        # Make stuff happen in temp dir.
        context = self.context_save(self.TaxonCtx.GAME, temp=True)

        # ---
        # glob:   False
        # ensure: False
        # ---
        glob = False
        ensure = False
        unsafe = ('mi$c', 'user/name')
        expected = self.root_temp / 'mi_c' / 'user_name'
        self._helper_test_path(*unsafe,
                               expected=expected,
                               context=context,
                               ensure=ensure,
                               glob=glob)

        # ---
        # glob:   True
        # ensure: False
        # ---
        # Globbing a save action isn't allowed.
        glob = True
        ensure = False
        unsafe = ('mi$c', 'user/name')
        expected = 'ERROR! ERROR! ERROR!'
        self._helper_test_path(*unsafe,
                               expected=expected,
                               context=context,
                               ensure=ensure,
                               glob=glob)

        # ---
        # glob:   False
        # ensure: True
        # ---
        glob = False
        ensure = True
        unsafe = ('mi$c', 'user/name')
        expected = self.root_temp / 'mi_c' / 'user_name'
        self._helper_test_path(*unsafe,
                               expected=expected,
                               context=context,
                               ensure=ensure,
                               glob=glob)

        self._tear_down_repo()

    def test_path_load(self) -> None:
        # Test that `_path()` returns a safe path (globbed if needed, ensured
        # if needed).
        self._set_up_repo()

        context = self.context_load(self.TaxonCtx.GAME)

        # ---
        # glob:   False
        # ensure: False
        # ---
        glob = False
        ensure = False
        unsafe = ('mi$c', 'user/name')
        expected = self.root / 'mi_c' / 'user_name'
        self._helper_test_path(*unsafe,
                               expected=expected,
                               context=context,
                               ensure=ensure,
                               glob=glob)

        # ---
        # glob:   True
        # ensure: False
        # ---
        glob = True
        ensure = False
        unsafe = ('mi$c', 'user/name')
        expected = self.root / 'mi_c' / 'user_name.*'
        self._helper_test_path(*unsafe,
                               expected=expected,
                               context=context,
                               ensure=ensure,
                               glob=glob)

        # ---
        # glob:   False
        # ensure: True
        # ---
        # Ensure is just ignored on loads...
        glob = False
        ensure = True
        unsafe = ('mi$c', 'user/name')
        expected = self.root / 'mi_c' / 'user_name'
        self._helper_test_path(*unsafe,
                               expected=expected,
                               context=context,
                               ensure=ensure,
                               glob=glob)

        self._tear_down_repo()

    def _helper_data_stream(self,
                            stream:  TextIOBase,
                            min_len: int) -> str:
        '''
        Read a file's contents with pathlib/Python and verify against inputs.
        '''
        stream.seek(0)
        data = stream.read()
        self.assertTrue(data)
        self.assertIsInstance(data, str)
        self.assertGreater(len(data), min_len)
        return data

    def _helper_file_contents(self,
                              path:           paths.Path,
                              min_len:        int,
                              verify_against: str) -> None:
        '''
        Read a file's contents with pathlib/Python and verify against inputs.
        '''
        self.assertTrue(path)
        self.assertGreater(min_len, 0)
        self.assertTrue(verify_against)
        self.assertGreater(len(verify_against), min_len)

        with path.open('r') as file_stream:
            # ---
            # Do the checks of this stream.
            # ---
            self.assertTrue(file_stream)
            self.assertIsInstance(file_stream, TextIOBase)

            data = file_stream.read()
            self.assertTrue(data)
            self.assertIsInstance(data, str)
            self.assertGreater(len(data), min_len)

            # ---
            # Verify our repo read & returned the same data.
            # ---
            self.assertEqual(len(verify_against), len(data))
            self.assertEqual(verify_against, data)

    def do_load_test(self,
                     load: Optional['Test_FileTreeRepo.TaxonCtx'] = None,
                     min_len: int = 1024,
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
        self.assertTrue(repo_ctx['paths'])
        self.assertIsInstance(repo_ctx['paths'], list)
        self.assertEqual(len(repo_ctx['paths']), 1)
        # ....and make sure the path exists.
        path = paths.cast(repo_ctx['paths'][0])
        self.assertTrue(path)

        # There should be a good amount of data in that file... whatever it is.
        data = self._helper_data_stream(loaded_stream, min_len)

        # read file directly, assert contents are same.
        self._helper_file_contents(path, min_len, data)

    def test_load_player(self) -> None:
        self.do_load_test(self.TaxonCtx.PLAYER)

    def test_load_monster(self) -> None:
        self.do_load_test(self.TaxonCtx.MONSTER)

    def test_load_npc(self) -> None:
        self.do_load_test(self.TaxonCtx.NPC)

    def test_load_item(self) -> None:
        self.do_load_test(self.TaxonCtx.ITEM)

    def do_save_test(self,
                     save: Optional['Test_FileTreeRepo.TaxonCtx'] = None,
                     min_len: int = 1024,
                     ) -> None:
        # ------------------------------
        # Get data to save, first.
        # ------------------------------
        # `save` enum is also good for the load.
        load_context = self.context_load(save)

        # Ok; give to repo to load...
        loaded_stream = self.repo.load(load_context)
        self.assertIsNotNone(loaded_stream)
        self.assertTrue(loaded_stream)

        # There should be a good amount of data in that file...
        loaded_data = self._helper_data_stream(loaded_stream, min_len)

        # ------------------------------
        # Prepare for the save.
        # ------------------------------
        with log.LoggingManager.on_or_off(self.debugging):
            context = self.context_save(save, True)

        # Did we get something?
        self.assertTrue(context)
        self.assertIsInstance(context, DataSaveContext)

        self.assertTrue(context.taxon)
        self.assertIsInstance(context.taxon, Taxon)
        self.assertIsInstance(context.taxon, SavedTaxon)

        self.assertTrue(context.dotted())
        self.assertEqual(context.dotted(), self.dotted(__file__))

        self.assertTrue(context.action)
        self.assertIsInstance(context.action, DataAction)
        self.assertEqual(context.action, DataAction.SAVE)

        # Assuming all saving done in temp for unit test.
        self.assertTrue(context.temp)

        # Shouldn't have repo context yet - haven't given it to repo yet.
        repo_ctx = context.repo_data
        self.assertFalse(repo_ctx)

        # ------------------------------
        # Save data to root_temp.
        # ------------------------------

        # Ok; give to repo to save...
        saved = self.repo.save(loaded_stream, context)
        self.assertTrue(saved)

        # And now the repo context should be there.
        repo_ctx = context.repo_data
        self.assertTrue(repo_ctx)
        self.assertTrue(repo_ctx['meta'])
        self.assertTrue(repo_ctx['paths'])
        self.assertIsInstance(repo_ctx['paths'], list)
        self.assertEqual(len(repo_ctx['paths']), 1)
        # ....and make sure the path exists.
        path = paths.cast(repo_ctx['paths'][0])
        self.assertTrue(path)

        # ------------------------------
        # Verify against loaded data.
        # ------------------------------

        # Read our newly saved file directly, assert contents are same as what
        # we loaded.
        self._helper_file_contents(path, min_len, loaded_data)

    def test_save_player(self) -> None:
        self.do_save_test(self.TaxonCtx.PLAYER)

    def test_save_monster(self) -> None:
        self.do_save_test(self.TaxonCtx.MONSTER)

    def test_save_npc(self) -> None:
        self.do_save_test(self.TaxonCtx.NPC)

    def test_save_item(self) -> None:
        self.do_save_test(self.TaxonCtx.ITEM)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.data.repository.zest_file

if __name__ == '__main__':
    import unittest
    unittest.main()
