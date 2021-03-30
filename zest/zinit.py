#!/usr/bin/env python3
# coding: utf-8

'''
Set-up veredi once-offs for a unittest.run().
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Type, Any, Iterable, List)
if TYPE_CHECKING:
    from veredi.data.config.config import Configuration


import unittest


from veredi.logs               import log

from veredi                    import run
from veredi.data               import background

# from veredi.data.registration import codec, config
from veredi.data.serdes.yaml   import registry as registry_yaml


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_SENTINEL_INIT: bool = False
'''
All these that should only be run once should be behind this sentinel.
'''


# -----------------------------------------------------------------------------
# Entry Functions
# -----------------------------------------------------------------------------

# TODO: v://future/unit-testing/2021-03-25T11:39:54-0800
# Problem with this:
# Unit-Test wants to create its Configuration based on what it wants/needs to
# test... And we need the config for setting up the registries, so... it's hard
# to do set-up before we have their config.
#
#
# We would need... a TestSuite or something? Gather up all tests that use the
# same config? IDK? Can't do this, exactly, anyways.
# def main(configuration:  'Configuration',
#          ut_module:      str = '__main__',
#          ut_defaultTest: Optional[Union[str, Iterable[str]]] = None,
#          ut_argv:        Optional[List[str]]                 = None,
#          ut_testRunner:  Union[Type[unittest.TextTestRunner],
#                                unittest.TextTestRunner]      = None,
#          ut_testLoader:  unittest.TestLoader      = unittest.defaultTestLoader,
#          ut_exit:        bool                                = True,
#          ut_verbosity:   int                                 = 1,
#          ut_failfast:    Optional[bool]                      = None,
#          ut_catchbreak:  Optional[bool]                      = None,
#          ut_buffer:      Optional[bool]                      = None,
#          ut_warnings:    Optional[str]                       = None) -> None:
#     '''
#     Call to start tests.
#
#     Runs once-per-entire-test-run stuff, then passes all `ut_*` args to
#     `unittest.main()`.
#     '''
#     set_up(configuration)
#
#     unittest.main(module=ut_module,
#                   defaultTest=ut_defaultTest,
#                   argv=ut_argv,
#                   testRunner=ut_testRunner,
#                   testLoader=ut_testLoader,
#                   exit=ut_exit,
#                   verbosity=ut_verbosity,
#                   failfast=ut_failfast,
#                   catchbreak=ut_catchbreak,
#                   buffer=ut_buffer,
#                   warnings=ut_warnings)


# -----------------------------------------------------------------------------
# Registries: Set-up / Tear-Down
# -----------------------------------------------------------------------------
# e.g. run.registration
# ------------------------------

def set_up_registries(config: Optional['Configuration']) -> None:
    '''
    Get the registries ready for all tests.
    '''
    # TODO: MOVE THESE BEHIND SENTINEL ONCE THEY HAVE BEEN UPDATED TO NEW
    # REGISTRATION.
    # ------------------------------
    # Ensure Things Are Not Registered.
    # ------------------------------
    registry_yaml._ut_unregister()

    # ------------------------------
    # Run our auto-registration.
    # ------------------------------
    global _SENTINEL_INIT
    if _SENTINEL_INIT:
        # Already ran - skip.
        return
    else:
        _SENTINEL_INIT = True

    # ------------------------------
    # Run our auto-registration.
    # ------------------------------
    run.registration(config)


# TODO: delete this.
def tear_down_registries() -> None:
    '''
    Get the registries cleared out and ready for a new test.
    '''
    # TODO: unit test log group?
    registry_yaml._ut_unregister()

    # Unregistering this way doesn't get things re-registered by the next
    # run.registration()... Probably because the imports do nothing since we
    # don't un-import?
    # So for now just leave it alone?
    #
    # # TODO: A more automatic unregister?
    # # run._ut_unregister()
    # reg_codec = registry_codec.registry()
    # if reg_codec:
    #     reg_codec._ut_unregister()


# -----------------------------------------------------------------------------
# Background: Set-up / Tear-Down
# -----------------------------------------------------------------------------

def set_up_background() -> None:
    '''
    Get the background cleared out and ready for a new test.
    '''
    # TODO: Figure out how to not nuke entire bg. Registrars lose their info?

    # Enable our unit-testing flag.
    background.testing.set_unit_testing(True)


def tear_down_background() -> None:
    '''
    Get the background cleared out and ready for a new test.
    '''
    # TODO: Figure out how to not nuke entire bg. Registrars lose their info?

    # Delete entire background, since it's all created during set-up/testing.
    background.testing.nuke()
