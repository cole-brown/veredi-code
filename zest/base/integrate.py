# coding: utf-8

'''
Base Class for Integration Tests.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union

from veredi.base         import paths
from veredi.base.strings import label
from veredi.zest.zpath   import TestType
from .ecs                import ZestEcs
from .engine             import ZestEngine


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Integrate ECS
# -----------------------------------------------------------------------------

class ZestIntegrateEcs(ZestEcs):
    '''
    Integration testing's base class with some setup and helpers. For when you
    need a lot, but not the engine; like: EcsManagers, events, data, and
    multiple Systems.
    '''

    def pre_set_up(self,
                   filename:  Union[str, paths.Path]  = None,
                   extra:     label.LabelLaxInputIter = (),
                   test_type: Optional[TestType]      = TestType.INTEGRATION
                   ) -> None:
        '''
        Use this!

        Called in `self.setUp()` after `self._define_vars()` and before
        anything happens.

        Use it to do any prep-work needed (like defining a different path for
        the config file).
        '''
        # Tests based off of this, ZestIntegrateEcs, are INTEGRATION tests...
        # So far. But I guess they can change test_type if they want.
        super().pre_set_up(filename=filename,
                           test_type=test_type)

    def set_up(self) -> None:
        super().set_up()
        self.set_up_input()
        self.set_up_output()
        # Not sure if tests want to do their own in tests or just do it here?
        # self.set_up_events(clear_self=True, clear_manager=True)


# -----------------------------------------------------------------------------
# Engine ECS
# -----------------------------------------------------------------------------

class ZestIntegrateEngine(ZestEngine):
    '''
    Integration testing's base class with some setup and helpers. For when you
    need a lot, but not the engine; like: EcsManagers, events, data, and
    multiple Systems.
    '''

    def pre_set_up(self,
                   filename:  Union[str, paths.Path]  = None,
                   extra:     label.LabelLaxInputIter = (),
                   test_type: Optional[TestType]      = TestType.INTEGRATION
                   ) -> None:
        '''
        Use this!

        Called in `self.setUp()` after `self._define_vars()` and before
        anything happens.

        Use it to do any prep-work needed (like defining a different path for
        the config file).
        '''
        # Tests based off of this, ZestIntegrateEcs, are INTEGRATION tests...
        # So far. But I guess they can change test_type if they want.
        super().pre_set_up(filename=filename,
                           test_type=test_type)

    def set_up(self) -> None:
        super().set_up()
        self.set_up_input()
        self.set_up_output()
        # Not sure if tests want to do their own in tests or just do it here?
        # self.set_up_events(clear_self=True, clear_manager=True)
