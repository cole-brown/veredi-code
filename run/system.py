# coding: utf-8

'''
Create Game ECS Systems.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, Optional, Type, NewType, Tuple, List

from veredi.logs                       import log
from veredi.base.strings               import label

from veredi.data                       import background
from veredi.debug.const                import DebugFlag

from veredi.data.config.config         import Configuration
from veredi.data.exceptions            import ConfigError

from veredi.game.ecs.base.system       import System
from veredi.base.context               import VerediContext
from veredi.game.ecs.base.identity     import SystemId


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_DOTTED = "veredi.run.system"

SysCreateType = NewType('SysCreateType',
                        Union[System,
                              Type[System],
                              Tuple[Union[System, Type[System]],
                                    VerediContext]])
'''
Systems can be created/added to Veredi in any of these forms:
  - A System instance.
  - A System type.
  - A tuple of:
    - System instance or type.
    - VerediContext intstance.

If a tuple (with a system type) is used, the tuple's context will be passed
into the system's `__init__()`.
'''


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def create(config:      Optional[Configuration],
           context:     VerediContext,
           system_type: Type[System],
           debug_flags: Optional[DebugFlag] = None) -> SystemId:
    '''
    Helper to create a system. Returns the created system's SystemId.
    '''
    log_dotted = label.normalize(_DOTTED, 'create')
    log.start_up(log_dotted,
                 f"Creating system '{str(system_type.__name__)}'...")

    sid = background.manager.system.create(system_type,
                                           context)

    log.start_up(log_dotted,
                 f"Created system '{str(system_type.__name__)}' with "
                 f"SystemId: {str(sid)}",
                 log_success=log.SuccessType.SUCCESS)
    return sid


def add(system: System) -> SystemId:
    '''
    Helper to take an already created system, and add it into the
    SystemManager's systems. Returns the SystemId assigned by SystemManager.
    '''
    log_dotted = label.normalize(_DOTTED, 'add')
    log.start_up(log_dotted,
                 f"Adding system '{str(system.__class__.__name__)}'...")

    sid = background.manager.system.add(system)

    log.start_up(log_dotted,
                 f"Added system '{str(system.__class__.__name__)}' with "
                 f"SystemId: {str(sid)}",
                 log_success=log.SuccessType.SUCCESS)
    return sid


def _create_or_add(log_dotted:      str,
                   config:          Optional[Configuration],
                   context:         VerediContext,
                   system_or_type:  Union[System, Type[System]],
                   debug_flags:     DebugFlag,
                   special_context: bool) -> SystemId:
    '''
    Helper for using SysCreateType to `create`/`add` systems.
    '''
    ctx_str = ('special context'
               if special_context else
               'context')
    sid = None

    # System type to create?
    if issubclass(system_or_type, System):
        log.start_up(
            log_dotted,
            f"Creating system '{str(system_or_type.__name__)}' "
            f"with {ctx_str} {str(context)}...")
        sid = create(config,
                     context,
                     system_or_type,
                     debug_flags)
        log.start_up(
            log_dotted,
            f"Created system '{str(system_or_type.__name__)}'.",
            log_success=log.SuccessType.SUCCESS)

    # System already created?
    elif isinstance(system_or_type, System):
        log.start_up(
            log_dotted,
            f"Adding system '{str(system_or_type.__name__)}' "
            f"with {ctx_str} {str(context)}...")
        sid = create(config,
                     context,
                     system_or_type,
                     debug_flags)
        log.start_up(
            log_dotted,
            f"Added system '{str(system_or_type.__name__)}'.",
            log_success=log.SuccessType.SUCCESS)

    # Error!
    else:
        msg = "`system_or_type` must be a System instance or System type."
        error = ConfigError(msg,
                            data={
                                'config': config,
                                'context': context,
                                'system_or_type': system_or_type,
                                'debug_flags': debug_flags,
                                'special_context': special_context,
                            })
        raise log.exception(error, msg)

    return sid


def many(config:      Optional[Configuration],
         context:     VerediContext,
         *args:       SysCreateType,
         debug_flags: Optional[DebugFlag] = None) -> List[SystemId]:
    '''
    Helper to `create`/`add` many systems.

    See SysCreateType docstr for what it accepts.

    Returns a list of SystemIds.

    If tuple, will use tuple's context, else uses the `context` arg.

    e.g.:
      systems(config, context, SomeSystem) # could just use `create` or add`
      systems(config, context,
              (SomeSystem, different_context)) # uses `different_context`
      systems(config, context,
              (SomeSystem, context_for_SomeSystem), # ignores `context`
              TwoSystem) # uses `context`
    '''
    log_dotted = label.normalize(_DOTTED, 'many')
    log.start_up(log_dotted,
                 f"Creating {len(args)} systems...")

    sids = []
    for each in args:
        sid = None
        system_or_type = None
        system_context = None
        context_unique = False

        if isinstance(each, tuple):
            # Have a special context in tuple - ignore the "default" `context`
            # arg.
            system_or_type = each[0]
            system_context = each[1]
            context_unique = True

        else:
            # Use the normal `context` arg.
            system_or_type = each
            system_context = context
            context_unique = False

        log.start_up(log_dotted,
                     f"Processing system '{str(system_or_type.__name__)}' for"
                     f"adding/creating...")

        # Alrighty - do the thing with the system.
        sid = _create_or_add(log_dotted,
                             config,
                             system_context,
                             system_or_type,
                             debug_flags,
                             context_unique)
        sids.append(sid)

        log.start_up(log_dotted,
                     f"System '{str(system_or_type.__name__)}' processed.",
                     log_success=log.SuccessType.SUCCESS)

    log.start_up(log_dotted,
                 f"Created {len(sids)} systems with SystemIds: {str(sids)}",
                 log_success=log.SuccessType.SUCCESS)
    return sids
