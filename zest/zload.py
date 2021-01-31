# coding: utf-8

'''
Helper for unit test data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Type, Tuple, Iterable, List)
if TYPE_CHECKING:
    from veredi.run.system             import SysCreateType


from veredi.logger                     import log
from .                                 import zmake, zontext
from .zpath                            import TestType
from .exceptions                       import UnitTestError

from veredi                            import run


from veredi.data                       import background
from veredi.debug.const                import DebugFlag

# Config Stuff
from veredi.data.config.config         import Configuration

# Meeting Stuff
from veredi.game.ecs.base.system       import System
from veredi.game.ecs.time              import TimeManager
from veredi.game.ecs.event             import EventManager
from veredi.game.ecs.component         import ComponentManager
from veredi.game.ecs.entity            import EntityManager
from veredi.game.ecs.system            import SystemManager
from veredi.game.ecs.meeting           import Meeting
from veredi.game.data.manager          import DataManager
from veredi.game.data.identity.manager import IdentityManager
from veredi.base.context               import VerediContext
from veredi.game.ecs.base.identity     import SystemId
from veredi.game.engine                import Engine

# Registry
from veredi.data.config                import registry as config_registry
from veredi.data.serdes.yaml           import registry as yaml_registry
from veredi.data.codec.encodable       import EncodableRegistry

# Registration
import veredi.math.d20.parser
# import veredi.data.repository.file
# import veredi.data.serdes.yaml.serdes
# import veredi.data.serdes.json.serdes


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Helpers for Systems.
# -----------------------------------------------------------------------------

def add_system(system: System) -> SystemId:
    '''
    Helper to add an already created system (e.g. one with a complex set-up).
    Returns the SystemId assigned to the system.

    e.g.:
      add_system(someSystemInstance)
    '''
    sid = run.system.add(system)
    return sid


def create_system(config:      Optional[Configuration],
                  context:     VerediContext,
                  sys_type:    Type[System],
                  debug_flags: Optional[DebugFlag] = None) -> SystemId:
    '''
    Helper to create a system.
    Returns the SystemId assigned to the system.

    e.g.:
      create_system(self._manager.system, self.context, SomeSystem)
      create_system(self._manager.system, special_context, SomeSystem)
    '''
    sid = run.system.create(config, context, sys_type,
                            debug_flags=debug_flags)
    return sid


def create_systems(config:      Optional[Configuration],
                   context:     VerediContext,
                   *args:       'SysCreateType',
                   debug_flags: Optional[DebugFlag] = None) -> List[SystemId]:
    '''
    Helper to create systems. Takes in either: system types, system instances,
    tuples of (type/instance, create-context). Returns a list of SystemIds
    created. If tuple, will use tuple's context for creation, else uses the
    `context` arg.

    e.g.:
      create_systems(config, self.context, SomeSystem)
      create_systems(config, self.context,
                     (SomeSystem, different_context)) # ignores self.context
      create_systems(None, self.context,
                     (SomeSystem, context_for_SomeSystem),
                     TwoSystem) # TwoSystem uses self.context
    '''
    sids = run.system.many(config, context,
                           *args,
                           debug_flags=debug_flags)
    return sids


# -----------------------------------------------------------------------------
# ECS / Engine: Set-up / Tear-Down
# -----------------------------------------------------------------------------

def set_up_ecs(test_name_class:   str,
               test_name_func:    str,
               enable_debug_logs: bool,
               # Optional Debug Stuff:
               test_type:         TestType                   = TestType.UNIT,
               debug_flags:       Optional[DebugFlag]        = None,
               # Optional ECS:
               require_engine:    Optional[bool]             = False,
               desired_systems:   Iterable['SysCreateType']  = None,
               # Optional to pass in - else we'll make:
               configuration:     Optional[Configuration]    = None,
               time_manager:      Optional[TimeManager]      = None,
               event_manager:     Optional[EventManager]     = None,
               component_manager: Optional[ComponentManager] = None,
               entity_manager:    Optional[EntityManager]    = None,
               system_manager:    Optional[SystemManager]    = None,
               data_manager:      Optional[DataManager]      = None,
               identity_manager:  Optional[IdentityManager]  = None,
               # Optional to pass in - else we'll make  if asked:
               engine:            Optional[Engine]           = None,
               ) -> Tuple[Meeting, Engine, VerediContext, List[SystemId]]:
    '''
    Creates config, managers, if not supplied (via zmake.meeting).
    Creates a managers' meeting (via zmake.meeting).
    Creates a real context (via zontext.real_contfig).
    Creates supplied Systems (using our zload.create_systems).
      - If none supplied, creates default of: (nothing)
        - These are (currently) the min required to get from disk to component.

    Returns:
      Tuple[Meeting, VerediContext, SystemManager, List[SystemId]]
    '''
    with log.LoggingManager.on_or_off(enable_debug_logs):
        # ---
        # Configuration
        # ---
        if not configuration:
            log.debug("zload.set_up_ecs creating Configuration...")
            configuration = configuration or zmake.config(test_type)

        # ---
        # ECS Managers
        # ---
        log.debug("zload.set_up_ecs creating Meeting...")
        meeting = run.managers(configuration,
                               time_manager=time_manager,
                               event_manager=event_manager,
                               component_manager=component_manager,
                               entity_manager=entity_manager,
                               system_manager=system_manager,
                               data_manager=data_manager,
                               identity_manager=identity_manager,
                               debug_flags=debug_flags)

        log.debug("zload.set_up_ecs running Meeting's Unit-Test Set-Up...")
        meeting._ut_set_up()

        # ---
        # Engine
        # ---
        engine = None
        if require_engine:
            log.debug("zload.set_up_ecs creating Engine...")
            engine = run.engine(configuration,
                                meeting,
                                debug_flags=debug_flags)

            log.debug("zload.set_up_ecs running Engine's Unit-Test Set-Up...")
            engine._ut_set_up()
        else:
            log.debug("zload.set_up_ecs SKIPPING Engine "
                      "creation (engine not requested).")
            log.debug("zload.set_up_ecs SKIPPING Engine's Unit-Test "
                      "Set-Up (engine not requested).")


        # ---
        # Config Context
        # ---
        log.debug("zload.set_up_ecs creating Context...")
        context = zontext.real_config(test_name_class,
                                      test_name_func,
                                      config=configuration)

        # ---
        # Additional Systems?
        # ---
        log.debug("zload.set_up_ecs creating systems...")
        system_manager = meeting.system
        sids = []
        if desired_systems:
            sids = run.system.many(system_manager, context,
                                   *desired_systems)
        elif not require_engine:
            sids = run.system.many(system_manager, context)
            # If you have required systems, see `run.system.many` docstr for
            # details but:
            # sids = run.system.many(system_manager, context,
            #                        OneSys, TwoSys, RedSys, BlueSys)
        # Else: our engine creates the requried stuff and we don't want to
        # double-create.

        log.debug("zload.set_up_ecs done.")
        return meeting, engine, context, sids


def tear_down_ecs(test_name_class:   str,
                  test_name_func:    str,
                  enable_debug_logs: bool,
                  meeting:           Meeting,
                  engine:            Optional[Engine] = None) -> None:
    '''
    Runs Tear-Down functions for each manager in meeting.

    Runs Tear-Down for engine if supplied.
    '''
    with log.LoggingManager.on_or_off(enable_debug_logs):
        log.debug("zload.tear_down_ecs running Meeting's "
                  "Unit-Test Tear-Down...")
        meeting._ut_tear_down()

        if engine:
            log.debug("zload.tear_down_ecs running Engine's "
                      "Unit-Test Tear-Down...")
            engine._ut_tear_down()
        else:
            log.debug("zload.tear_down_ecs SKIPPING Engine's "
                      "Unit-Test Tear-Down (engine does not exist)...")

        log.debug("zload.tear_down_ecs done.")


# -----------------------------------------------------------------------------
# Background: Set-up / Tear-Down
# -----------------------------------------------------------------------------

def set_up_background() -> None:
    '''
    Get the background cleared out and ready for a new test.
    '''
    # Technically should only do this in tear-down. See if it's too much of a
    # pain or too many mess-ups to just do it there.
    # background.testing.nuke()

    # Enable our unit-testing flag.
    background.testing.set_unit_testing(True)


def tear_down_background() -> None:
    '''
    Get the background cleared out and ready for a new test.
    '''
    # Delete entire background, since it's all created during set-up/testing.
    background.testing.nuke()


# -----------------------------------------------------------------------------
# Registries: Set-up / Tear-Down
# -----------------------------------------------------------------------------

# TODO [2020-11-12]: Figure out how to register Encodables for every test?
# If not, remove these functions and the things that call them.

def set_up_registries(encodables: bool = True,
                      **kwargs:   bool) -> None:
    '''
    Get the registries ready for a new test.
    '''
    # ------------------------------
    # Ensure Things Are Not Registered.
    # ------------------------------
    config_registry._ut_unregister()
    yaml_registry._ut_unregister()

    # log.ultra_mega_debug("Nuking EncodableRegistry. Was: "
    #                      f"\n{EncodableRegistry._get()}")
    # EncodableRegistry.nuke()
    #
    # # ------------------------------
    # # Register Things.
    # # ------------------------------
    # if encodables:
    #     log.ultra_mega_debug("Providing Encodables...")
    #     import veredi.data.codec.provide
    #     log.ultra_mega_debug("Done. EncodableRegistry is: "
    #                          f"\n{EncodableRegistry._get()}")

    # ------------------------------
    # Check for unknown inputs...
    # ------------------------------
    for reg_name in kwargs:
        msg = (f"Unhandled registry setup for '{reg_name}'. Don't know "
               "how to set it up.")
        error = UnitTestError(reg_name, msg)
        raise log.exception(error, msg)


def tear_down_registries() -> None:
    '''
    Get the registries cleared out and ready for a new test.
    '''
    config_registry._ut_unregister()
    yaml_registry._ut_unregister()

    # # Currently nothing really to do that set_up_registries() doesn't do.
    # # But I want to clear out the registries for the pairing.
    # EncodableRegistry.nuke()
