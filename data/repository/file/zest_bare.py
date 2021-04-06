# coding: utf-8

'''
Tests for the FileBareRepository.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from io import TextIOBase
import shutil

from veredi.zest                import zpath
from veredi.zest.base.unit      import ZestBase


from veredi.logs                import log
from veredi.data                import background
from veredi.base                import paths

from veredi.base.exceptions     import VerediError
from veredi.data.exceptions     import LoadError, SaveError
from veredi.zest.exceptions     import UnitTestError

from veredi.data.config.context import ConfigContext
from veredi.data.context        import (DataAction,
                                        DataBareContext)

from .bare                      import FileBareRepository


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_FileBareRepo(ZestBase):

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Set-Up
    # -------------------------------------------------------------------------

    def set_up(self) -> None:
        # ---
        # Paths
        # ---
        # Note: 'config.test-bare.yaml' isn't in the usual
        # config-file-for-tests spot (zpath.config()). It's in
        # zpath.repository_file_bare().
        self.root = zpath.repository_file_bare()
        self.filename = 'config.test-bare.yaml'
        self.path_file = self.root / self.filename
        self.path_temp = None
        self.path_temp_file = None

        # ---
        # Create Repo.
        # ---
        context = ConfigContext(self.root,
                                self.dotted,
                                id=zpath.config_id(self.type, None))
        ConfigContext.set_testing(context, True)
        context.ut_inject(testing_target="FileBareRepository")
        self.repo = FileBareRepository(context)

    # -------------------------------------------------------------------------
    # Tear-Down
    # -------------------------------------------------------------------------

    def tear_down(self) -> None:
        # ---
        # Delete temp dir if needed.
        # ---
        if not self.root:
            self.root = zpath.repository_file_bare()
        if not self.repo.root():
            self.repo._root = self.root
        if not self.path_temp:
            self.path_temp = self.repo._path_temp()
        if self.root.exists() and self.path_temp.exists():
            self._tear_down_repo()

        # ---
        # Clear out our vars...
        # ---
        self.root           = None
        self.filename       = None
        self.path_file      = None
        self.path_temp      = None
        self.path_temp_file = None
        self.repo           = None

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _set_temp_paths(self):
        # We need a root.
        self.assertTrue(self.repo.root())

        # Set test's `path_temp` and make sure it doesn't exist yet.
        self.path_temp = self.repo._path_temp()
        self.assertTrue(self.path_temp)
        self.assertFalse(self.path_temp.exists(),
                         f"Delete temp repo dir please: {self.path_temp}")

        # Set test's `path_temp_file`. Can't exist yet.
        self.path_temp_file = self.repo._path_temp(self.filename)
        expected = self.path_temp / self.filename
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
        self.assertTrue(self.path_temp.exists())

    def _tear_down_repo(self):
        '''
        Call our tear-down helpers:
          - repo._ut_tear_down()
        '''
        self.repo._ut_tear_down()

        # Now our temp dir should not exist.
        if self.path_temp.exists():
            self.fail(f"temp exists... root is: {self.repo.root()}")
        self.assertFalse(self.path_temp.exists())

    def _meta(self, func):
        '''
        Get some metadata for DataBareContext.
        '''
        return {
            'dotted': self.dotted,
            'test-suite': self.__class__.__name__,
            'unit-test': func,
        }

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_init(self) -> None:
        self.assertTrue(self.root)
        self.assertIsInstance(self.root, paths.Path)

        self.assertTrue(self.filename)
        self.assertIsInstance(self.filename, str)

        self.assertTrue(self.path_file)
        self.assertIsInstance(self.path_file, paths.Path)
        self.assertTrue(self.path_file.parent.exists())
        self.assertTrue(self.path_file.parent.is_dir())
        self.assertTrue(self.path_file.exists())
        self.assertTrue(self.path_file.is_file())

        self.assertTrue(self.repo)
        # Bare repo does have a root to start with now, and it should be our
        # root.
        self.assertTrue(self.repo.root())
        self.assertEqual(self.repo.root(), self.root)

    def test_glob(self) -> None:
        # These should be the same result just different inputs.
        globbed_full = self.repo._ext_glob(self.path_file)

        self.assertNotEqual(globbed_full, self.path_file)
        self.assertNotEqual(globbed_full.suffix, self.path_file.suffix)
        self.assertEqual(globbed_full.suffix, '.*')
        self.assertEqual(globbed_full.stem, self.path_file.stem)

    def test_path_temp(self) -> None:
        # Test out our FileBareRepository._path_temp() function that we'll be
        # using in test_save().
        self.assertTrue(self.repo)

        # Don't care about this file name... Anything will do.
        path_in = "jeff.file-does-not-exist.txt"

        # Bare repo does have a root to start with now, and it should be our
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
        expected = path_in_repo.parent / self.repo._TEMP_PATH / self.filename
        path_in_temp = self.repo._path_temp(path_in_repo)
        self.assertNotEqual(path_in_repo, path_in_temp)
        self.assertEqual(path_in_temp, expected)
        # /srv/veredi/veredi/zest/zata/unit/repository/file-bare/config.test-bare.yaml

        # ------------------------------
        # Success Cases: NO ROOT!
        # ------------------------------

        # Bare repo does have a root...
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
        # Test that FileBareRepository does its `_ut_set_up()`.

        # We should /not/ be set up yet.
        self.assertFalse(self.path_temp)

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
        self.assertTrue(self.path_temp)
        self.assertFalse(self.path_temp.exists())

        # ---
        # Do the thing, finally.
        # ---
        self.repo._ut_set_up()

        # Now our temp dir should exist.
        self.assertTrue(self.path_temp.exists())

        # ---
        # Do the clean-up.
        # ---
        # We don't test it here... but try to do it anyways.
        self._tear_down_repo()

    def test_tear_down(self) -> None:
        # Test that FileBareRepository does its `_ut_tear_down()`.

        # Get all set up...
        self._set_up_repo()

        # Now our temp dir should exist.
        self.assertTrue(self.path_temp.exists())

        # ---
        # Do the tear-down
        # ---
        self.repo._ut_tear_down()

        # Make sure our temp dir is gone now.
        self.assertFalse(self.path_temp.exists())

        # Set up again!
        self._set_up_repo()

        # Add a temp file?
        self.assertTrue(self.path_file)
        self.assertTrue(self.path_file.exists())
        shutil.copyfile(self.path_file, self.path_temp_file)
        # Original and new exist.
        self.assertTrue(self.path_file)
        self.assertTrue(self.path_file.exists())
        self.assertTrue(self.path_temp_file)
        self.assertTrue(self.path_temp_file.exists())

        # Tear down again.
        self.repo._ut_tear_down()

        # Make sure tear-down deleted non-empty dir.
        self.assertFalse(self.path_temp.exists())

    def test_ensure(self) -> None:
        # Test that `_ensure` can create a needed parent.
        self._set_up_repo()

        # Shouldn't exist yet.
        dirpath = self.path_temp / 'ensure.this.tmp'
        filepath = dirpath / 'somefile.txt'
        self.assertFalse(dirpath.exists())

        # Only needed for logging:
        context = DataBareContext(self.dotted,
                                  ConfigContext.KEY,
                                  "not-used-this-test",
                                  DataAction.SAVE,
                                  self._meta('test_path_save'),
                                  # Make stuff happen in temp dir.
                                  temp=True)

        # Now we'll ensure it exists... Ensure only ensures the path's parent,
        # so in this case it ensures `dirpath` exists, not `filepath`.
        self.repo._path_ensure(filepath, context)
        # ...so the directory should exist now.
        self.assertTrue(dirpath.exists())

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
                          context:  DataBareContext = None,
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
                if ensure:
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

        action = DataAction.SAVE
        context = DataBareContext(self.dotted,
                                  ConfigContext.KEY,
                                  "not-used-this-test",
                                  action,
                                  self._meta('test_path_save'),
                                  # Make stuff happen in temp dir.
                                  temp=True)

        # ---
        # glob:   False
        # ensure: False
        # ---
        glob = False
        ensure = False
        unsafe = ('mi$c', 'user/name')
        expected = self.path_temp / 'mi_c' / 'user_name'
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
        expected = self.path_temp / 'mi_c' / 'user_name'
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

        action = DataAction.SAVE
        context = DataBareContext(self.dotted,
                                  ConfigContext.KEY,
                                  "not-used-this-test",
                                  action,
                                  self._meta('test_path_load'),
                                  # Make stuff happen in temp dir.
                                  temp=True)

        # ---
        # glob:   False
        # ensure: False
        # ---
        glob = False
        ensure = False
        unsafe = ('mi$c', 'user/name')
        expected = self.path_temp / 'mi_c' / 'user_name'
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
        expected = self.path_temp / 'mi_c' / 'user_name.*'
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
        expected = self.path_temp / 'mi_c' / 'user_name'
        self._helper_test_path(*unsafe,
                               expected=expected,
                               context=context,
                               ensure=ensure,
                               glob=glob)

        self._tear_down_repo()

    def _helper_test_context_data(self, context: DataBareContext) -> None:
        with self.subTest(action=context.action, context=context):
            # ------------------------------
            # Fill up the context.
            # ------------------------------
            filled = self.repo._context_data(context, self.path_file)

            # We should get the same object back.
            self.assertEqual(id(context), id(filled))

            # And it should have some stuff added to it.
            key = str(background.Name.REPO)
            path_key = background.Name.PATH.key
            self.assertIsInstance(filled[key], dict)
            self.assertIsInstance(filled[key]['meta'], dict)

            # ---
            # BaseRepository
            # ---
            self.assertEqual(filled[key]['meta']['dotted'], self.repo.dotted)
            self.assertEqual(filled[key]['meta']['type'], self.repo.name)

            # ---
            # FileRepository
            # ---
            self.assertEqual(filled[key]['meta'][path_key]['root'],
                             self.root)
            self.assertEqual(filled[key]['meta'][path_key]['temp'],
                             self.path_temp)
            self.assertEqual(filled[key]['meta']['path-safing'],
                             'veredi.paths.sanitize.human')

            # ---
            # FileBareRepository
            # ---
            self.assertEqual(filled[key]['action'], context.action)
            self.assertEqual(filled[key]['path'], str(self.path_file))

            self._tear_down_repo()

    def test_context_data(self) -> None:
        self._set_up_repo()

        # Test for LOAD.
        load_context = DataBareContext(self.dotted,
                                       ConfigContext.KEY,
                                       self.path_file,
                                       DataAction.LOAD,
                                       self._meta('test_context_data'))
        self._helper_test_context_data(load_context)

        # Test for SAVE.
        save_context = DataBareContext(self.dotted,
                                       ConfigContext.KEY,
                                       self.path_file,
                                       DataAction.SAVE,
                                       self._meta('test_context_data'))
        self._helper_test_context_data(save_context)

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

    def test_load(self) -> None:
        # Use repository to load a file, then check against directly read file
        # contents.
        self._set_up_repo()
        ctx = DataBareContext(self.dotted,
                              ConfigContext.KEY,
                              self.path_file,
                              DataAction.LOAD,
                              self._meta('test_load'))
        # Read using our repository.
        with self.repo.load(ctx) as repo_stream:
            # ---
            # Do some checks of the stream loaded.
            # ---
            self.assertTrue(repo_stream)
            self.assertIsInstance(repo_stream, TextIOBase)

            # There should be a good amount of data in that file.
            # As of [2021-02-02], it's ~1.5 kB in size, so:
            min_len = 1024
            data = self._helper_data_stream(repo_stream, min_len)

            # And again using python to get something to check.
            self._helper_file_contents(self.path_file, min_len, data)

        self._tear_down_repo()

    def test_save(self) -> None:
        # log.set_group_level(log.Group.DATA_PROCESSING, log.Level.INFO)

        # Use repository to load a file, save it to the temp unit-testing
        # place, then check original vs saved.
        self._set_up_repo()

        load_ctx = DataBareContext(self.dotted,
                                   ConfigContext.KEY,
                                   self.path_file,
                                   DataAction.LOAD,
                                   self._meta('test_load'))

        # ------------------------------
        # Read initial data.
        # ------------------------------
        with self.repo.load(load_ctx) as repo_stream:
            # ---
            # Do some checks of the stream loaded.
            # ---
            self.assertTrue(repo_stream)
            self.assertIsInstance(repo_stream, TextIOBase)

            # There should be a good amount of data in that file.
            # As of [2021-02-02], it's ~1.5 kB in size, so:
            min_len = 1024
            data = self._helper_data_stream(repo_stream, min_len)

            # ------------------------------
            # Save data to temp.
            # ------------------------------
            save_ctx = DataBareContext(self.dotted,
                                       ConfigContext.KEY,
                                       # Don't add temp dir ourself.
                                       self.path_file,
                                       DataAction.SAVE,
                                       self._meta('test_save'),
                                       temp=True)
            # DO NOT SEEK BACK TO 0!!!
            # LET IT MAKE SURE TO DO THAT ITSELF!!!
            success = self.repo.save(repo_stream, save_ctx)
            self.assertTrue(success)

            # ------------------------------
            # Read the saved file to see how we did.
            # ------------------------------
            self._helper_file_contents(self.path_temp_file, min_len, data)

        self._tear_down_repo()


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi run data/repository/file/zest_bare.py

if __name__ == '__main__':
    import unittest
    unittest.main()
