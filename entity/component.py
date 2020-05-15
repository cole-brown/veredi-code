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

ComponentId = NewType('ComponentId', int)
INVALID_COMPONENT_ID = ComponentId(0)

CompInstOrType = Union['Component', Type['Component']]

@enum.unique
class ComponentLifeCycle(enum.Enum):
    INVALID    = 0
    CREATING   = enum.auto()
    ALIVE      = enum.auto()
    DESTROYING = enum.auto()

# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Component:
    '''
    A component does not track its EntityId. This is so we can have entities
    that actually share the same exact component.
    '''

    def __init__(self,
                 cid: ComponentId) -> None:
        self._comp_id = cid
        self._life_cycle = ComponentLifeCycle.CREATING

    @property
    def id(self) -> ComponentId:
        return self._comp_id

    @property
    def life_cycle(self):
        return self._life_cycle

    @property
    def enabled(self):
        return self._life_cycle == ComponentLifeCycle.ALIVE

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

    def __hash__(self):
        '''Set/Dict interface.

        Redefining so that Components are singleton - only one per class
        allowed. This doesn't prevent an Entity from having, say, HealthClass
        and HealthSubClass, but at least it's a sanity check.
        '''
        # Hash of (sub)class itself, not any instance.
        # All (sub)class instances will be considered 'equal' this way for
        # e.g. set, dict operations.
        return hash(self.__class__)

    def __eq__(self, other: Any):
        '''Set/Dict interface.

        Redefining so that Components are singleton - only one per class
        allowed. This doesn't prevent an Entity from having, say, HealthClass
        and HealthSubClass, but at least it's a sanity check.
        '''
        # Hash of (sub)class itself, not any instance.
        # All (sub)class instances will be considered 'equal' this way for
        # e.g. set, dict operations.
        other_hash = None
        if isinstance(other, Component):
            other_hash = Component.hashed(other)
        else:
            other_hash = hash(other)
        return hash(self) == other_hash

# TODO:
#   Some ComponentSet or ComponentDict or ComponentManager for representing, comparing Components/Entities.

class ComponentMetaData:
    def __init__(self,
                 enabled: bool = True,
                 ) -> None:
        self.enabled = enabled
