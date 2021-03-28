# coding: utf-8

'''
Profile our registration functionality.
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

# Profile the actual codebase's registration.
from veredi.base.const import LIB_VEREDI_ROOT


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Base Class
# -----------------------------------------------------------------------------

class ZestFindRegistrations(ZestBase):
    '''
    Test the veredi.run.registry's finding/initializing registrations.
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
        self.path_test_root = LIB_VEREDI_ROOT

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

    def find_registration_modules(self,
                                  root: paths.Path) -> Iterable[ModuleType]:
        '''
        Find registration modules using `run._find_modules`.
          - Both registrees and registrars.

        Use `const.LIB_VEREDI_ROOT` if you want the actual modules.
        '''
        # modules = registry._find_modules(const.LIB_VEREDI_ROOT)
        modules = registry._find_modules(root)
        return modules

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_find_registration_modules(self) -> None:
        # self.debugging = True
        found_registrars = []
        found_registrees = []
        unknown = []
        with log.LoggingManager.on_or_off(self.debugging):
            found = self.find_registration_modules(self.path_test_root)
            found_registrars, found_registrees, unknown = found

        # ------------------------------
        # Expected Sub-Set
        # ------------------------------
        # Just check for a few expected registree and registrar module names.
        expected_registrees = [
            'veredi.data.codec.__register__',
            'veredi.math.d20.__register__'
        ]
        expected_registrars = [
            'veredi.data.codec.__registrar__',
        ]

        # ------------------------------
        # Expect only the Known...
        # ------------------------------
        self.assertFalse(unknown)

        # ------------------------------
        # Check registrars.
        # ------------------------------
        self.assertTrue(found_registrars)
        for module in expected_registrars:
            self.assertIn(module, found_registrars)

        # ------------------------------
        # Check registrars.
        # ------------------------------
        self.assertTrue(found_registrees)
        for module in expected_registrees:
            self.assertIn(module, found_registrees)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi run run/zprofile_registry.py

if __name__ == '__main__':
    import unittest
    import cProfile
    cProfile.run('unittest.main()',
                 # filename='whatever'
                 sort='time')
