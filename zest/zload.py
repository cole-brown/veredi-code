# coding: utf-8

'''
Helper for unit test data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, Optional, Type, NewType, Tuple, Iterable, List

from veredi.logger                      import log
from .                                  import zmake, zontext
from .zpath                             import TestType

from veredi.data                        import background
from veredi.debug.const                 import DebugFlag

# Config Stuff
from veredi.data.config.config          import Configuration

# Meeting Stuff
from veredi.game.ecs.base.system        import System
from veredi.game.ecs.time               import TimeManager
from veredi.game.ecs.event              import EventManager
from veredi.game.ecs.component          import ComponentManager
from veredi.game.ecs.entity             import EntityManager
from veredi.game.ecs.system             import SystemManager
from veredi.game.ecs.meeting            import Meeting
from veredi.base.context                import VerediContext
from veredi.game.ecs.base.identity      import SystemId
from veredi.game.engine                 import Engine

# System Stuff
from veredi.game.data.system            import DataSystem

# Registry
from veredi.data.config                 import registry as config_registry
from veredi.data.serdes.yaml            import registry as yaml_registry
from veredi.data.codec.encodable import EncodableRegistry

# Registration
import veredi.math.d20.parser
# import veredi.data.repository.file
# import veredi.data.serdes.yaml.serdes
# import veredi.data.serdes.json.serdes


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

SysCreateType = NewType('SysCreateType',
                        Union[Type[System],
                              Tuple[Type[System], VerediContext]])


# -----------------------------------------------------------------------------
# Helpers for loader()
# -----------------------------------------------------------------------------

def create_system(system_manager: SystemManager,
                  context: VerediContext,
                  sys_type: Type[System],
                  debug_flags: Optional[DebugFlag] = None) -> SystemId:
    '''
    Helper to create a system. Returns a list of SystemIds.

    e.g.:
      create_system(self._manager.system, self.context, SomeSystem)
      create_system(self._manager.system, special_context, SomeSystem)
    '''
    # sub = context.sub
    # if kwargs:
    #     sub['system'] = kwargs
    # else:
    #     sub.pop('system', None)

    sid = system_manager.create(sys_type,
                                context)

    # sub.pop('system', None)
    return sid


def create_systems(system_manager: SystemManager,
                   context: VerediContext,
                   *args: SysCreateType,
                   debug_flags: Optional[DebugFlag] = None) -> List[SystemId]:
    '''
    Helper to create systems. Takes in either types or tuples of
    (type, context). Returns a list of SystemIds.
    If tuple, will use tuple's context, else uses the `context` arg.

    e.g.:
      create_systems(self._manager.system, self.context, SomeSystem)
      create_systems(self._manager.system, self.context,
                     (SomeSystem, different_context)) # ignores self.context
      create_systems(self._manager.system, self.context,
                     (SomeSystem, context_for_SomeSystem),
                     TwoSystem) # TwoSystem uses self.context
    '''
    sids = []
    for each in args:
        if isinstance(each, tuple):
            # Have context in tuple - ignore the "default" `context` arg.
            sids.append(create_system(system_manager, each[1],
                                      each[0]))
        else:
            # Use `context` arg.
            sids.append(create_system(system_manager, context,
                                      each))

    return sids


# -----------------------------------------------------------------------------
# Enough to load some data from the zata dir related to `test_type`.
# -----------------------------------------------------------------------------

def set_up(test_name_class:   str,
           test_name_func:    str,
           enable_debug_logs: bool,
           # Optional Debug Stuff:
           test_type:         TestType                   = TestType.UNIT,
           debug_flags:       Optional[DebugFlag]        = None,
           # Optional ECS:
           require_engine:    Optional[bool]             = False,
           desired_systems:   Iterable[SysCreateType]    = None,
           # Optional to pass in - else we'll make:
           configuration:     Optional[Configuration]    = None,
           time_manager:      Optional[TimeManager]      = None,
           event_manager:     Optional[EventManager]     = None,
           component_manager: Optional[ComponentManager] = None,
           entity_manager:    Optional[EntityManager]    = None,
           system_manager:    Optional[SystemManager]    = None,
           # Optional to pass in - else we'll make  if asked:
           engine:            Optional[Engine]           = None,
           ) -> Tuple[Meeting, VerediContext, List[SystemId]]:
    '''
    Creates config, managers, if not supplied (via zmake.meeting).
    Creates a managers' meeting (via zmake.meeting).
    Creates a real context (via zontext.real_contfig).
    Creates supplied Systems (using our zload.create_systems).
      - If none supplied, creates default of: DataSystem.
      - These are (currently) the min required to get from disk to component.

    Returns:
      Tuple[Meeting, VerediContext, SystemManager, List[SystemId]]
    '''
    with log.LoggingManager.on_or_off(enable_debug_logs):
        if not configuration:
            log.debug("zload.loader creating Configuration...")
            configuration = configuration or zmake.config(test_type)

        log.debug("zload.loader creating Meeting...")
        meeting = zmake.meeting(test_type,
                                configuration,
                                time_manager,
                                event_manager,
                                component_manager,
                                entity_manager,
                                system_manager,
                                debug_flags)

        engine = None
        if require_engine:
            log.debug("zload.loader creating Engine...")
            engine = Engine(None, None,
                            configuration,
                            meeting.event,
                            meeting.time,
                            meeting.component,
                            meeting.entity,
                            meeting.system,
                            debug_flags)

        system_manager = meeting.system

        log.debug("zload.loader creating Context...")
        context = zontext.real_config(test_name_class,
                                      test_name_func,
                                      config=configuration)
        log.debug("zload.loader creating systems...")
        sids = []
        if desired_systems:
            sids = create_systems(system_manager, context,
                                  *desired_systems)
        elif not require_engine:
            sids = create_systems(system_manager, context,
                                  DataSystem)  # , NextSystem, etc)
        # Else: our engine creates the requried stuff and we don't want to
        # double-create.

        return meeting, engine, context, sids


# -----------------------------------------------------------------------------
# Background Helper
# -----------------------------------------------------------------------------

def set_up_background() -> None:
    '''
    Get the context cleared out and ready for a new test.
    '''
    # Context will create an empty data structure to fill if it has none, so we
    # just need to nuke it from orbit.
    background.testing.nuke()
    background.testing.set_unit_testing(True)


def tear_down_background() -> None:
    '''
    Get the context cleared out and ready for a new test.
    '''
    # Currently nothing really to do that set_up_background() doesn't do.
    # But I want tear_down_background() for the pairing.
    background.testing.nuke()


# -----------------------------------------------------------------------------
# Registries Helper
# -----------------------------------------------------------------------------

# TODO [2020-11-12]: Figure out how to register Encodables for every test?
# If not, remove these functions and the things that call them.

def set_up_registries(encodables: bool = True,
                      **kwargs:   bool) -> None:
    '''
    Get the registries cleared out and ready for a new test.
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
        error = ValueError(reg_name, msg)
        raise log.exception(error, None, msg)


def tear_down_registries() -> None:
    '''
    Get the registries cleared out and ready for a new test.
    '''
    config_registry._ut_unregister()
    yaml_registry._ut_unregister()

    # # Currently nothing really to do that set_up_registries() doesn't do.
    # # But I want to clear out the registries for the pairing.
    # EncodableRegistry.nuke()
