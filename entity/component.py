# coding: utf-8

'''
Everything that makes up players, monsters, items, etc. should be a Component
subclass...
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import NewType, Any, Union, Type, Iterable
import enum

from .exceptions import ComponentError

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

EntityId = NewType('EntityId', int)
INVALID_ENTITY_ID = EntityId(0)

InstOrType = Union['Component', Type['Component']]

@enum.unique
class StateLifeCycle(enum.Enum):
    INVALID = 0
    ADDED   = enum.auto()
    EXISTS  = enum.auto()
    REMOVED = enum.auto()


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Component:
    '''
    A component does not track its EntityId. This is so we can have entities
    that actually share the same exact component.
    '''

    def __init__(self) -> None:
        self.meta = ComponentMetaData(True, StateLifeCycle.ADDED)

    def replaceable_with(self, other: 'Component'):
        '''
        Entities can only have one of any type of component. This function is
        for the case where a component type has been requested to be added to an
        entity that already has one of those.

        Returns:
          - True if this can be replaced with `other`.
          - False if not.
        '''
        # default to not allowing a component to be replaced
        return False

    # --------------------------------------------------------------------------
    # Set Interface (hashable, equals)
    # --------------------------------------------------------------------------

    @staticmethod
    def hashed(components: Iterable['Component']) -> int:
        '''
        Hashes each component and returns the overall hash.
        '''
        return sum(map(hash, components))

    def __hash__(self):
        # Hash of (sub)class itself, not any instance.
        # All (sub)class instances will be considered 'equal' this way for
        # e.g. set, dict operations.
        return hash(self.__class__)

    def __eq__(self, other: Any):
        # Hash of (sub)class itself, not any instance.
        # All (sub)class instances will be considered 'equal' this way for
        # e.g. set, dict operations.
        other_hash = None
        if isinstance(other, (set, frozenset)):
            other_hash = Component.hashed(other)
        else:
            other_hash = hash(other)
        return hash(self) == other_hash


class ComponentMetaData:
    def __init__(self,
                 enabled: bool = True,
                 state: StateLifeCycle = StateLifeCycle.ADDED
                 ) -> None:
        self.enabled = enabled
        self.state = state
