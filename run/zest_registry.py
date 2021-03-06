# coding: utf-8

'''
Test our registry/registrar/registree finding functionality.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, Optional, Iterable
from types import ModuleType


from veredi.zest.base.unit import ZestBase
from veredi.zest.zpath     import TestType

from veredi.logs         import log
from veredi.base.context import UnitTestContext
from veredi.base.strings import label
from veredi.base         import paths
from veredi.data         import background


# ------------------------------
# What we're testing:
# ------------------------------
from . import registry
from veredi.base import const


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Base Class
# -----------------------------------------------------------------------------

class ZestFindRegistees(ZestBase):
    '''
    Test the veredi.run.registry's finding/initializing registrees.
    '''

    # -------------------------------------------------------------------------
    # Set-Up
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Defines any instance variables with type hinting, docstrs.
        Happens ASAP during unittest.setUp().
        '''
        # ------------------------------
        # Parent!
        # ------------------------------
        super()._define_vars()

        self.path_test_root: paths.Path = None
        '''
        Path to the root directory that we've set up with a faked out directory
        structure to walk/ignore for finding registration files.
        '''

    def set_up(self) -> None:
        '''
        Set up our logging to be unit-testable.
        '''
        # TestType enum values are paths to their base testing data directory
        self.path_test_root = (self._TEST_TYPE.value
                               / 'run'
                               / '_find_modules'
                               / 'veredi')

    # -------------------------------------------------------------------------
    # Tear-Down
    # -------------------------------------------------------------------------

    def tear_down(self) -> None:
        '''
        Do any of our own clean-up.
        '''
        self.path_test_root = None

    # -------------------------------------------------------------------------
    # Test Helpers
    # -------------------------------------------------------------------------

    def find_registree_modules(self, root: paths.Path) -> Iterable[ModuleType]:
        '''
        Find registree modules using `run._find_modules`.

        Use `const.LIB_VEREDI_ROOT` if you want the actual modules.
        '''
        # modules = registry._find_modules(const.LIB_VEREDI_ROOT)
        modules = registry._find_modules(root)
        return modules

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_find_registree_modules(self) -> None:
        # self.debugging = True
        modules = []
        with log.LoggingManager.on_or_off(self.debugging):
            modules = self.find_registree_modules(self.path_test_root)

        expected = ['veredi.__register__', 'veredi.valid.__register__']
        for module in modules:
            self.assertIn(module, expected)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi run logs/log/zest_log.py

if __name__ == '__main__':
    import unittest
    # log.set_level(const.Level.DEBUG)
    unittest.main()
