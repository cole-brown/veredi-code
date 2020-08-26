# coding: utf-8

'''
Base class for testing an ECS System.
  - Helpful functions.
  - Set-up / Tear-down for System Stuff.
  - Derives from ZestEcs.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from .ecs                        import ZestEcs

from veredi.game.ecs.base.system import System


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Base Class for Testing Systems
# -----------------------------------------------------------------------------

class ZestSystem(ZestEcs):
    '''
    Base testing class for testing an ECS System.

    Helpers for events, commands, etc.
    '''

    # -------------------------------------------------------------------------
    # Set-Up
    # -------------------------------------------------------------------------

    def set_up(self) -> None:
        '''
        Override this!

        super().set_up()
        <your test stuff>
        self.init_managers(...)
        self.init_system(...)
        '''
        super().set_up()

        # ---
        # Set-Up subclasses might want to do:
        # ---
        #
        # self.set_up_input()
        #   - Create an InputSystem for self.input_system.
        #   - Subscribes self._eventsub_cmd_reg to CommandRegistrationBroadcast
        #
        # self.set_up_output()
        #   - Create an OutputSystem for self.output_system.
        #
        # self.set_up_events()
        #   - Subscribes to test's desired events, tells ECS to subscribe.

    def _define_vars(self) -> None:
        '''
        Defines ZestSystem's instance variables with type hinting, docstrs.
        '''
        super()._define_vars()

        self.system:         System                       = None
        '''
        The system being tested.
        '''

    # -------------------------------------------------------------------------
    # System Creation Helpers
    # -------------------------------------------------------------------------

    # PREVIOUSLY init_system_self !!!
    def init_self_system(self, sys_type: System) -> System:
        '''
        Initializes, returns your test's system.
        '''
        self.system = self.init_one_system(sys_type)
        return self.system

    # -------------------------------------------------------------------------
    # Tear-Down
    # -------------------------------------------------------------------------

    def tear_down(self) -> None:
        '''
        Override this!

        <your stuff here>
        super().tear_down()
        '''

        self.system = None
        super().tear_down()
