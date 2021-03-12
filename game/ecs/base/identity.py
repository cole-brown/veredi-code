# coding: utf-8

'''
IDs for Entities, Components, and Systems.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.base.strings  import labeler
from veredi.base.identity import MonotonicId

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# ECS ID Types
# -----------------------------------------------------------------------------

@labeler.dotted('veredi.game.ecs.base.identity.component')
class ComponentId(MonotonicId):
    _ENCODE_FIELD_NAME = 'cid'
    '''Can override in sub-classes if needed.'''

    # Subclass has no new functionality.
    pass


@labeler.dotted('veredi.game.ecs.base.identity.entity')
class EntityId(MonotonicId):
    _ENCODE_FIELD_NAME = 'eid'
    '''Can override in sub-classes if needed.'''

    # Subclass has no new functionality.
    pass


@labeler.dotted('veredi.game.ecs.base.identity.system')
class SystemId(MonotonicId):
    _ENCODE_FIELD_NAME = 'sid'
    '''Can override in sub-classes if needed.'''

    # Subclass has no new functionality.
    pass
