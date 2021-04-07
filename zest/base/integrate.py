# coding: utf-8

'''
Base Class for Integration Tests.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.zest.zpath import TestType
from .ecs              import ZestEcs
from .engine           import ZestEngine


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

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.INTEGRATION

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

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.INTEGRATION

    def set_up(self) -> None:
        super().set_up()
        self.set_up_input()
        self.set_up_output()
        # Not sure if tests want to do their own in tests or just do it here?
        # self.set_up_events(clear_self=True, clear_manager=True)
