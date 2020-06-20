# coding: utf-8

'''
Helper for unit test data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, Optional, Type, NewType, Tuple, Iterable, List

from veredi.logger import log
from .             import zmake, zontext
from .zpath        import TestType

# Config Stuff
from veredi.data.config.config          import Configuration

# Meeting Stuff
from veredi.game.ecs.const              import DebugFlag
from veredi.game.ecs.base.system        import Meeting, System
from veredi.game.ecs.time               import TimeManager
from veredi.game.ecs.event              import EventManager
from veredi.game.ecs.component          import ComponentManager
from veredi.game.ecs.entity             import EntityManager
from veredi.game.ecs.system             import SystemManager
from veredi.base.context                import VerediContext
from veredi.game.ecs.base.identity      import SystemId

# System Stuff
from veredi.game.data.repository.system import RepositorySystem
from veredi.game.data.codec.system      import CodecSystem
from veredi.game.data.system            import DataSystem

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
                  sys_type: Type[System]) -> SystemId:
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
                   *args: SysCreateType) -> List[SystemId]:
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

def set_up(
        test_name_class:   str,
        test_name_func:    str,
        enable_debug_logs: bool,
        desired_systems:   Optional[Iterable[SysCreateType]] = None,
        test_type:         Optional[TestType]                = TestType.UNIT,
        configuration:     Optional[Configuration]           = None,
        time_manager:      Optional[TimeManager]             = None,
        event_manager:     Optional[EventManager]            = None,
        component_manager: Optional[ComponentManager]        = None,
        entity_manager:    Optional[EntityManager]           = None,
        system_manager:    Optional[SystemManager]           = None,
        debug_flags:       Optional[DebugFlag]               = None
        # This closing paren is a fucked up way to make pycodestyle happy...
        # May need to get flake8 so I can "# noqa" this one?
        # Oh. This comment itself lets me do whatever I want now. Yay.
        ) -> Tuple[Meeting, VerediContext, List[SystemId]]:
    '''
    Creates config, managers, if not supplied (via zmake.meeting).
    Creates a managers' meeting (via zmake.meeting).
    Creates a real context (via zontext.real_contfig).
    Creates supplied Systems (using our zload.create_systems).
      - If none supplied, creates default RepositorySystem, CodecSystem, and
        DataSystem.
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
                                debug_flags)

        log.debug("zload.loader SystemManager...")
        system_manager = SystemManager(configuration,
                                       meeting.time,
                                       meeting.event,
                                       meeting.component,
                                       meeting.entity,
                                       debug_flags)

        log.debug("zload.loader creating Context...")
        context = zontext.real_config(test_name_class,
                                      test_name_func,
                                      config=configuration,
                                      test_type=test_type)

        log.debug("zload.loader creating systems...")
        if not desired_systems:
            sids = create_systems(system_manager, context,
                                  RepositorySystem, CodecSystem, DataSystem)
        else:
            sids = create_systems(system_manager, context,
                                  *desired_systems)

        return meeting, context, system_manager, sids
