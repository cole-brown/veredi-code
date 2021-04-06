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

class ComponentId(MonotonicId,
                  name_dotted='veredi.game.ecs.base.identity.component',
                  name_string='cid'):
    pass

class EntityId(MonotonicId,
               name_dotted='veredi.game.ecs.base.identity.entity',
               name_string='eid'):
    pass

class SystemId(MonotonicId,
               name_dotted='veredi.game.ecs.base.identity.system',
               name_string='sid'):
    pass
