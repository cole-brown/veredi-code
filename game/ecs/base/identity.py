# coding: utf-8

'''
IDs for Entities, Components, and Systems.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.base.identity import MonotonicId

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# ECS ID Types
# -----------------------------------------------------------------------------

class ComponentId(MonotonicId,
                  dotted='veredi.game.ecs.base.identity.component'):
    _ENCODE_FIELD_NAME = 'cid'
    '''Can override in sub-classes if needed.'''

    # Subclass has no new functionality.
    pass


class EntityId(MonotonicId,
               dotted='veredi.game.ecs.base.identity.entity'):
    _ENCODE_FIELD_NAME = 'eid'
    '''Can override in sub-classes if needed.'''

    # Subclass has no new functionality.
    pass


class SystemId(MonotonicId,
               dotted='veredi.game.ecs.base.identity.system'):
    _ENCODE_FIELD_NAME = 'sid'
    '''Can override in sub-classes if needed.'''

    # Subclass has no new functionality.
    pass
