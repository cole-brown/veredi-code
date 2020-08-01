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

class ComponentId(MonotonicId):
    _ENCODE_FIELD_NAME = 'cid'
    '''Can override in sub-classes if needed.'''

    # Subclass has no new functionality.
    pass


class EntityId(MonotonicId):
    _ENCODE_FIELD_NAME = 'eid'
    '''Can override in sub-classes if needed.'''

    # Subclass has no new functionality.
    pass


class SystemId(MonotonicId):
    _ENCODE_FIELD_NAME = 'sid'
    '''Can override in sub-classes if needed.'''

    # Subclass has no new functionality.
    pass
